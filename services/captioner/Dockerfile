# OmniCaption captioner — linux/amd64, AMD ROCm runtime.
# Build: docker build --platform linux/amd64 -t omnicaption-captioner .
#
# The base image ships PyTorch built against ROCm/HIP; CTranslate2 and ffmpeg
# are added on top. Keep the final image <10 GB and cold start <60 s.
FROM --platform=linux/amd64 rocm/pytorch:latest

# ---- OS packages --------------------------------------------------------------
# ffmpeg is required by the ingestion stage for audio extraction.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Default ROCm arch matrix knobs. Override at `docker run` for a specific GPU:
#   MI300X gfx942 | RX 7900 XTX gfx1100 | RX 6600 gfx1032 | Ryzen AI gfx1103/gfx1150
ENV PYTORCH_ROCM_ARCH="gfx942;gfx1100;gfx1032;gfx1103;gfx1150" \
    HF_HOME="/opt/hf-cache" \
    PYTHONUNBUFFERED="1"

# ---- Python dependencies (own layer for build caching) ------------------------
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---- Model weight cache layer -------------------------------------------------
# Bake the Whisper weights into HF_HOME while the network is still allowed, so
# container startup does no model download (<60 s budget). faster-whisper's
# "large-v3" alias resolves to this repo via huggingface_hub, which finds the
# baked snapshot in HF_HOME at runtime. This layer is cached independently of
# the app source, so code edits do not re-download the (~3 GB) weights.
RUN python -c "from huggingface_hub import snapshot_download; \
               snapshot_download('Systran/faster-whisper-large-v3')"

# Model weights are baked from here on: forbid hub network access at runtime.
# (The container still uses the network for video downloads and the Fireworks
# VLM API — only Hugging Face hub lookups are forced offline.)
ENV HF_HUB_OFFLINE="1"

# ---- Application source -------------------------------------------------------
COPY app ./app

# The eval harness mounts /input and /output at runtime. The synthesis stage
# additionally needs FIREWORKS_API_KEY passed at `docker run -e ...`; without
# it every style deterministically falls back (never crashes, but scores low).
VOLUME ["/input", "/output"]

ENTRYPOINT ["python", "-m", "app.main"]
