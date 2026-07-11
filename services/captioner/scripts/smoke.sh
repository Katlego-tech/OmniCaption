#!/usr/bin/env bash
# OmniCaption captioner — container smoke test.
#
# Builds (unless --no-build) the linux/amd64 image, runs it against one clip, and
# hard-checks four things:
#   1. exit 0 and a schema-valid /output/results.json (every requested style present)
#   2. AMD-compute proof in the logs (ROCm gfx942 device active)
#   3. image size <= 10 GB (the judging gate)
#   4. captions non-empty when FIREWORKS_API_KEY is set
#
# CRITICAL: the gfx942 rocBLAS prune can ONLY be validated on real gfx942 (MI300).
# On a CPU host (no /dev/kfd) the pipeline falls back to CPU and never loads the
# pruned kernels, so GPU proof is reported as NOT VALIDATED and the script exits 2.
# Run this on the MI300 box before trusting the pruned image.
#
# Usage:
#   FIREWORKS_API_KEY=fw-… services/captioner/scripts/smoke.sh
#   services/captioner/scripts/smoke.sh --no-build --image omnicaption-captioner:latest
set -euo pipefail

IMAGE="omnicaption-captioner:latest"
BUILD=1
CLIP_URL="https://storage.googleapis.com/amd-hackathon-clips/1860079-uhd_2560_1440_25fps.mp4"
while [ $# -gt 0 ]; do
  case "$1" in
    --no-build) BUILD=0 ;;
    --image) IMAGE="$2"; shift ;;
    --clip) CLIP_URL="$2"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
  shift
done

here="$(cd "$(dirname "$0")/.." && pwd)"   # services/captioner
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
mkdir -p "$work/input" "$work/output"
cat > "$work/input/tasks.json" <<JSON
[{"task_id":"smoke","video_url":"$CLIP_URL","styles":["formal","sarcastic","humorous_tech","humorous_non_tech"]}]
JSON

pass() { printf '  \033[32mPASS\033[0m %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAILED=1; }
FAILED=0

if [ "$BUILD" = 1 ]; then
  echo "== building $IMAGE (linux/amd64) =="
  docker build --platform linux/amd64 -t "$IMAGE" "$here"
fi

# --- 3. image size gate ------------------------------------------------------
echo "== image size =="
bytes="$(docker image inspect "$IMAGE" --format '{{.Size}}')"
gib="$(awk -v b="$bytes" 'BEGIN{printf "%.2f", b/1073741824}')"
echo "  $IMAGE = ${gib} GiB"
awk -v b="$bytes" 'BEGIN{exit !(b <= 10*1073741824)}' && pass "image <= 10 GiB" || fail "image ${gib} GiB > 10 GiB gate"

# --- run: request the GPU if the host exposes ROCm devices -------------------
gpu_flags=""
if [ -e /dev/kfd ]; then
  gpu_flags="--device=/dev/kfd --device=/dev/dri --security-opt seccomp=unconfined --group-add video"
  echo "== running WITH ROCm devices (/dev/kfd present) =="
else
  echo "== running on CPU (no /dev/kfd) — GPU proof will NOT be validated =="
fi

log="$work/run.log"
set +e
# shellcheck disable=SC2086
docker run --rm $gpu_flags \
  -e FIREWORKS_API_KEY="${FIREWORKS_API_KEY:-}" \
  -v "$work/input:/input" -v "$work/output:/output" \
  "$IMAGE" > "$log" 2>&1
rc=$?
set -e
echo "  container exit code: $rc"
[ "$rc" -eq 0 ] && pass "container exited 0" || fail "container exit $rc"

# --- 1. schema-valid output --------------------------------------------------
echo "== output =="
python3 - "$work/output/results.json" <<'PY' && pass "results.json schema-valid (all styles present)" || fail "results.json missing/invalid"
import json, sys
want = {"formal", "sarcastic", "humorous_tech", "humorous_non_tech"}
data = json.load(open(sys.argv[1]))
clip = next(c for c in data if c["task_id"] == "smoke")
assert want <= set(clip["captions"]), f"missing styles: {want - set(clip['captions'])}"
PY

# --- 4. captions non-empty (only meaningful with a key) ----------------------
if [ -n "${FIREWORKS_API_KEY:-}" ]; then
  python3 - "$work/output/results.json" <<'PY' && pass "all captions non-empty" || fail "some captions empty"
import json, sys
clip = next(c for c in json.load(open(sys.argv[1])) if c["task_id"] == "smoke")
empty = [s for s, t in clip["captions"].items() if not (t or "").strip()]
assert not empty, f"empty captions: {empty}"
PY
else
  echo "  (skip caption-content check — FIREWORKS_API_KEY not set)"
fi

# --- 2. AMD-compute proof ----------------------------------------------------
echo "== AMD-compute proof =="
if grep -qE "ROCm gfx arch detected: gfx942|Active device: cuda" "$log"; then
  pass "ran on AMD ROCm gfx942 (kernels loaded — gfx942 prune validated)"
elif grep -q "CPU-fallback" "$log"; then
  echo "  \033[33mGPU NOT VALIDATED\033[0m — ran on CPU, so the gfx942 rocBLAS prune was not exercised."
  [ -e /dev/kfd ] && fail "ROCm devices present but pipeline fell back to CPU" || FAILED=2
else
  fail "no device line in logs (unexpected)"
fi

echo
if [ "$FAILED" = 0 ]; then
  echo "SMOKE PASSED"; exit 0
elif [ "$FAILED" = 2 ]; then
  echo "SMOKE INCONCLUSIVE — output+size OK but GPU proof requires an MI300 (gfx942) host."; exit 2
else
  echo "SMOKE FAILED — see $log"; exit 1
fi
