# OmniCaption — STATUS

_Last updated: 2026-07-08 — by Tumo (via Claude)_

> Read this first, then [AGENTS.md](AGENTS.md). Update this file after **every** step.
> Shared state lives in three files only: AGENTS.md (rules), this board, and
> [TASKS.md](TASKS.md) (the task list). If it isn't here, it didn't happen.

## 🎯 Current focus (claim your lane here)

Project bootstrapped and simplified. The scaffold is in place — shared-state protocol, the
SPEC/PLAN/TASKS planning documents, numbered docs, and the `services/captioner/` Python skeleton.
**IBM Bob and GitHub Spec-Kit have been removed**; planning is now self-driven through
[SPEC.md](SPEC.md) / [PLAN.md](PLAN.md) / [TASKS.md](TASKS.md). **Nothing is implemented yet**; the
next move is Phase 0 setup and claiming the first lanes.

| Lane | Owner | AI | Status |
|------|-------|----|--------|
| Repo scaffold & docs | Tumo | Claude | ✅ bootstrapped |
| Phase 0 — AMD access & runbook | _unclaimed_ | | ⬜ |
| Ingestion + I/O contract | _unclaimed_ | | ⬜ |
| Audio (Whisper-HIP) | _unclaimed_ | | ⬜ |
| Vision (keyframes) | _unclaimed_ | | ⬜ |
| Synthesis (Gemma 4 VLM) + styles | _unclaimed_ | | ⬜ |
| Container + budgets | _unclaimed_ | | ⬜ |

## ⏭️ Next action

1. **Confirm the hackathon deadline** and fill the timeline dates (currently TBD). — _open decision_
2. Work [docs/11-phase0-runbook.md](docs/11-phase0-runbook.md): get AMD Developer Cloud / local ROCm
   access, enable hooks (`git config core.hooksPath .githooks`), build the container skeleton.
3. Claim the **Ingestion + I/O contract** lane and start T-tasks in Phase 1 of [TASKS.md](TASKS.md).

## 🗓️ Timeline (to <hackathon deadline — TBD>)

| Phase | What | Target window | Status |
|-------|------|---------------|--------|
| Phase 0 | Setup & AMD access | TBD | ⬜ |
| Phase 1 | Ingestion + I/O contract | TBD | ⬜ |
| Phase 2 | Audio (Whisper-HIP) | TBD | ⬜ |
| Phase 3 | Vision (keyframes) | TBD | ⬜ |
| Phase 4 | Synthesis (Gemma 4 VLM) + 4 styles | TBD | ⬜ |
| Phase 5 | Container + budgets (≤10 min, ≤10 GB, <30 s) | TBD | ⬜ |
| Phase 6 | Polish & submission | TBD | ⬜ |

## 🧱 What's built so far

- ✅ Shared-state protocol: [README](README.md), [AGENTS](AGENTS.md), [CLAUDE](CLAUDE.md), [GEMINI](GEMINI.md), this board + [template](STATUS.template.md).
- ✅ Planning documents: [SPEC.md](SPEC.md), [PLAN.md](PLAN.md) (incl. the 7 non-negotiables), [TASKS.md](TASKS.md) (102 tasks).
- ✅ Reference docs: [docs/](docs/) 00–17 + deployment (data model, I/O contract, pipeline stages).
- ✅ Python pipeline skeleton: [services/captioner/](services/captioner/) (6-stage pipeline, config, schema, tests, Dockerfile) — 17 tests passing, ruff clean.
- ✅ Always-green-main gate: [pre-push hook](.githooks/pre-push) + [CI](.github/workflows/ci.yml).
- ✅ IBM Bob + GitHub Spec-Kit removed; planning flattened to SPEC/PLAN/TASKS/STATUS.
- ⬜ No models wired, no real inference, no container build validated yet.

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
