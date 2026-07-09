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

_Status as of 2026-07-09 (Tumo via Claude, T097). Evidence cited per item; unchecked items list
the blocking task._

- [ ] Docker image published to a **public registry** (Docker Hub or GHCR). — **blocked on T099**
      (build, tag, push; needs registry login — Katlego).
- [ ] Image manifest is **linux/amd64**. — verified at push time as part of **T099**.
- [ ] **AMD compute proof** — logs / evidence the run used AMD compute. — **blocked on T095**.
      Two-part proof now that the stack is hybrid: (a) ROCm/HIP device logs for local Whisper STT,
      (b) Fireworks AI request logs (MI300X-backed platform) for VLM synthesis.
- [x] `/output/results.json` is **schema-valid**: every task, every requested style present.
      — contract tests (T073/T074) green; verified clean end-to-end run 2026-07-09 (STATUS log).
- [ ] Container **starts within 60 s** and **finishes ≤10 min** on the baseline batch. — needs a
      timed run of the **built** container (T099/T102). ⚠️ Whisper weights are not yet baked into
      the image and the Dockerfile sets `HF_HUB_OFFLINE=1` — startup would currently fail/blow the
      budget; fix in T099.
- [ ] Per-request latency **< 30 s**. — soft-guarded in the orchestrator; ⚠️ the synthesis HTTP
      timeout is 60 s to absorb reasoning-VLM latency, so a slow style can breach 30 s. Needs a
      measured run (T102) and, if breached, a tighter per-style budget.
- [ ] Image is **≤ 10 GB**. — measured at build time (T099). Note: `requirements.txt` still
      installs `transformers`/`accelerate`/`bitsandbytes` for the legacy local-VLM loader; prune
      if the image runs oversize.
- [x] Process **exits 0** on success (and on partial failure). — enforced in `app/main.py`
      (T081) + unit test T075; verified in the end-to-end run.
- [x] All four styles (`formal`, `sarcastic`, `humorous_tech`, `humorous_non_tech`) produce
      distinct, on-tone captions. — verified end-to-end 2026-07-09, all four cleanly populated
      (STATUS log).
- [ ] `main` is green; PRs merged; docs current. — final sweep is **T102** after T095/T099 land.

See [deployment](deployment.md) for build/push mechanics and [11-phase0-runbook](11-phase0-runbook.md)
for the local verification run.
