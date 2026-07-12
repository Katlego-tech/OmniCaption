#!/usr/bin/env bash
# Build, tag, and push the linux/amd64 captioner image to a public registry —
# and REFUSE to push unless it is strictly < 10 GB (the judging gate).
#
# "GB" is decimal (10^9), the unit `docker images` prints and the strictest
# reading of the "< 10 GB" limit. An image shown as "10.0GB"+ is rejected.
#
# Usage:
#   services/captioner/scripts/build_push.sh docker.io/<user>        [tag]
#   services/captioner/scripts/build_push.sh ghcr.io/<org>           [tag]
#   NO_PUSH=1 services/captioner/scripts/build_push.sh <registry>    # build+measure only
#
# Log in first: `docker login` (Docker Hub) or `docker login ghcr.io`.
set -euo pipefail

REGISTRY="${1:?usage: build_push.sh <registry/namespace> [tag]   e.g. docker.io/yourname}"
TAG="${2:-latest}"
NAME="omnicaption-captioner"
REF="${REGISTRY%/}/${NAME}:${TAG}"
here="$(cd "$(dirname "$0")/.." && pwd)"   # services/captioner
GATE=10000000000   # 10 GB decimal, strict (<)

echo "== build ${REF} (linux/amd64) =="
# Bake the Fireworks key when the caller provides one (judge runs the container
# with no -e flags, so the key must live in the image). Empty/unset -> the app
# falls back deterministically; a warning makes that impossible to miss.
if [ -z "${FIREWORKS_API_KEY:-}" ]; then
  echo "WARNING: FIREWORKS_API_KEY is not set — the pushed image will produce"
  echo "         FALLBACK captions on a bare 'docker run' (low score)."
fi
docker build --platform linux/amd64 \
  ${FIREWORKS_API_KEY:+--build-arg FIREWORKS_API_KEY="$FIREWORKS_API_KEY"} \
  -t "$REF" -t "${NAME}:${TAG}" "$here"

bytes="$(docker image inspect "$REF" --format '{{.Size}}')"
gb="$(awk -v b="$bytes" 'BEGIN{printf "%.2f", b/1000000000}')"
gib="$(awk -v b="$bytes" 'BEGIN{printf "%.2f", b/1073741824}')"
echo "== size: ${gb} GB (${gib} GiB) — gate: strictly < 10 GB =="

if ! awk -v b="$bytes" -v g="$GATE" 'BEGIN{exit !(b < g)}'; then
  echo "ABORT: ${gb} GB is NOT < 10 GB. Prune more (see the gfx942/rocBLAS step in the"
  echo "       Dockerfile and STATUS.md) before pushing. Not pushing."
  exit 1
fi
echo "OK: ${gb} GB < 10 GB."

if [ -n "${NO_PUSH:-}" ]; then
  echo "NO_PUSH set — built and measured only, skipping push."
  exit 0
fi

echo "== push ${REF} =="
docker push "$REF"
echo
echo "PUSHED: ${REF}"
echo "NEXT: record this pull URL in docs/06-judging-criteria.md (submission checklist)"
echo "      and make the repository/package PUBLIC so the judges can pull it."
