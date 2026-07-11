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

- [ ] Docker image **built & pushed** to a **public** registry. — Previously built and squashed to
      9.58 GB (Katlego, T099), but the moving `rocm/pytorch:latest` base has since grown the image to
      **10.28 GB** (over the gate). Landed two size cuts — `__pycache__` strip (#30) and a
      **gfx942-only rocBLAS/Tensile prune** (#31) — expected to clear it. ⚠️ **ACTIONS:** (1) rebuild
      on the MI300 and confirm `scripts/smoke.sh` → `SMOKE PASSED` (strict < 10 GB + gfx942 proof);
      (2) `scripts/build_push.sh <registry>` to push (it refuses to push a ≥10 GB image); (3) make it
      **public** and **record the pull URL here** — the submission form needs it.
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
- [ ] Image is **strictly < 10 GB** (decimal, as `docker images` prints). — ⚠️ **Currently 10.28 GB**
      (the `rocm/pytorch:latest` base grew since the 9.58 GB squash). Cuts landed: `__pycache__` strip
      (#30) + **gfx942-only rocBLAS/Tensile prune** (#31, ~1–3 GB). **PENDING: rebuild on the MI300 and
      re-measure via `scripts/smoke.sh`** — the gate now enforces `< 10 GB` strictly and `build_push.sh`
      refuses to push otherwise. Update this line with the measured size once confirmed.
- [x] Process **exits 0** on success (and on partial failure). — enforced in `app/main.py`
      (T081) + unit test T075; verified in the end-to-end run.
- [x] All four styles (`formal`, `sarcastic`, `humorous_tech`, `humorous_non_tech`) produce
      distinct, on-tone captions. — verified end-to-end 2026-07-09, all four cleanly populated
      (STATUS log).
- [x] `main` is green; PRs merged; docs current. — T102 done: CI green on `main` (captioner + api
      + web lanes), release **v1.0.0** tagged 2026-07-10, planning docs reconciled (T101).

See [deployment](deployment.md) for build/push mechanics and [11-phase0-runbook](11-phase0-runbook.md)
for the local verification run.
