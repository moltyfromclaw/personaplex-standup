# PersonaPlex Standup 🎤🦞

Voice standup meetings with your AI agents. Ask what they got done, what they're stuck on, and what's next.

Built on [NVIDIA PersonaPlex-7B](https://huggingface.co/nvidia/personaplex-7b-v1) - a full-duplex speech-to-speech model with 170ms latency.

## Features

- **Voice conversation** - Talk naturally with your agent, interrupts work
- **Context injection** - Feed ClawView markdown data for the agent to reference
- **Full duplex** - Agent listens while speaking, like a real conversation
- **Persona control** - Molty personality, customizable voice

## Architecture

```
┌─────────────────────────────────────────────┐
│  ClawView                                   │
│  GET /api/tasks/export → markdown           │
└──────────────────┬──────────────────────────┘
                   │ POST /context
                   ▼
┌─────────────────────────────────────────────┐
│  PersonaPlex Standup Server (this)          │
│  :8080 - API (context injection)            │
│  :8998 - Moshi WebSocket (audio)            │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Browser WebUI / Phone                      │
│  "Hey Molty, what did you get done?"        │
└─────────────────────────────────────────────┘
```

## Quick Start (RunPod)

### 1. Build & Push Docker Image

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build
docker build -t ghcr.io/moltyfromclaw/personaplex-standup:latest .

# Push
docker push ghcr.io/moltyfromclaw/personaplex-standup:latest
```

### 2. Create RunPod Pod

1. Go to [RunPod](https://runpod.io)
2. Create new Pod:
   - **GPU**: A100 40GB (or A40 with CPU_OFFLOAD=true)
   - **Image**: `ghcr.io/moltyfromclaw/personaplex-standup:latest`
   - **Expose ports**: 8080, 8998 (both HTTP)
   - **Environment variables**:
     ```
     HF_TOKEN=hf_your_token_here
     VOICE_PROMPT=NATM1.pt
     ```

3. Start the pod

### 3. Test Connection

```bash
# Health check
curl https://<pod-id>-8080.proxy.runpod.net/health

# Should return:
# {"status":"healthy","moshi_running":true,...}
```

### 4. Inject ClawView Context

```bash
# Fetch markdown from ClawView
curl -s https://your-clawview/api/tasks/export > tasks.md

# Inject into PersonaPlex
curl -X POST https://<pod-id>-8080.proxy.runpod.net/context \
  -H "Content-Type: application/json" \
  -d "{\"markdown\": $(cat tasks.md | jq -Rs .)}"
```

### 5. Connect to Voice UI

Open in browser:
```
https://<pod-id>-8998.proxy.runpod.net
```

Click "Start" and begin talking!

## API Reference

### `POST /context`
Update the context markdown. Restarts PersonaPlex with new prompt.

```json
{
  "markdown": "# Task Summary\n\n...",
  "agent_name": "Molty"
}
```

### `GET /context`
Get current context and prompt preview.

### `GET /health`
Health check. Returns moshi process status.

### `POST /restart`
Restart moshi with current context.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_TOKEN` | (required) | HuggingFace token for model download |
| `VOICE_PROMPT` | `NATM1.pt` | Voice embedding (NATM1, NATF2, etc.) |
| `PORT_API` | `8080` | API server port |
| `PORT_MOSHI` | `8998` | Moshi WebSocket port |
| `CPU_OFFLOAD` | `false` | Enable CPU offload for smaller GPUs |

## Voice Options

Natural voices (recommended):
- `NATF0` - `NATF3`: Female natural voices
- `NATM0` - `NATM3`: Male natural voices

Variety voices:
- `VARF0` - `VARF4`: Female variety
- `VARM0` - `VARM4`: Male variety

## Integration with ClawView

Add a "Standup" button to ClawView that:
1. Fetches markdown export
2. POSTs to PersonaPlex `/context`
3. Opens PersonaPlex WebUI in new tab

```javascript
async function startStandup() {
  // Get tasks markdown
  const res = await fetch('/api/tasks/export');
  const markdown = await res.text();
  
  // Inject context
  await fetch('https://personaplex.example.com/context', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ markdown }),
  });
  
  // Open voice UI
  window.open('https://personaplex.example.com:8998', '_blank');
}
```

## Local Development

```bash
# Requires NVIDIA GPU with CUDA
docker build -t personaplex-standup .
docker run --gpus all -p 8080:8080 -p 8998:8998 \
  -e HF_TOKEN=hf_xxx \
  personaplex-standup
```

## Costs

- **RunPod A100 40GB**: ~$1.09/hr
- **RunPod A40 24GB** (with CPU_OFFLOAD): ~$0.39/hr

Recommended: Spin up on-demand for standups, shut down after.

## License

MIT (wrapper code). PersonaPlex model under NVIDIA Open Model License.
