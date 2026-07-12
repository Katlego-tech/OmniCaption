#!/usr/bin/env bash
# Capture AMD/ROCm compute evidence for the OmniCaption submission, on the gfx1100
# notebook. Runs the already-published image against one clip WITH GPU access,
# samples rocm-smi throughout the run, and saves every artifact under evidence/.
#
# The AMD-compute proof is: the captioner loads Whisper on the ROCm/HIP GPU and
# transcribes there. We capture (a) the container's own proof logs, (b) rocm-smi
# showing GPU utilisation + the container process holding the device during the
# run, and (c) rocminfo/driver info.
#
# Prereqs (on the notebook):
#   - docker can pull the image (daemon already trusts the proxy)
#   - rocminfo / rocm-smi on PATH (they are on the AMD notebook)
#
# Usage (from the repo root on the notebook):
#   FIREWORKS_API_KEY=fw_... \
#     services/captioner/scripts/capture_amd_evidence.sh <image-ref> [clip_url]
# Example:
#   services/captioner/scripts/capture_amd_evidence.sh \
#       docker.io/<your-user>/omnicaption-captioner:latest
set -euo pipefail

IMAGE="${1:?usage: capture_amd_evidence.sh <image-ref> [clip_url]}"
CLIP="${2:-https://storage.googleapis.com/amd-hackathon-clips/1860079-uhd_2560_1440_25fps.mp4}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || echo run)"
OUT="evidence/${STAMP}"
mkdir -p "$OUT/input" "$OUT/output"

echo "== 1/4  static AMD evidence (arch + driver) =="
rocminfo > "$OUT/rocminfo.txt" 2>&1 || echo "rocminfo failed" | tee -a "$OUT/rocminfo.txt"
grep -E 'Name:\s+gfx|Marketing Name' "$OUT/rocminfo.txt" | head
rocm-smi --showproductname --showdriverversion --showvbios \
  > "$OUT/rocm-smi-static.txt" 2>&1 || true

cat > "$OUT/input/tasks.json" <<JSON
[{"task_id":"evidence","video_url":"${CLIP}","styles":["formal","sarcastic","humorous_tech","humorous_non_tech"]}]
JSON

# ROCm device access for the container.
GPU="--device=/dev/kfd --device=/dev/dri --security-opt seccomp=unconfined --group-add video"

echo "== 2/4  sampling rocm-smi every 2s during the run =="
( while true; do
    date -u +%FT%TZ
    rocm-smi --showuse --showmemuse --showpids 2>/dev/null
    echo "----"
    sleep 2
  done ) > "$OUT/gpu-during-run.log" 2>&1 &
SAMPLER=$!
trap 'kill "$SAMPLER" 2>/dev/null || true' EXIT

echo "== 3/4  running the captioner on the GPU =="
# shellcheck disable=SC2086
docker run --rm $GPU \
  ${FIREWORKS_API_KEY:+-e FIREWORKS_API_KEY=${FIREWORKS_API_KEY}} \
  -v "$PWD/$OUT/input:/input:ro" -v "$PWD/$OUT/output:/output" \
  "$IMAGE" 2>&1 | tee "$OUT/container.log"

kill "$SAMPLER" 2>/dev/null || true

echo
echo "== 4/4  AMD-compute proof (from the container log) =="
if grep -E 'Active device: cuda|ROCm gfx arch detected:|ROCm HIP device total memory:|Loading Whisper .* on cuda' "$OUT/container.log"; then
  echo "  >> GPU PROOF FOUND above."
else
  echo "  !! No GPU proof lines. The container likely ran on CPU — check that"
  echo "     /dev/kfd is exposed and rocminfo reports gfx1100. See troubleshooting."
fi
echo
echo "== evidence bundle: $OUT =="
ls -R "$OUT"
echo
echo "Submit: container.log (proof lines), gpu-during-run.log (rocm-smi + the"
echo "container PID holding the GPU), rocminfo.txt, rocm-smi-static.txt, output/results.json"
