# OmniCaption captioner — linux/amd64, AMD ROCm runtime.
# Build: docker build --platform linux/amd64 -t omnicaption-captioner .
#
# The base image ships PyTorch built against ROCm/HIP; CTranslate2-HIP and
# ffmpeg are added on top. Keep the final image <10 GB and cold start <60 s.
FROM --platform=linux/amd64 rocm/pytorch:latest

# ---- OS packages --------------------------------------------------------------
# ffmpeg is required by the ingestion stage for audio extraction.
# git, cmake, and build-essential are required to build CTranslate2 with HIP support.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

# ---- Compile CTranslate2-HIP from source ---------------------------------------
# Target GPU architectures (gfx) matching the AMD matrix.
# We build against the preinstalled ROCm SDK in the base image.
ENV LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH}"

RUN git clone --recursive --branch v4.8.0 https://github.com/OpenNMT/CTranslate2.git \
    && cd CTranslate2 \
    && mkdir build && cd build \
    && cmake -DWITH_HIP=ON -DWITH_MKL=OFF -DOPENMP_RUNTIME=COMP -DCMAKE_BUILD_TYPE=Release .. \
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
# Bake Whisper large-v3 weights into the image so container startup does no network I/O
RUN python -c "from faster_whisper import WhisperModel; \
               WhisperModel('large-v3', download_root='/opt/hf-cache')"
# These layers are cached independently of the app source so code edits do not
# invalidate the (large, slow) weight download.

# ---- Application source -------------------------------------------------------
COPY app ./app

# The eval harness mounts /input and /output at runtime.
VOLUME ["/input", "/output"]

ENTRYPOINT ["python", "-m", "app.main"]
