# OmniCaption — Build, Publish & Submit (for Katlego)

This is the **exact, in-order** checklist to build the AMD/ROCm captioner image, push it
to Docker Hub, prove it runs on the GPU, and submit. No local Docker build needed — GitHub
builds it for you. Just follow the steps top to bottom.

> Status of the code: the gfx1100 fix + prebuilt-CTranslate2-ROCm-wheel Dockerfile + the
> publish workflow are all on `main`. You do NOT need to touch the Dockerfile unless step 3
> tells you to.

---

## Step 1 — Create a Docker Hub access token (once)

1. Log in at https://hub.docker.com → **Account Settings → Security → New Access Token**.
2. Description: `omnicaption-ci`. Permissions: **Read & Write**. Click **Generate**.
3. **Copy the token now** (you can't see it again).

## Step 2 — Add two GitHub secrets (once)

In the repo on GitHub → **Settings → Secrets and variables → Actions → New repository secret**.
Add both:

| Name | Value |
|------|-------|
| `DOCKERHUB_USERNAME` | your Docker Hub username |
| `DOCKERHUB_TOKEN` | the token from Step 1 |

## Step 3 — Run the publish workflow (this builds + pushes the image)

1. GitHub → **Actions** tab → left sidebar → **"Publish captioner image"**.
2. Click **Run workflow** (right side) → branch `main` → tag `latest` → **Run workflow**.
3. Wait ~15–30 min. Watch the **"Build, enforce <10 GB gate, and push"** step.

**Three possible outcomes:**

- ✅ **It pushes.** The log ends with `PUSHED: docker.io/<you>/omnicaption-captioner:latest`.
  That URL is your image. Go to Step 4.

- ❌ **It fails with `ABORT: X GB is NOT < 10 GB`.** The image is too big. Do the
  **gfx1100-only fallback** (see box below), commit, and re-run this step.

- ❌ **It fails on `No ctranslate2 wheel for cp312`** or a disk-space error. Stop and send me
  (Tumo/Claude) the failing log — it's a known-possible snag with a quick fix.

> ### Fallback: shrink the image to gfx1100-only (if the <10 GB gate fails)
> The judge/notebook is gfx1100, so we can drop the gfx942 kernels to save ~1–3 GB.
> Edit `services/captioner/Dockerfile`, find the rocBLAS prune line, and remove `gfx942`:
>
> ```dockerfile
> # before:
> RUN find /opt/rocm -type f -path '*/rocblas/library/*' -name '*gfx*' \
>         ! -name '*gfx942*' ! -name '*gfx1100*' -delete
> # after (keep gfx1100 only):
> RUN find /opt/rocm -type f -path '*/rocblas/library/*' -name '*gfx*' \
>         ! -name '*gfx1100*' -delete
> ```
> Commit to a branch, open a PR, merge, then re-run Step 3.

## Step 4 — Make the Docker Hub repo public

Docker Hub → your `omnicaption-captioner` repo → **Settings → Make public**. Judges must be
able to `docker pull` it without logging in.

## Step 5 — Prove it runs on the GPU (on the gfx1100 notebook)

This is the ONE thing GitHub can't do (it has no AMD GPU). On the notebook terminal:

```bash
docker pull docker.io/<you>/omnicaption-captioner:latest
cd OmniCaption   # the repo checkout on the notebook
bash services/captioner/scripts/smoke.sh --no-build \
     --image docker.io/<you>/omnicaption-captioner:latest
```

- `docker pull` just downloads the finished image — it does NOT hit GitHub/HuggingFace, so
  the notebook's SSL proxy won't get in the way.
- Look for **`SMOKE PASSED`** and a log line **`ROCm gfx arch detected: gfx1100`** /
  **`Active device: cuda`**. That's your AMD-compute proof.
- If it says `No SGEMM backend on CPU` again, send me the log — but the arch-detection fix
  should prevent it.

> If `smoke.sh` doesn't accept `--image`, just run the image directly:
> ```bash
> docker run --rm --device=/dev/kfd --device=/dev/dri \
>   --security-opt seccomp=unconfined --group-add video \
>   -e FIREWORKS_API_KEY=$FIREWORKS_API_KEY \
>   -v "$PWD/services/captioner/tests/fixtures:/input:ro" -v "$PWD/out:/output" \
>   docker.io/<you>/omnicaption-captioner:latest
> ```
> and check `out/results.json` plus the `Active device: cuda` log line.

## Step 6 — Submit

Submit the **public Docker Hub pull URL** from Step 3, e.g.
`docker.io/<you>/omnicaption-captioner:latest`, per the hackathon form. Record it in
`docs/06-judging-criteria.md` too.

---

## Quick reference — what runs where

| Task | Where | Why |
|------|-------|-----|
| Build image | **GitHub Actions** | clean network (notebook proxy blocks github/HF); no local disk limit |
| Push to Docker Hub | **GitHub Actions** | uses your two secrets |
| `< 10 GB` gate | **GitHub Actions** | `build_push.sh` refuses to push a ≥10 GB image |
| GPU smoke test | **gfx1100 notebook** | only place with a real AMD GPU |
| Submit URL | you | the public Docker Hub ref |

**Open risk:** the two-arch image size is unmeasured until Step 3 runs. If it's ≥10 GB, use
the gfx1100-only fallback in Step 3.
