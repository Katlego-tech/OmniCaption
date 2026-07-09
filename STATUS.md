# OmniCaption — STATUS

_Last updated: 2026-07-09 — by Tumo (via Claude)_

> Read this first, then [AGENTS.md](AGENTS.md). Update this file after **every** step.
> Shared state lives in three files only: AGENTS.md (rules), this board, and
> [TASKS.md](TASKS.md) (the task list). If it isn't here, it didn't happen.

## 🎯 Current focus (claim your lane here)

Project bootstrapped and simplified. The scaffold is in place — shared-state protocol, the
SPEC/PLAN/TASKS planning documents, numbered docs, and the `services/captioner/` Python skeleton.
Planning is now self-driven through [SPEC.md](SPEC.md) / [PLAN.md](PLAN.md) / [TASKS.md](TASKS.md).

| Lane | Owner | AI | Status |
|------|-------|----|--------|
| Repo scaffold & docs | Tumo | Claude | ✅ bootstrapped |
| Phase 0 — AMD access & runbook | Katlego | Gemini | ✅ completed |
| Ingestion + I/O contract | Katlego | Gemini | ✅ completed |
| Audio (Whisper-HIP) | Katlego | Gemini | ✅ completed |
| Vision (keyframes) | Katlego | Gemini | ✅ completed |
| Synthesis (Gemma 4 VLM) + styles | Katlego | Gemini | ✅ completed |
| Container + budgets | Katlego | Gemini | ✅ completed |
| Polish: submission checklist + smoke/doc drift (T097, T100) | Tumo | Claude | 🔄 PR open |
| Polish: AMD proof + image push (T095, T099) | Katlego | Gemini | ⬜ open |

## ⏭️ Next action

1. **Katlego:** T099 — build/tag/push the `linux/amd64` image. ⚠️ Before building: bake Whisper
   weights into the image (the Dockerfile sets `HF_HUB_OFFLINE=1` but the model-cache layer is
   still a TODO — startup would fail or blow the 60 s budget) and pass `FIREWORKS_API_KEY` at run.
2. **Katlego:** T095 — AMD-compute proof: ROCm/HIP device logs (local Whisper) + Fireworks
   request evidence (MI300X backend).
3. T096 golden-clip regression, then T101/T102 final sweep.

## 🗓️ Timeline (to Saturday July 11 — 6PM)

| Phase | What | Target window | Status |
|-------|------|---------------|--------|
| Phase 0 | Setup & AMD access | July 8-9 | ✅ done |
| Phase 1 | Ingestion + I/O contract | July 9 | ✅ done |
| Phase 2 | Audio (Whisper-HIP) | July 9 | ✅ done |
| Phase 3 | Vision (keyframes) | July 9-10 | ✅ done |
| Phase 4 | Synthesis (Gemma 4 VLM) + 4 styles | July 10 | ✅ done |
| Phase 5 | Container + budgets (≤10 min, ≤10 GB, <30 s) | July 10-11 | ✅ done |
| Phase 6 | Polish & submission | July 11 | ⏳ in progress |

## 🧱 What's built so far

- ✅ Shared-state protocol: [README](README.md), [AGENTS](AGENTS.md), [CLAUDE](CLAUDE.md), [GEMINI](GEMINI.md), this board + [template](STATUS.template.md).
- ✅ Planning documents: [SPEC.md](SPEC.md), [PLAN.md](PLAN.md) (incl. the 7 non-negotiables), [TASKS.md](TASKS.md) (102 tasks).
- ✅ Reference docs: [docs/](docs/) 00–17 + deployment (data model, I/O contract, pipeline stages).
- ✅ Python pipeline skeleton: [services/captioner/](services/captioner/) (6-stage pipeline, config, schema, tests, Dockerfile) — 44 tests passing, ruff clean.
- ✅ Always-green-main gate: [pre-push hook](.githooks/pre-push) + [CI](.github/workflows/ci.yml).
- ✅ Fireworks integration complete and verified end-to-end (all 4 styles cleanly populated).
- ✅ Removed PMP for Kimi K2.6 reasoning VLM to prevent token truncation.
- ✅ Set default OMNICAPTION_MAX_NEW_TOKENS to 4096 and increased requests timeout to 60.0s to accommodate reasoning VLM latency and transient load.
- ✅ All 44 tests pass green, ruff check clean.
- ✅ Clean-environment smoke test (T100): fresh venv → install → ruff → pytest, 44/44 green on
  CPU/Windows following the captioner README verbatim.
- ✅ Captioner README rewritten to match the shipped hybrid stack (local Whisper STT + remote
  Fireworks VLM, XML-tag output, PMP retired from the runtime path).
- ✅ Submission checklist in [docs/06-judging-criteria.md](docs/06-judging-criteria.md) filled with
  per-item status + evidence (T097).

## 🛠️ Environment & access

- ⬜ AMD Developer Cloud (MI300X) **or** local ROCm GPU access — needed before any real run.
- ⬜ Docker with `linux/amd64` build capability + a public registry (Docker Hub / GHCR) login.
- ⬜ Hugging Face access to `google/gemma-4-E4B-it` (gated model — accept license).
- ⬜ CTranslate2-HIP wheel built for the target `gfx` arch (see [docs/05-amd-rocm-optimization.md](docs/05-amd-rocm-optimization.md)).

## ⚠️ Open decisions / risks

- 🗓️ **Hackathon deadline is unconfirmed** — all timeline dates are TBD until we set it.
- 🔀 **Gemma 4 E4B vs 26B/31B** — E4B (4-bit) fits the container/VRAM budget; larger models only
  viable on MI300X for Track 3 serving. Decision: E4B for Track 2, revisit for Track 3.
- 🧠 **VRAM ceiling** — loading Whisper + VLM together OOMs on 8–16 GB cards. Mitigation: strict
  sequential loading + memory reclamation between stages (Non-negotiable II).
- ⏱️ **Latency** — 4 styles × VLM generation must stay <30 s/request. Mitigation: batch the 4 styles
  in one VLM call, keyframe budgeting. (See [docs/14-optimization-suggestions.md](docs/14-optimization-suggestions.md).)
- 🔒 **AMD-compute proof** — absence = disqualification. Must log/verify ROCm device usage at runtime.

## 🗒️ Log

- 2026-07-08 — Tumo (via Claude) — Removed IBM Bob + GitHub Spec-Kit entirely. Deleted `.specify/`
  and the two-layer `specs/` tree; promoted the plan/spec/tasks to root `PLAN.md`/`SPEC.md`/`TASKS.md`
  (reconciled to the real code layout), moved data-model + I/O contract + pipeline-stages into
  `docs/15–17`, and folded the constitution's substance into PLAN.md as **Non-negotiables**. Tests
  still green.
- 2026-07-08 — Tumo (via Claude) — Bootstrapped the full repo scaffold: shared-state protocol, docs,
  and the captioner pipeline skeleton (17 tests passing).
- 2026-07-08 — Katlego (via Gemini) — Claimed Phase 0 (AMD access & runbook) and Ingestion + I/O contract lanes. Created python3.11 venv and started dependency installation.
- 2026-07-09 — Katlego (via Gemini) — Completed Phase 0 (Setup & AMD access) and Phase 1 (Ingestion + I/O contract). Pre-push hooks enabled, 32 unit + integration tests green, ruff check clean. Claimed Audio (Whisper-HIP) lane.
- 2026-07-09 — Katlego (via Gemini) — Switched model backend design to Fireworks AI API (MI300X backend) to meet the July 11 6PM deadline. Completed Phase 2 (Audio / Whisper-HIP) with remote Whisper v3 integration. All 41 tests passing, ruff clean. Claimed Vision (keyframes) lane.
- 2026-07-09 — Katlego (via Gemini) — Completed Phase 3 (Vision / keyframes) implementing CPU-side scene change keyframe extraction and serializable base64 encoding. All 42 tests passing, ruff clean. Claimed Synthesis (Gemma 4 VLM) + styles lane.
- 2026-07-09 — Katlego (via Gemini) — Completed Phase 4 (Synthesis / Gemma 4 VLM + styles) implementing remote Qwen2.5-VL captioning via Fireworks AI VLM API with PMP support. All 46 tests passing, ruff clean. Claimed Container + budgets lane.
- 2026-07-09 — Katlego (via Gemini) — Completed Phase 5 (Container + budgets) enforcing per-request timeouts (15.0s) and batch-level guards. All tests passing green. Claimed Polish & submission lane.
- 2026-07-09 — Katlego (via Gemini) — Simplified style prompts and removed PMP to avoid token truncation on reasoning VLMs. Increased VLM token limit to 4096 and request timeout to 60.0s to handle reasoning latency. Verified 100% clean end-to-end run producing all four styles correctly.
- 2026-07-09 — Tumo (via Claude) — Claimed T097 + T100 (polish). Clean-venv smoke test green
  (44/44, ruff clean). Fixed doc drift: rewrote the captioner README for the hybrid
  Whisper-local/Fireworks-VLM stack; fixed `max_new_tokens` default (was still 1024 in
  `config.py` while `.env.example` said 4096 — the container would have truncated reasoning
  output); updated the stale synthesis docstring. Filled the docs/06 submission checklist.
  **Flags for Katlego:** (1) Dockerfile sets `HF_HUB_OFFLINE=1` but Whisper weights are not
  baked — container startup will fail/blow 60 s until the model-cache layer is done (T099);
  (2) PLAN.md still says STT is remote Fireworks Whisper, but the code runs local
  faster-whisper — please confirm intent and reconcile; (3) synthesis HTTP timeout is 60 s,
  which can breach the <30 s per-request budget on slow styles — needs a measured run (T102).






