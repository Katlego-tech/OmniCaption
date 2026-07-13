# OmniCaption — Build, Publish & Submit (for Katlego)

This is the **exact, in-order** checklist to build the AMD/ROCm captioner image, push it
to Docker Hub, prove it runs on the GPU, and submit.

> **Status 2026-07-12 evening:** Steps 1–4 below are ✅ DONE — the image is built (9.67 GB,
> gate passed in CI), pushed to **`docker.io/katlegotech/omnicaption-captioner:latest`**, and
> the Docker Hub repo is public. **What remains, in order: Step 4b (bake the Fireworks key —
> NEW, judging-critical), Step 5 (GPU smoke re-run), Step 6 (submit the form).**

---

## Step 4b — Bake the Fireworks key (NEW — judging-critical)

The judging FAQ says the container is run **bare**: _"Run the container without local files
or manual setup"_, _"No private secrets are required."_ Our synthesis stage needs
`FIREWORKS_API_KEY` — without it in the image, **every caption falls back to generic text
and the accuracy gate fails.** Team decision (Tumo, 2026-07-12): bake a **fresh, disposable**
key into the public image and rotate it after judging.

1. Fireworks dashboard → create a **new** API key (name it `omnicaption-judging`).
2. On a docker-logged-in machine (an account that can push to `katlegotech/…`), save the key
   to a file `keyfile` (no trailing newline problems: `printf '%s' 'fw_...' > keyfile`), then:

   ```bash
   # A derived, ENV-only image: zero new blobs, push takes seconds, the CI-measured
   # 9.67 GB stays valid. Dockerfile content:
   #   FROM docker.io/katlegotech/omnicaption-captioner:latest
   #   ARG FIREWORKS_API_KEY
   #   ENV FIREWORKS_API_KEY="${FIREWORKS_API_KEY}" OMNICAPTION_DOWNLOAD_TIMEOUT_S=180
   docker build --build-arg FIREWORKS_API_KEY="$(cat keyfile)" \
     -t docker.io/katlegotech/omnicaption-captioner:latest <dir-with-that-Dockerfile>
   docker push docker.io/katlegotech/omnicaption-captioner:latest
   rm keyfile
   ```

   (Alternative without local docker: add the key as a `FIREWORKS_API_KEY` **repo secret**
   — needs repo admin — and re-run the publish workflow; the workflow + Dockerfile on the
   fix branch forward it as a build-arg. Full rebuild, ~20–30 min.)
3. **After judging:** delete the key in the Fireworks dashboard.

`OMNICAPTION_DOWNLOAD_TIMEOUT_S=180` rides along because the judged clips are 1440p–4K and
a real run lost every caption when a 4K download hit the code's old 60 s default.

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

## Captions via Gemma 4 (dedicated Fireworks deployment)

The default VLM is `kimi-k2p6` (serverless — cheap, always on, already proven end-to-end).
**Gemma 4 is a *dedicated* Fireworks deployment: ~$28/hr, and the hackathon credit is ~$50
(~1.75 hr).** So treat it like a stopwatch — do all prep first, run in one short batch, undeploy.

**Before deploying Gemma 4 (while it's OFF — free):**
1. Captioner image built and the pipeline verified with kimi-k2p6 (done).
2. Final `tasks.json` (every judged clip) staged in `services/api/data/input/`.
3. `FIREWORKS_API_KEY` in `./.env` (already set; the script reads it, never prints it).

**Live window (aim for minutes):**
1. Deploy Gemma 4 on Fireworks → copy its deployment model id
   (looks like `accounts/<account>/deployedModels/<id>`).
2. Run the batch (auto-pings the deployment first, then runs every clip):
   ```bash
   services/captioner/scripts/run_gemma4_batch.sh accounts/<account>/deployedModels/<id>
   ```
3. Check the printed `results.json`.
4. **Undeploy Gemma 4 immediately.**

Only the model id changes — same key, same API URL, same code, both audio and no-audio clips.
Retries don't add cost (dedicated deployments bill by the hour, not per call). If the judged run
also uses Gemma 4, it must be **deployed during judging** — coordinate the deploy/undeploy timing.

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
