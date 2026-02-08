#!/bin/bash
# Build and push PersonaPlex Standup Docker image
set -e

REGISTRY="${REGISTRY:-ghcr.io}"
REPO="${REPO:-moltyfromclaw/personaplex-standup}"
TAG="${TAG:-latest}"

IMAGE="${REGISTRY}/${REPO}:${TAG}"

echo "🐳 Building ${IMAGE}..."
docker build -t "${IMAGE}" .

echo "📤 Pushing ${IMAGE}..."
docker push "${IMAGE}"

echo "✅ Done! Image: ${IMAGE}"
echo ""
echo "Deploy on RunPod with:"
echo "  Image: ${IMAGE}"
echo "  GPU: A100 40GB"
echo "  Ports: 8080, 8998"
echo "  Env: HF_TOKEN=hf_xxx"
