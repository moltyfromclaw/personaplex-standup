"""
PersonaPlex Standup Server
Wrapper that manages PersonaPlex process and allows dynamic context injection.
"""

import os
import subprocess
import signal
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="PersonaPlex Standup", version="1.0.0")

# CORS for ClawView integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
moshi_process: Optional[subprocess.Popen] = None
current_context: str = ""
ssl_dir: Optional[str] = None

# Config from environment
HF_TOKEN = os.environ.get("HF_TOKEN", "")
VOICE_PROMPT = os.environ.get("VOICE_PROMPT", "NATM1.pt")
PORT_API = int(os.environ.get("PORT_API", 8080))
PORT_MOSHI = int(os.environ.get("PORT_MOSHI", 8998))
CPU_OFFLOAD = os.environ.get("CPU_OFFLOAD", "false").lower() == "true"


# Base prompt template for agent standup
BASE_PROMPT = """You are Molty, a helpful AI agent assistant. You're having a voice standup meeting with your human to report on what you and other agents have accomplished.

Your personality:
- Friendly and conversational, like a coworker giving a standup update
- Concise but thorough - hit the highlights, offer details if asked
- Honest about issues or blockers encountered
- You refer to costs in dollars when relevant

When answering:
- Start with the big picture (how many tasks, total cost, major accomplishments)
- Mention any failures or issues that needed attention
- If asked about specific tasks, reference the details below
- Keep responses conversational, not robotic

{context}

Answer questions naturally. If you don't know something that's not in the context above, say so.
"""


class ContextUpdate(BaseModel):
    """Markdown context from ClawView"""
    markdown: str
    agent_name: Optional[str] = "Molty"


class StandupConfig(BaseModel):
    """Configuration for standup session"""
    voice_prompt: Optional[str] = None
    clawview_url: Optional[str] = None


def build_prompt(context_markdown: str) -> str:
    """Build the full text prompt with injected context."""
    if context_markdown:
        context_section = f"""
Here's the activity report for your reference:

---
{context_markdown}
---
"""
    else:
        context_section = """
No activity data has been loaded yet. You can still have a conversation, but you won't have specific task data to reference. Ask your human to update the context.
"""
    return BASE_PROMPT.format(context=context_section)


def stop_moshi():
    """Stop the running moshi process."""
    global moshi_process
    if moshi_process:
        print("Stopping moshi process...")
        moshi_process.terminate()
        try:
            moshi_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            moshi_process.kill()
        moshi_process = None
        print("Moshi process stopped.")


def start_moshi(text_prompt: str):
    """Start the moshi server with the given prompt."""
    global moshi_process, ssl_dir
    
    # Stop existing process
    stop_moshi()
    
    # Create SSL directory if needed
    if not ssl_dir:
        ssl_dir = tempfile.mkdtemp(prefix="moshi_ssl_")
    
    # Write prompt to file (moshi can read from file)
    prompt_file = Path("/app/context/current_prompt.txt")
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(text_prompt)
    
    # Build command
    cmd = [
        "python", "-m", "moshi.server",
        "--ssl", ssl_dir,
        "--port", str(PORT_MOSHI),
        "--voice-prompt", VOICE_PROMPT,
        "--text-prompt", text_prompt,
    ]
    
    if CPU_OFFLOAD:
        cmd.append("--cpu-offload")
    
    # Set environment
    env = os.environ.copy()
    env["HF_TOKEN"] = HF_TOKEN
    
    print(f"Starting moshi server: {' '.join(cmd[:6])}...")
    
    # Start process
    moshi_process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    
    print(f"Moshi server started (PID: {moshi_process.pid})")
    return moshi_process.pid


@app.on_event("startup")
async def startup():
    """Start moshi with default prompt on server startup."""
    print("PersonaPlex Standup Server starting...")
    if not HF_TOKEN:
        print("WARNING: HF_TOKEN not set. Moshi will fail to download model.")
    else:
        # Start with empty context initially
        prompt = build_prompt("")
        start_moshi(prompt)


@app.on_event("shutdown")
async def shutdown():
    """Clean shutdown."""
    stop_moshi()


@app.get("/health")
async def health():
    """Health check endpoint."""
    moshi_running = moshi_process is not None and moshi_process.poll() is None
    return {
        "status": "healthy" if moshi_running else "degraded",
        "moshi_running": moshi_running,
        "moshi_pid": moshi_process.pid if moshi_process else None,
        "context_loaded": bool(current_context),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint with info."""
    return {
        "service": "PersonaPlex Standup",
        "version": "1.0.0",
        "endpoints": {
            "POST /context": "Update markdown context from ClawView",
            "GET /context": "Get current context",
            "POST /restart": "Restart moshi with current context",
            "GET /health": "Health check",
            "WebSocket wss://<host>:8998": "Moshi audio stream (PersonaPlex WebUI)",
        },
        "moshi_port": PORT_MOSHI,
    }


@app.post("/context")
async def update_context(update: ContextUpdate, background_tasks: BackgroundTasks):
    """
    Update the context markdown and restart moshi with new prompt.
    
    Call this with ClawView's markdown export before starting a standup.
    """
    global current_context
    
    current_context = update.markdown
    prompt = build_prompt(current_context)
    
    # Restart moshi in background (takes a few seconds)
    def restart_with_prompt():
        start_moshi(prompt)
    
    background_tasks.add_task(restart_with_prompt)
    
    return {
        "status": "context_updated",
        "context_length": len(current_context),
        "message": "Moshi restarting with new context. Wait ~10s before connecting.",
    }


@app.get("/context")
async def get_context():
    """Get the current context."""
    return {
        "context": current_context,
        "context_length": len(current_context),
        "prompt_preview": build_prompt(current_context)[:500] + "...",
    }


@app.post("/restart")
async def restart_moshi():
    """Restart moshi with current context."""
    prompt = build_prompt(current_context)
    pid = start_moshi(prompt)
    return {
        "status": "restarted",
        "pid": pid,
    }


@app.get("/logs")
async def get_logs():
    """Get recent moshi logs."""
    if not moshi_process:
        return {"logs": "Moshi not running"}
    
    # This is a simplified version - in production you'd want proper log handling
    return {
        "status": "running" if moshi_process.poll() is None else "stopped",
        "pid": moshi_process.pid,
    }


# Signal handlers for clean shutdown
def handle_signal(signum, frame):
    print(f"Received signal {signum}, shutting down...")
    stop_moshi()
    exit(0)


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT_API,
        log_level="info",
    )
