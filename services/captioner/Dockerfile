# OmniCaption captioner — linux/amd64, AMD ROCm runtime.
# Build: docker build --platform linux/amd64 -t omnicaption-captioner .
#
# The base image ships PyTorch built against ROCm/HIP; CTranslate2-HIP and
# ffmpeg are added on top. Keep the final image <10 GB and cold start <60 s.
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
    HF_HUB_OFFLINE="1" \
    TRANSFORMERS_OFFLINE="1" \
    PYTHONUNBUFFERED="1"

# ---- Python dependencies (own layer for build caching) ------------------------
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---- Model weight cache layer -------------------------------------------------
# Bake weights into the image so container startup does no network I/O (startup
# <60 s constraint, and the harness runs offline). Uncomment and pin real ids.
#
# TODO(hackathon): pre-download and bake model weights here, e.g.:
#   RUN python -c "from faster_whisper import WhisperModel; \
#                  WhisperModel('large-v3', download_root='/opt/hf-cache')"
#   RUN python -c "from transformers import AutoProcessor, AutoModelForImageTextToText; \
#                  AutoProcessor.from_pretrained('google/gemma-4-e4b-it'); \
#                  AutoModelForImageTextToText.from_pretrained('google/gemma-4-e4b-it')"
# These layers are cached independently of the app source so code edits do not
# invalidate the (large, slow) weight download.

# ---- Application source -------------------------------------------------------
COPY app ./app

# The eval harness mounts /input and /output at runtime.
VOLUME ["/input", "/output"]

ENTRYPOINT ["python", "-m", "app.main"]
