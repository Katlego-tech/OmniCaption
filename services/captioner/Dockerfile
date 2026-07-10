# OmniCaption captioner — linux/amd64, AMD ROCm runtime.
# Build: docker build --platform linux/amd64 -t omnicaption-captioner .
#
# The base image ships PyTorch built against ROCm/HIP; CTranslate2 and ffmpeg
# are added on top. Keep the final image <10 GB and cold start <60 s.
FROM --platform=linux/amd64 rocm/pytorch:latest

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
# VLM API — only Hugging Face hub lookups are forced offline.)
ENV HF_HUB_OFFLINE="1"

# ---- Application source -------------------------------------------------------
COPY app ./app

# The eval harness mounts /input and /output at runtime. The synthesis stage
# additionally needs FIREWORKS_API_KEY passed at `docker run -e ...`; without
# it every style deterministically falls back (never crashes, but scores low).
VOLUME ["/input", "/output"]

ENTRYPOINT ["python", "-m", "app.main"]
