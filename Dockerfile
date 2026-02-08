# PersonaPlex Standup Server
# GPU: Requires A100 40GB or H100
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    libopus-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set python3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

WORKDIR /app

# Clone PersonaPlex
RUN git clone https://github.com/NVIDIA/personaplex.git

# Install PersonaPlex (moshi)
WORKDIR /app/personaplex
RUN pip install --no-cache-dir ./moshi/

# Install additional dependencies for our wrapper
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    httpx \
    python-multipart

# Copy our wrapper code
WORKDIR /app
COPY server.py /app/server.py
COPY prompts/ /app/prompts/

# Create directories
RUN mkdir -p /app/context /app/ssl

# Environment
ENV HF_TOKEN=""
ENV VOICE_PROMPT="NATM1.pt"
ENV PORT_API=8080
ENV PORT_MOSHI=8998

# Expose ports
# 8080 = API for context injection
# 8998 = Moshi WebSocket for audio
EXPOSE 8080 8998

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD curl -f http://localhost:8080/health || exit 1

# Start wrapper server (manages moshi process)
CMD ["python", "server.py"]
