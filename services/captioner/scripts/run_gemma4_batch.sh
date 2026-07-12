#!/usr/bin/env bash
# Run the FULL captioner batch against a Fireworks **Gemma 4 dedicated deployment**,
# then remind you to UNDEPLOY it. Gemma 4 is not serverless — it bills ~$28/hr while
# deployed, and the hackathon credit is ~$50 (~1.75 hr). KEEP THIS WINDOW SHORT.
#
# Do everything below BEFORE deploying Gemma 4 (while it is OFF):
#   1. Build + verify the captioner image (kimi-k2p6 already proves the pipeline).
#   2. Stage your FINAL tasks.json (every judged clip) in the input dir.
#   3. Put FIREWORKS_API_KEY in ./.env (or export it). This script never prints it.
#
# Then, and only then:
#   4. Deploy Gemma 4 on Fireworks, copy its deployment model id.
#   5. Run this script.  6. UNDEPLOY the moment it finishes.
#
# Usage (from the repo root):
#   scripts/run_gemma4_batch.sh <GEMMA4_MODEL_ID> [input_dir] [output_dir] [image]
# Example:
#   services/captioner/scripts/run_gemma4_batch.sh \
#       accounts/your-account/deployedModels/gemma4-xxxxxx
set -euo pipefail

MODEL="${1:?usage: run_gemma4_batch.sh <fireworks Gemma4 deployment model id> [input_dir] [output_dir] [image]}"
INPUT_DIR="${2:-services/api/data/input}"
OUTPUT_DIR="${3:-services/api/data/output}"
IMAGE="${4:-omnicaption-captioner:latest}"
API_URL="${OMNICAPTION_FIREWORKS_API_URL:-https://api.fireworks.ai/inference/v1}"

# Load the key from ./.env if not already exported. Never echoed.
if [ -z "${FIREWORKS_API_KEY:-}" ] && [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${FIREWORKS_API_KEY:?FIREWORKS_API_KEY not set (export it or put it in ./.env)}"

IN_ABS="$(cd "$INPUT_DIR" && pwd)"
OUT_ABS="$(cd "$OUTPUT_DIR" && pwd)"
n_tasks="$(grep -o '"task_id"' "$IN_ABS/tasks.json" 2>/dev/null | wc -l | tr -d ' ')"

# GPU flags only when a ROCm device is present (notebook); harmless to omit on CPU.
gpu=""
if [ -e /dev/kfd ]; then
  gpu="--device=/dev/kfd --device=/dev/dri --security-opt seccomp=unconfined --group-add video"
fi

echo "== Gemma 4 batch run =="
echo "  model : $MODEL"
echo "  image : $IMAGE   ($([ -n "$gpu" ] && echo 'ROCm GPU' || echo 'CPU'))"
echo "  input : $IN_ABS  (${n_tasks:-?} task(s))"
echo "  output: $OUT_ABS"
echo

# --- pre-check: confirm the deployment is live BEFORE running the whole batch ---
# A 1-token text ping. Costs ~nothing; catches a wrong model id / not-yet-live
# deployment before Whisper churns through every clip.
echo "== pre-check: pinging the deployment =="
code="$(curl -s -o /dev/null -w '%{http_code}' -m 45 "$API_URL/chat/completions" \
  -H "Authorization: Bearer $FIREWORKS_API_KEY" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":1}")"
if [ "$code" != "200" ]; then
  echo "  FAILED (HTTP $code) — is Gemma 4 deployed and is the model id correct? Aborting."
  exit 1
fi
echo "  deployment reachable (HTTP 200)."
echo "  >> Gemma 4 is billing now. Running the batch..."
echo

MSYS_NO_PATHCONV=1 docker run --rm $gpu \
  -e FIREWORKS_API_KEY="$FIREWORKS_API_KEY" \
  -e OMNICAPTION_FIREWORKS_VLM_MODEL="$MODEL" \
  -e OMNICAPTION_FIREWORKS_API_URL="$API_URL" \
  -v "$IN_ABS:/input:ro" -v "$OUT_ABS:/output" \
  "$IMAGE"

echo
echo "== results ($OUT_ABS/results.json) =="
cat "$OUT_ABS/results.json" 2>/dev/null || echo "(no results.json written)"
echo
echo "############################################################"
echo "#  UNDEPLOY Gemma 4 on Fireworks NOW to stop the billing.  #"
echo "############################################################"
