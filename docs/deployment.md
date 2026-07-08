# Deployment

How to build, tag, push, and smoke-test the OmniCaption container. The image must be **linux/amd64**,
**≤10 GB**, start within **60 s**, and demonstrably use AMD compute
([06-judging-criteria](06-judging-criteria.md)).

## 1. Build the linux/amd64 image

Export the host GPU's gfx arch before building so CTranslate2-HIP compiles for the right target
([05-amd-rocm-optimization](05-amd-rocm-optimization.md)):

```bash
export PYTORCH_ROCM_ARCH=gfx942          # match your target GPU

docker buildx build \
  --platform linux/amd64 \
  --build-arg PYTORCH_ROCM_ARCH=$PYTORCH_ROCM_ARCH \
  -t omnicaption:local .
```

Confirm the manifest is single-arch linux/amd64 and the image is ≤10 GB:

```bash
docker image inspect omnicaption:local --format '{{.Os}}/{{.Architecture}} {{.Size}}'
```

## 2. Tag for a public registry

Pick one public registry. The judges must be able to pull it.

**Docker Hub:**

```bash
docker tag omnicaption:local <dockerhub-user>/omnicaption:v1
```

**GHCR (matches the repo `Katlego-tech/OmniCaption`):**

```bash
docker tag omnicaption:local ghcr.io/katlego-tech/omnicaption:v1
```

## 3. Push

```bash
# Docker Hub
docker login
docker push <dockerhub-user>/omnicaption:v1

# or GHCR
echo $GHCR_TOKEN | docker login ghcr.io -u katlego-tech --password-stdin
docker push ghcr.io/katlego-tech/omnicaption:v1
```

Make sure the package/repository is set to **public** so the harness can pull it anonymously.

## 4. Local smoke test

Place a `tasks.json` under `./input`, then:

```bash
docker run --rm \
  -v ./input:/input \
  -v ./output:/output \
  omnicaption:local          # add ROCm device flags for your host GPU
```

Verify:

- `./output/results.json` exists and is **schema-valid** — every task, every requested style present.
- The container **exited 0** (`echo $?`).
- Logs show **AMD/ROCm** was used, not CPU fallback (disqualifier if absent).
- Startup was within **60 s** and the batch finished **≤10 min**.

Run the three baseline clips (v1 boulevard, v2 kitten, v3 office worker) as the standing smoke test —
see [11-phase0-runbook](11-phase0-runbook.md). Then work the
[06-judging-criteria](06-judging-criteria.md) submission checklist before publishing the final tag.
