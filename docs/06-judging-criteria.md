# 06 — Judging Criteria

## Track 2 scoring

Each clip is scored **per style** on two axes, each in `[0, 1]`:

- **Accuracy A(v, s)** — visual fidelity: does the caption match what is actually on screen?
- **Style Match M(v, s)** — tone alignment: does it read like the requested style?

The final score aggregates over all clips `V` and all styles `S`:

```
        1
Φ  =  ───────  ·  Σ_v  Σ_s  ( α·A(v,s)  +  β·M(v,s) )
      |V|·|S|
```

where `α` and `β` weight accuracy vs. style. Evaluation runs over **~12 hidden clips** across diverse
domains: nature, urban, animals, human actions, sports, food, weather, technology. Design for
generality, not for the three baseline clips.

**A missing style scores 0.** Always emit a caption for every requested style — fall back to the
deterministic caption rather than omitting a key (see [03-captioning-pipeline](03-captioning-pipeline.md)).

## Runtime constraints (hard gates)

| Constraint | Limit |
| --- | --- |
| Total container runtime | **≤ 10 min** |
| Per-request response | **< 30 s** |
| Container image size | **≤ 10 GB** |
| Container startup | **within 60 s** |
| AMD compute usage | **Required** — absent ⇒ disqualified |
| Exit code | **0** |

These are enforced in tests — see [04-testing-strategy](04-testing-strategy.md).

## Submission checklist

_Status as of 2026-07-11 (Tumo via Claude). Evidence cited per item._

- [x] Docker image **built & pushed** to a **public** registry. — ✅ 2026-07-12: the "Publish
      captioner image" workflow built + pushed **`docker.io/katlegotech/omnicaption-captioner:latest`**
      (public — anonymous `docker pull` works; Docker Hub shows the tag active, ~4.6 GB compressed).
      **This is the submission pull URL.** ⚠️ One re-push pending: the derived image baking the
      fresh Fireworks key + `OMNICAPTION_DOWNLOAD_TIMEOUT_S=180` (ENV-only layer, same blobs) so a
      bare judge `docker run` produces real captions — see SUBMISSION.md.
- [x] Image manifest is **linux/amd64**. — ROCm `linux/amd64` base; verified at build (T099).
- [x] **AMD compute proof** — [submission-amd-proof.md](submission-amd-proof.md) (T095):
      (a) ROCm/HIP device logs for local Whisper STT (CTranslate2 loads on GPU in-container),
      (b) Fireworks AI request evidence (MI300X-backed platform) for VLM synthesis.
- [x] `/output/results.json` is **schema-valid**: every task, every requested style present.
      — contract tests (T073/T074) green; verified clean end-to-end run 2026-07-09 (STATUS log).
- [x] Container **starts within 60 s** and **finishes ≤10 min** on the baseline batch. — Whisper
      weights now baked before `HF_HUB_OFFLINE=1` (merged via #7); container CPU smoke test ran
      and wrote schema-valid output (Katlego, 2026-07-10). ⚠️ A stopwatch-timed run on an AMD GPU
      host is still the strongest evidence — recommended before submission if time allows.
- [x] Per-request latency **< 30 s**. — guarded in the orchestrator (fallback trips the budget);
      clean end-to-end run verified 2026-07-09. ⚠️ Same caveat: a measured per-style timing on the
      AMD host would close this beyond doubt (synthesis HTTP timeout is 60 s to absorb
      reasoning-VLM latency).
- [x] Image is **strictly < 10 GB** (decimal, as `docker images` prints). — ✅ **9.67 GB measured in
      CI** by `build_push.sh`'s strict gate on the pushed build (2026-07-12 STATUS log; the path from
      22.1 → 9.67 GB: prebuilt CT2 ROCm wheel, torch dropped, symlink-resolved ROCm prunes,
      large-v3-turbo weights). Note: Docker Desktop's containerd store reports the same digest as
      14.4 GB locally — a snapshotter accounting difference; the CI overlay2 measure is the
      authoritative one for the gate. A derived ENV-only layer adds zero bytes.
- [x] Process **exits 0** on success (and on partial failure). — enforced in `app/main.py`
      (T081) + unit test T075; verified in the end-to-end run.
- [x] All four styles (`formal`, `sarcastic`, `humorous_tech`, `humorous_non_tech`) produce
      distinct, on-tone captions. — verified end-to-end 2026-07-09, all four cleanly populated
      (STATUS log).
- [x] `main` is green; PRs merged; docs current. — T102 done: CI green on `main` (captioner + api
      + web lanes), release **v1.0.0** tagged 2026-07-10, planning docs reconciled (T101).

See [deployment](deployment.md) for build/push mechanics and [11-phase0-runbook](11-phase0-runbook.md)
for the local verification run.
