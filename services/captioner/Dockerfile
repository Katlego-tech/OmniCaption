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
# ffmpeg is required by the ingestion stage for audio extraction.
# git, cmake, and build-essential are required to build CTranslate2 with HIP support.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git build-essential cmake libomp-dev \
    && ln -sf $(find /usr/lib -name "libomp.so" | head -n 1) /usr/local/lib/libomp.so \
    && rm -rf /var/lib/apt/lists/*

# ---- Compile CTranslate2-HIP from source ---------------------------------------
# Target GPU architectures (gfx) matching the AMD matrix.
# We build against the preinstalled ROCm SDK in the base image.
ENV LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH}"

RUN git clone --recursive --branch v4.8.0 https://github.com/OpenNMT/CTranslate2.git \
    && cd CTranslate2 \
    && mkdir build && cd build \
    && CC=/opt/rocm/lib/llvm/bin/clang CXX=/opt/rocm/lib/llvm/bin/clang++ cmake \
       -DCMAKE_CXX_COMPILER=/opt/rocm/lib/llvm/bin/clang++ \
       -DCMAKE_C_COMPILER=/opt/rocm/lib/llvm/bin/clang \
       -DWITH_HIP=ON -DWITH_MKL=OFF -DOPENMP_RUNTIME=COMP -DCMAKE_BUILD_TYPE=Release .. \
    && make -j$(nproc) install \
    && cd ../python \
    && pip install --no-cache-dir -r install_requirements.txt \
    && python setup.py bdist_wheel \
    && pip install --no-cache-dir dist/*.whl \
    && cd ../.. && rm -rf CTranslate2

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
RUN python -c "import huggingface_hub; \
               huggingface_hub.snapshot_download('Systran/faster-whisper-large-v3', cache_dir='/opt/hf-cache')"

# Model weights are baked from here on: forbid hub network access at runtime.
# (The container still uses the network for video downloads and the Fireworks
# VLM API - only Hugging Face hub lookups are forced offline.)
ENV HF_HUB_OFFLINE="1"

# ---- ROCm libraries kept intact ----------------------------------------------
# The heavy-dependency prune (deleting hipblaslt/rocfft/migraphx/llvm) and the
# gfx942-only rocBLAS kernel prune were REMOVED: they made the image MI300-only
# and broke runs on other AMD hardware (e.g. rocBLAS falling back so faster-whisper
# raised "No SGEMM backend on CPU" on Katlego's laptop). The Dockerfile multi-stage
# rework already brings the final image to ~7 GB, so the size-motivated pruning is
# no longer needed to satisfy the <=10 GB gate. Only harmless build artifacts are
# cleaned to keep the image tidy without removing any runtime ROCm data.
RUN find / -type d -name "__pycache__" -prune -exec rm -rf {} + \
    && rm -rf /root/.cache/*

# ---- Application source -------------------------------------------------------
# Placed after heavy layers so minor code modifications do not invalidate the build cache
COPY app ./app

# ---- Clean Runtime Stage -----------------------------------------------------
FROM rocm/pytorch:latest

# Install essential runtime shared libraries and tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libomp-dev \
    && rm -rf /var/lib/apt/lists/*

# Remove base unpruned directories before copying our optimized versions
RUN rm -rf /opt/rocm /opt/venv

# Copy the streamlined Python environment and custom compiled binaries
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /usr/local /usr/local

# Copy the full ROCm runtime environment (kernels for all gfx arches retained)
COPY --from=builder /opt/rocm /opt/rocm

# Copy the baked Hugging Face model weights cache
COPY --from=builder /opt/hf-cache /opt/hf-cache

# Copy the application code
COPY --from=builder /app /app

WORKDIR /app

ENV PATH="/opt/venv/bin:/opt/rocm/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    LD_LIBRARY_PATH="/usr/local/lib:/opt/rocm/lib" \
    PYTORCH_ROCM_ARCH="gfx942;gfx1100;gfx1032;gfx1103;gfx1150" \
    HF_HOME="/opt/hf-cache" \
    HF_HUB_OFFLINE="1" \
    PYTHONUNBUFFERED="1"

# The eval harness mounts /input and /output at runtime. The synthesis stage
# additionally needs FIREWORKS_API_KEY passed at `docker run -e ...`; without
# it every style deterministically falls back (never crashes, but scores low).
VOLUME ["/input", "/output"]

ENTRYPOINT ["python", "-m", "app.main"]