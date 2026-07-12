# OmniCaption captioner - linux/amd64, AMD ROCm runtime.
# Build (the platform is REQUIRED - set it at build time, not hardcoded in FROM):
#   docker build --platform linux/amd64 -t omnicaption-captioner .
# The rocm/pytorch base is amd64-only, so on an amd64 host the platform is implied
# anyway; the flag keeps the manifest single-arch linux/amd64 on any builder.
#
# The base image ships PyTorch built against ROCm/HIP; CTranslate2 and ffmpeg
# are added on top. Keep the final image <10 GB and cold start <60 s.
FROM rocm/pytorch:latest AS builder

# ---- OS packages --------------------------------------------------------------
# ffmpeg for audio extraction; libgomp1 is CTranslate2's OpenMP runtime. No build
# toolchain is needed — CTranslate2 comes as a prebuilt ROCm wheel (below).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ---- CTranslate2-ROCm from the official prebuilt wheel ------------------------
# We DON'T compile CTranslate2. OpenNMT ships ROCm wheels built against ROCm 7.2.1
# (this base is 7.2.x) with GPU kernels for gfx942 + gfx1100 (and more) already
# baked in — no GPU_TARGETS guesswork, and minutes- not hours-long builds. Pick the
# wheel matching this base's CPython, install it FIRST (so faster-whisper below
# reuses it instead of pulling the NVIDIA build from PyPI), then prove it imports.
# NOTE: the download is from github.com, so build in a clean-network environment
# (GitHub Actions) — NOT the SSL-intercepting notebook proxy.
ARG CT2_VERSION=4.8.1
ADD https://github.com/OpenNMT/CTranslate2/releases/download/v${CT2_VERSION}/rocm-python-wheels-Linux.zip /tmp/ct2.zip
RUN python -m zipfile -e /tmp/ct2.zip /tmp/ct2_wheels \
    && PYTAG="$(python -c 'import sys; print(f"cp{sys.version_info.major}{sys.version_info.minor}")')" \
    && WHL="$(find /tmp/ct2_wheels -name "ctranslate2-*${PYTAG}*x86_64*.whl" | head -n 1)" \
    && { [ -n "$WHL" ] || { echo "No ctranslate2 wheel for ${PYTAG} in the zip:"; find /tmp/ct2_wheels -name '*.whl'; exit 1; }; } \
    && echo "Installing ${WHL}" \
    && pip install --no-cache-dir "$WHL" \
    && rm -rf /tmp/ct2.zip /tmp/ct2_wheels \
    && python -c "import ctranslate2; print('CTranslate2', ctranslate2.__version__)"

WORKDIR /app

# Supported gfx arches (match the CTranslate2 GPU_TARGETS and the rocBLAS kernels
# kept below): MI300 gfx942 and W7900/RX7900 gfx1100. This is a build-target list,
# NOT a runtime device signal — the app auto-detects the active GPU via rocminfo.
# Force a specific GPU at `docker run` with OMNICAPTION_GFX_ARCH / OMNICAPTION_HSA_OVERRIDE_GFX_VERSION.
ENV PYTORCH_ROCM_ARCH="gfx942;gfx1100" \
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
RUN python -c "import huggingface_hub; \
               huggingface_hub.snapshot_download('Systran/faster-whisper-large-v3', cache_dir='/opt/hf-cache')"

# Model weights are baked from here on: forbid hub network access at runtime.
# (The container still uses the network for video downloads and the Fireworks
# VLM API - only Hugging Face hub lookups are forced offline.)
ENV HF_HUB_OFFLINE="1"

# ---- Prune heavy ROCm dependencies to meet the <=10 GB gate -------------------
# We delete static archives (.a), LLVM build files, and unused heavy libraries
# (like hipblaslt, rocfft, and migraphx) which are not needed for Whisper or VLM.
RUN find /opt/rocm -name "*.a" -delete \
    && rm -rf /opt/rocm/lib/llvm \
    && rm -rf /opt/rocm/lib/hipblaslt \
    && rm -rf /opt/rocm/lib/rocfft \
    && rm -rf /opt/rocm/lib/migraphx \
    && rm -rf /opt/rocm/lib/librocalution_hip.so* \
    && rm -rf /opt/rocm/lib/librpp.so* \
    && find / -type d -name "__pycache__" -prune -exec rm -rf {} + \
    && rm -rf /root/.cache/*

# ---- Keep only the target arches' rocBLAS kernels ---------------------------
# rocBLAS/Tensile ships precompiled GEMM kernels for every gfx arch. We keep the
# two arches the pipeline actually runs on — MI300 (gfx942) and the W7900/RX7900
# dev+notebook box (gfx1100) — and delete the rest (~1-3 GB): gfx1032/gfx1103/
# gfx1150 are not used. Files without a gfx tag (arch-agnostic indices) are kept;
# the -path form no-ops if a ROCm version lays the library out differently.
# VALIDATE on real hardware (scripts/smoke.sh): on CPU/other GPUs rocBLAS never
# loads these kernels, so only a real gfx942 or gfx1100 run proves it.
RUN find /opt/rocm -type f -path '*/rocblas/library/*' -name '*gfx*' \
        ! -name '*gfx942*' ! -name '*gfx1100*' -delete

# ---- Application source -------------------------------------------------------
# Placed after heavy layers so minor code modifications do not invalidate the build cache
COPY app ./app

# ---- Squashed final stage ----------------------------------------------------
# Flatten the ENTIRE builder filesystem into a single layer. This is the key size
# lever: a layered image (e.g. `FROM rocm/pytorch` + rm + COPY) keeps every file
# ever written — data added in one layer and deleted in a later one still counts,
# and `rm` only writes a whiteout — so re-using the heavy base plus copying our
# dirs back on top ballooned the image to ~23 GB. Squashing onto `scratch`
# collapses all that inter-layer churn (and the base's own bloat) down to the true
# on-disk size (~10 GB before pruning). ffmpeg, libgomp, python, the venv, the
# CTranslate2-ROCm wheel, the pruned ROCm runtime, the baked weights, and the app
# all come from the builder.
FROM scratch
COPY --from=builder / /

WORKDIR /app

ENV PATH="/opt/venv/bin:/opt/rocm/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    LD_LIBRARY_PATH="/usr/local/lib:/opt/rocm/lib" \
    PYTORCH_ROCM_ARCH="gfx942;gfx1100" \
    HF_HOME="/opt/hf-cache" \
    HF_HUB_OFFLINE="1" \
    PYTHONUNBUFFERED="1"

# The eval harness mounts /input and /output at runtime. The synthesis stage
# additionally needs FIREWORKS_API_KEY passed at `docker run -e ...`; without
# it every style deterministically falls back (never crashes, but scores low).
VOLUME ["/input", "/output"]

ENTRYPOINT ["python", "-m", "app.main"]
