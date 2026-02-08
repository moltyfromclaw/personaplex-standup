#!/bin/bash
# Run this on a fresh RunPod A100 pod
# Usage: curl -sSL https://raw.githubusercontent.com/moltyfromclaw/personaplex-standup/main/runpod-setup.sh | bash -s -- <HF_TOKEN>

set -e

HF_TOKEN="${1:-$HF_TOKEN}"

if [ -z "$HF_TOKEN" ]; then
    echo "❌ HuggingFace token required!"
    echo "Usage: ./runpod-setup.sh <HF_TOKEN>"
    exit 1
fi

echo "🦞 PersonaPlex Standup Setup"
echo "============================"

# Install system deps
echo "📦 Installing system dependencies..."
apt-get update && apt-get install -y libopus-dev ffmpeg git python3-pip

# Clone PersonaPlex
echo "📥 Cloning PersonaPlex..."
cd /workspace
git clone https://github.com/NVIDIA/personaplex.git
cd personaplex
pip install ./moshi/

# Install wrapper deps
echo "📦 Installing wrapper dependencies..."
pip install fastapi uvicorn[standard] httpx python-multipart

# Clone our standup server
echo "📥 Cloning standup server..."
cd /workspace
git clone https://github.com/moltyfromclaw/personaplex-standup.git
cd personaplex-standup

# Set environment
export HF_TOKEN="$HF_TOKEN"
export VOICE_PROMPT="NATM1.pt"
export PORT_API=8080
export PORT_MOSHI=8998

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the server, run:"
echo "  cd /workspace/personaplex-standup"
echo "  HF_TOKEN=$HF_TOKEN python server.py"
echo ""
echo "Then access:"
echo "  API: https://<pod-id>-8080.proxy.runpod.net"
echo "  Voice UI: https://<pod-id>-8998.proxy.runpod.net"
