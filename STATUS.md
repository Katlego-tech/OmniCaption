# OmniCaption — STATUS

_Last updated: 2026-07-10 — by Tumo (via Claude)_

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
| Polish: submission checklist + smoke/doc drift (T097, T100) | Tumo | Claude | ✅ merged (via #7/#8) |
| Polish: golden-clip regression tests (T096) | Tumo | Claude | ✅ merged (via #7/#8) |
| Polish: planning-doc reconciliation (T101 part 1) | Tumo | Claude | ✅ merged (via #7/#8) |
| Polish: AMD proof + image push (T095, T099) | Katlego | Gemini | ✅ completed |
| Web frontend architecture (Track 3 stretch) | Katlego | Claude | ✅ plan merged (PR #9) |
| Web frontend backend API (`services/api/`) | Tumo | Claude | ✅ merged (PR #9) |
| Release sweep (T101, T102) | Tumo | Claude | ✅ completed |
| Web frontend pages (`apps/web/`) | Tumo | Claude | ✅ merged (PR #11) |
| Track 3 Video-Oracle (T086–T094) | Tumo | Claude | ✅ merged (PR #13) |
| Run diagnostics (stdout/stderr + env forwarding) | Katlego → Tumo | Gemini/Claude | 🔄 PR open |
| Honest run reporting (empty-caption run ≠ green success) | Tumo | Claude | 🔄 PR open |

## ⏭️ Next action

1. **Katlego:** Record the **public registry URL** for the captioner image in
   docs/06-judging-criteria.md — the only unevidenced submission item.
2. **Both:** Submission form for Saturday 6PM — Track 2 is code-complete, tagged v1.0.0, released.
3. **Optional (post-submission):** CLIP visual embeddings for the oracle; persist transcript
   sidecars from the pipeline to enrich the index.

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

- 2026-07-11 — Tumo (via Claude) — **Image size: gfx942-only rocBLAS prune + container smoke test**
  (⚠️ **merged UNVALIDATED** per Tumo's call — MI300 smoke deferred). Added a Dockerfile prune that keeps only MI300 (`gfx942`)
  rocBLAS/Tensile kernels (`find … -path '*/rocblas/library/*' -name '*gfx*' ! -name '*gfx942*'
  -delete`), the big lever (~1–3 GB) toward the ≤10 GB gate — makes the image **MI300-specific by
  design**. Added `services/captioner/scripts/smoke.sh`: builds the image, runs one clip, and hard-
  checks (1) exit 0 + schema-valid results.json, (2) **AMD-compute proof** (ROCm gfx942 device
  active), (3) image ≤10 GB, (4) captions non-empty (when a key is set). **Critical:** the gfx942
  prune can only be validated on real gfx942 — on CPU/other GPUs rocBLAS never loads the kept
  kernels, so the script reports GPU proof INCONCLUSIVE (exit 2) off-MI300. Verified here: Dockerfile
  lints clean, `bash -n` clean, both results.json assertions catch the right failures. **⚠️ OPEN RISK:
  merged without GPU validation (Tumo chose to merge now, validate later). Before the submission run,
  someone MUST rebuild on the MI300 and get `smoke.sh` → SMOKE PASSED; if the gfx942 prune cut a
  kernel gfx942 needs, the container will fail on the MI300 (fix forward by narrowing the prune).**
- 2026-07-11 — Tumo (via Claude) — **Image size: strip `__pycache__`** (toward the ≤10 GB gate; the
  ROCm image had crept to 10.28 GB on a moving `rocm/pytorch:latest` base). Added a
  `find / -type d -name __pycache__ -prune -exec rm -rf {} +` to the Dockerfile prune layer — safe,
  since Python regenerates bytecode on import. Validated the command on the CPU dev image: removed
  313 dirs / 47 MB, app still imports (the ROCm image carries more via torch/ctranslate2). More
  aggressive size levers (gfx942-only rocBLAS Tensile kernels, dropping rccl/rocsparse/rocsolver/
  rocrand, optionally MIOpen) are documented as the next step if this alone doesn't clear 10 GB —
  those need a rebuild + MI300 GPU smoke to validate.
- 2026-07-11 — Tumo (via Claude) — **Dockerfile: drop hardcoded `--platform` from FROM.** The ROCm
  `services/captioner/Dockerfile` used `FROM --platform=linux/amd64 rocm/pytorch:latest`, which trips
  BuildKit's `FromPlatformFlagConstDisallowed` check. Removed the constant flag; the platform is now
  set at build time (`docker build --platform linux/amd64 …`), which the canonical build already does
  (Dockerfile comment, docs/deployment.md, captioner README). Added the flag to the two convenience
  builds that lacked it (`package.json` `captioner:build`, root README quickstart) so the amd64
  guarantee is preserved. `docker build --check` now reports **no warnings** (was 1); build steps
  unchanged, so the produced image is identical on an amd64 host. (Full ROCm build not re-run here —
  tens of GB / long; verified via the linter and that the base reference still resolves.)
- 2026-07-11 — Tumo (via Claude) — **Oracle QA reasoning-leak fix** (tests-first). Built the Track 3
  index from the live run (`<DATA_DIR>/oracle/index.json`, 6 moments) and lit up `/api/search` +
  `/api/qa`. Search worked well, but **Ask** returned the Kimi-K2P6 reasoning model's raw
  chain-of-thought as the answer (truncated mid-thought) — the same leak class as the captioner, in
  `oracle/qa.py` which returned `chat.complete(...)` verbatim, with `FireworksChat` capped at
  `max_tokens=1024`. Fix: the QA system prompt now asks the model to wrap only its final answer in
  `<answer>...</answer>`; `qa.answer` extracts that span (falls back to whole content if untagged);
  `FireworksChat` default `max_tokens` 1024 → 4096 for reasoning headroom. Oracle suite 14 → **18**
  green, ruff clean. Live-verified: Ask now returns a clean, grounded answer with `[task_id @ t]`
  citations and no leaked reasoning. Index needs no rebuild (answer-formatting path only).
- 2026-07-10 — Tumo (via Claude) — **Live end-to-end UI testing + synthesis robustness fix.** Brought
  up the full stack locally (web + API) and ran real pipeline jobs to test the Captioner Hub. Built a
  **CPU dev image** (`services/captioner/Dockerfile.dev`: `python:3.11-slim` + ffmpeg + faster-whisper
  int8 + opencv, no ROCm/torch/source-compile, ~1.9 GB) so the pipeline runs on non-AMD dev machines
  — the ROCm `Dockerfile` stays the submission artifact. Real runs against live Fireworks Kimi-K2P6
  produced grounded captions across styles, and **transcript grounding is verified** (a clip with
  dialogue → Whisper transcript → captions weave the spoken line with the visual). Two real content
  bugs surfaced and are now fixed (tests-first, verified inside the image, 13 synthesis tests green,
  ruff clean): (1) the reasoning VLM occasionally emits a degenerate `<captionStyle>...</captionStyle>`
  (bare ellipsis) — seen once as a literal `"..."` caption; (2) worse, when it is truncated
  (`finish_reason="length"`) before closing the tag, the old parse path dumped the **entire raw
  chain-of-thought** as the caption. Fix has two layers: (i) `synthesis` rejects punctuation-only/empty
  captions and untagged truncated/long reasoning leaks; (ii) because the failures are **intermittent**,
  `generate_caption` now **retries with escalation** (config `OMNICAPTION_SYNTHESIS_MAX_ATTEMPTS`,
  default 3) — each retry doubles `max_tokens` (recovers truncation/leaks) and adds a little
  temperature (breaks a repeated degenerate answer) — falling back to the grounded deterministic
  caption only if all attempts fail. Verified live: a re-run of the same clip that had shown BOTH
  `"..."` (sarcastic) and an 18,897-char reasoning leak (humorous) recovered **four real captions** —
  sarcastic on attempt 3, humorous on attempt 2 (logs show the reject → recover). Also confirmed the
  honest-reporting fix live: an
  ingestion 403 (bad clip URL) → empty captions → UI shows "completed with errors" with the log, not a
  false green. **Ops note (dev only):** a fresh web build on a non-3000 port needs that origin in the
  API's `CORS_ORIGINS`.
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
- 2026-07-09 — Tumo (via Claude) — T096 golden-clip regression tests (tests-first: failed, then
  green). Pins the tone-bearing surfaces byte-for-byte against golden fixtures over frozen
  v1/v2/v3 evidence: the four style system prompts + tag rules, prompt-assembly shape
  (images → transcript), and the deterministic fallback text. Deliberate tone changes must
  regenerate goldens via `tests/regression/regen_goldens.py` in the same PR. Added an opt-in
  live Fireworks structural test (gated on `FIREWORKS_API_KEY` + `OMNICAPTION_LIVE_TESTS=1`,
  never runs in CI). Suite now 49 green + 1 gated skip, ruff clean.
- 2026-07-09 — Tumo (via Claude) — T101 part 1: reconciled the planning docs with the shipped
  hybrid stack (PROPOSAL — Katlego please confirm the STT decision). PLAN.md summary/tech-table/
  non-negotiable V now say: local faster-whisper STT (HIP in container) + remote Fireworks
  Kimi-K2P6 VLM; SPEC.md AC2.2/AC2.4/AC6.6/CC2/CC3 updated to the hybrid AMD-proof story;
  AC5.1 updated to single-shot sarcasm (PMP retired — the documented cut-order fallback);
  CLAUDE.md/GEMINI.md "locked stack" + stage list updated with a pointer to this plan change.
  Release tagging (T101 part 2) waits for T095/T099/T102.
- 2026-07-09 — Tumo (via Claude) — CI: removed the `branches: [main]` filter on `pull_request`
  so stacked PRs (feature → feature) run the gate before merge. Verified locally that the full
  CI recipe passes on the stack, including `ruff format --check` (46 files clean).
- 2026-07-09 — Katlego (via Gemini) — T095, T099: Removed stock ctranslate2 from requirements.txt to avoid conflict; updated Dockerfile to compile CTranslate2-HIP from source with native compilation flags. Created draft docs/submission-amd-proof.md for judging. Committed and pushed to feat/polish-amd-container-v2.
- 2026-07-09 — Tumo (via Claude) — T099-prep (Dockerfile only; build/push stays with Katlego):
  bake Whisper weights (`Systran/faster-whisper-large-v3` → `HF_HOME`) **before** flipping
  `HF_HUB_OFFLINE=1` — previously startup would fail offline with no cached weights. Pruned the
  dead local-VLM path (legacy `load_gemma_vlm`, `transformers`/`accelerate`/`bitsandbytes`/
  `pillow` deps, `gemma_model_id`/`load_in_4bit` settings) to shrink the image toward the
  ≤10 GB gate. Fixed root `.env.example` (wrong `*_PATH` var names Settings never read) and
  documented the Whisper knobs. Also fixed a Windows timer-resolution bug in
  `core/timing.py` (monotonic → perf_counter; sub-16 ms stages recorded 0.0). 49 tests green.
  ⚠️ Open risk for T099: `rocm/pytorch:latest` base may alone exceed 10 GB — needs a measured
  build and possibly a slimmer ROCm base image.
- 2026-07-10 — Katlego (via Gemini) — T099: Fixed container build (specified ROCm clang/clang++ compilers, installed libomp-dev, dynamically symlinked libomp.so to /usr/local/lib, and resolved build OOM by swapping to memory-efficient snapshot_download for model caching). Successfully built omnicaption-captioner:latest (13.5 GB) and verified CTranslate2 loads correctly on GPU inside the container. Committed and pushed to feat/polish-amd-container-v2.
- 2026-07-10 — Katlego (via Gemini) — T095, T099: Successfully merged Tumo's latest PR branch containing Whisper cache prep, environment config fixes, and timing improvements. Resolved conflicts in STATUS.md, Dockerfile, requirements.txt, and loader.py. Discovered and fixed a CPU fallback issue in load_whisper where MKL-less compilation lacked an x86 int8 SGEMM backend (implemented dynamic compute fallback using ctranslate2.get_supported_compute_types). Confirmed container local CPU smoke test runs successfully and writes schema-valid output on partial fallback. Marked T095/T099 complete.
- 2026-07-10 — Katlego (via Claude) — T096 image gate: Squashed Docker image with ROCm pruning (static archives, LLVM, hipblaslt, rocfft, migraphx, librocalution_hip, librpp). Final size 9.58 GB (under 10 GB gate). Verified all core imports pass (torch, ctranslate2, faster_whisper, cv2). Pushed to feat/polish-amd-container-v2.
- 2026-07-10 — Katlego (via Claude) — Web frontend architecture: Designed full frontend plan using Next.js 15, shadcn/ui + VengeanceUI animated components, Tailwind CSS. 7 pages (Landing, Dashboard, Captioner Hub, Search, Oracle Chat, Accounts/API Keys, Docs). Decoupled deployment: static Next.js export + standalone FastAPI backend. API key management via localStorage. Plan committed to `docs/18-frontend-architecture.md` on `feat/web-frontend` branch. Handover to Tumo for backend API scaffolding.
- 2026-07-10 — Tumo (via Claude) — Synced with main after the #7/#8 merges; PRs #3–#6 are now
  empty vs main and should be closed (flagged for Katlego — branch cleanup too). Accepted the
  web-frontend handover: scaffolded `services/api/` per docs/18 §4 (tests FIRST: 27-test contract
  suite red on missing package, then green). FastAPI + CORS, endpoints: tasks CRUD over the
  captioner `tasks.json` contract (unknown styles dropped, same-id replace, atomic writes),
  single-slot pipeline runner (`POST /api/tasks/run` → 202/409 + status polling), results
  read-through (`/api/results[/{task_id}]`), traversal-safe `/api/media/{file}`, Fireworks key
  validation (`/api/keys/validate` → upstream probe, 502 on unreachable), and 501-pinned Track 3
  stubs for `/api/search` + `/api/qa`. Standalone deploy: no captioner import, slim Dockerfile,
  env contract per docs/18 §6 (`CORS_ORIGINS`/`DATA_DIR`/`CAPTIONER_IMAGE`/`CAPTIONER_CMD`).
  Extended CI + pre-push gates with an `api` lane. Verified with the gate's own interpreter:
  api 27/27 green, captioner 49 green + 1 gated skip, ruff check + format clean on both.
- 2026-07-10 — Tumo (via Claude) — Merged PR #9 (backend API + Katlego's docs/18 plan) with both
  CI lanes green; post-merge CI on main green. Housekeeping: closed stale PRs #3/#5 (#4/#6 were
  already closed) and deleted the merged branches (Tumo-approved). T101/T102 release sweep:
  AGENTS.md repo map now includes `services/api/`; the 2026-07-09 hybrid-stack plan change was
  already recorded in PLAN.md by T101 pt.1. Gate evidence for T102: CI green on main (both
  lanes), image gate 9.58 GB ≤ 10 GB (measured by Katlego, T096/T099), AMD-compute proof drafted
  in docs/submission-amd-proof.md (T095), latency guards enforced in code with a verified clean
  end-to-end run (2026-07-09 log). Tagging release v1.0.0 on this merge. Remaining before
  submission: Katlego's frontend page generation (Track 3 stretch — does not gate Track 2).
- 2026-07-10 — Tumo (via Claude) — **Lane takeover (Tumo's call):** claiming the frontend-pages
  lane so it lands before Saturday; Katlego, shout if you'd rather run your Ollama flow — nothing
  here blocks regenerating pages later. Building `apps/web/` per docs/18: Next.js 15 App Router,
  TypeScript, Tailwind, `output: 'export'` static build, dark-first AMD-red theme.
  **One deliberate deviation from docs/18 for reliability:** the VengeanceUI-style animated
  components (aurora hero, flip-text, bento grid, animated counters, glow cards) are implemented
  in-repo with Tailwind/CSS instead of pulling from the third-party vengenceui.com registry —
  no external registry dependency in the build; swapping in real VengeanceUI components via the
  shadcn CLI later remains possible. Dashboard stats are computed from live API data (no
  invented numbers); Search/Oracle pages handle the 501 Track 3 stubs with honest
  "not built yet" states.
- 2026-07-10 — Tumo (via Claude) — Frontend pages shipped: all 7 routes (Landing, Dashboard,
  Captioner Hub, Search, Oracle Chat, Accounts, Docs) build and export statically (11 static
  routes, ~106 kB first-load JS). Typed API client over the full services/api contract with a
  run-status poller; Accounts stores the backend URL + Fireworks key in localStorage only
  (docs/18 option (a)). ESLint clean, `next build` green. CI gains a `web` lane
  (npm ci → lint → static-export build).
- 2026-07-10 — Tumo (via Claude) — Submission packaging + release: docs/06 checklist refreshed
  with landed evidence (PR #12) — **one open item: Katlego to record the public registry URL**;
  README drift fixed (hybrid stack diagram, layout, web quickstart); GitHub Release **v1.0.0**
  published. Track 3 Video-Oracle shipped as a **text-modality MVP** (Tumo-approved scope):
  `services/oracle/` (T089) with Fireworks embeddings index + persistence (T090 text-modality /
  T091), cosine top-k search (T092), grounded RAG QA with [task_id @ t] citations on Kimi-K2P6
  (T093 per the Fireworks plan change), CLI (T094), tests-first T086–T088 (9 tests, Fireworks
  mocked, red→green). `/api/search` + `/api/qa` now serve the index when present at
  `<DATA_DIR>/oracle/index.json` (Fireworks key via `X-Fireworks-Key` header or env) and keep
  the honest 501 otherwise; web Search/Oracle pages render ranked hits and cited answers. CI
  gains an `oracle` lane (4 lanes total). Suites: oracle 9/9 (3 seeds), api 30/30, captioner
  49+1 skip, web lint+build green. **Honest scope note:** CLIP visual keyframe embeddings are
  NOT implemented — the index is text-only (captions + optional transcript sidecars).
- 2026-07-10 — Tumo (via Claude) — Follow-up leftovers closed (tests-first throughout): (1)
  captioner now emits **sidecars** for the oracle — `/output/transcripts.json` (timed segments,
  default on, `OMNICAPTION_EMIT_TRANSCRIPTS=0` to disable) and keyframe JPEGs under
  `/output/keyframes/` (opt-in via `OMNICAPTION_EMIT_KEYFRAMES=1`); best-effort writers that can
  never break the results.json contract. (2) Oracle gains the **CLIP visual space**: keyframe
  moments (`space="clip"`) embedded via optional open_clip ViT-B-32 (`oracle/clip_embed.py`),
  cross-modal search merges text + clip hits, clip moments skip gracefully when open_clip is
  absent; CLI grows `--keyframes`; API bridge passes a CLIP encoder when available. Old
  text-only index files still load (covered by test). (3) CI actions bumped
  (checkout@v5, setup-python@v6) to clear the Node 20 deprecation warnings. Suites: captioner
  53/53 (+4), oracle 14/14 (+5), api 30/30, ruff clean. Cross-space score merge is uncalibrated
  (MVP) — noted in the search docstring.
- 2026-07-10 — Tumo (via Claude) — Branch hygiene (Tumo-approved): verified Katlego's three
  remaining branches (`feat/fireworks-integration`, `feat/polish-amd-container-v2`,
  `feat/web-frontend`) were each **0 commits ahead of main** (fully landed via PRs #1, #7/#8,
  and #9) and deleted them — no work lost, merge history preserved on main. The remote now has
  a single branch: `main`, green on all four CI lanes, tagged v1.0.0. Remaining before
  submission (non-code): Katlego records the image's public registry URL in docs/06; team
  submits by Saturday 6PM.
- 2026-07-10 — Tumo (via Claude) — **Team decision (Tumo): all web icons come from Icons8**
  (https://icons8.com/icons, free tier). Added `components/icon.tsx` (ios-glyphs style via the
  img.icons8.com CDN), swapped the sidebar emoji + run-button glyph for Icons8 icons, removed
  the unused create-next-app scaffold SVGs, and added the license-required "Icons by Icons8"
  attribution links (landing footer + sidebar). Verified live on the dev stack: all 7 icon URLs
  200, active/muted tints render, lint + static-export build green. Also live-validated
  Katlego's Fireworks key via `/api/keys/validate` (valid=true; key kept in process env only,
  never committed).
- 2026-07-10 — Tumo (via Claude) — **Completed Katlego's `fix/synthesis-diagnostics` branch** (he
  pushed the fix; I added the missing test coverage and landed it, per the "complete his branches"
  ask). His change: the runner now captures pipeline stdout/stderr (tail 4 KB, thread-safe) and
  surfaces them on terminal states; `run_command()` forwards `FIREWORKS_API_KEY` + `OMNICAPTION_*`
  + `HF_*` into the docker container; the Captioner UI shows a diagnostic log on failure and marks
  empty captions clearly. My additions: `test_config.py` (env forwarding + default docker command)
  and 3 runner tests (idle omits output, success captures stdout, failure surfaces stderr) — api
  now 36 green. ruff + format clean, web lint + build green.
- 2026-07-10 — Katlego (via Gemini) — Authored `docs/19-notebook-environment.md`: a ROCm 7.2 +
  vLLM 0.16.0 + PyTorch 2.9 notebook run-plan for the organizer hardware (diagnostics, deps,
  inline pipeline run, optional local vLLM serving). Verified against local Ollama (qwen3:14b).
  Indexed docs 18 + 19 in `docs/README.md`.
- 2026-07-10 — Tumo (via Claude) — Reviewed + landed the notebook doc: fixed two broken code
  references in its inline-run cell against the real API (`log_amd_device` → `assert_amd`,
  `write_results` → `validate_and_write`) so the cell actually imports and runs. All four CI
  lanes green.
- 2026-07-10 — Tumo (via Claude) — **Auth (login/signup) + delete endpoints** (user-requested;
  tests-first). Backend: `AuthService` (stdlib only — SQLite user store at `<DATA_DIR>/auth.db`,
  PBKDF2-hashed passwords, HMAC-signed expiring bearer tokens) with `POST /api/auth/signup`,
  `/login`, `GET /api/auth/me`; plus `DELETE /api/tasks[/{id}]` and `DELETE /api/results[/{id}]`
  (delete-one + clear-all, 204/404). Frontend: `/login` + `/signup` pages, localStorage session,
  client-side dashboard `AuthGuard` + user chip/logout, Bearer header on every call, and trash
  (Icons8) delete buttons on queued tasks and generated captions. **New env: `AUTH_SECRET`** —
  default is a dev placeholder, must be overridden in prod. api suite 36 → 54, ruff clean; web
  lint + 13-route static build green. **Live-smoked the whole flow** on the running stack:
  signup → duplicate-409 → login → wrong-pw-401 → `/me` with/without/tampered token → task &
  result delete (one/all/404) all behaved correctly. Note: existing task/result/run endpoints
  stay unauthenticated (parity with prior behavior); gating mutations behind the token is a
  possible follow-up.
- 2026-07-10 — Tumo (via Claude) — **Security hardening** (self red-team of the auth work, then
  fixed the High+ findings; tests-first). (1) **No more known-default signing key** — an unset
  `AUTH_SECRET` now auto-generates a random 256-bit secret persisted at
  `<DATA_DIR>/auth_secret.key` (gitignored) instead of the old public `dev-insecure-change-me`;
  a token forged with that old default is rejected. (2) **Mutations now require a token** —
  `require_user` gates `POST /api/tasks`, `DELETE /api/tasks[/{id}]`, `POST /api/tasks/run`, and
  `DELETE /api/results[/{id}]` (reads stay open); moved the dependency into `core/deps.py`.
  (3) **SSRF guard** — `video_url` must be http(s) to a non-internal host (blocks
  169.254.169.254, loopback/private/link-local/reserved IPs, `localhost`/metadata hostnames);
  `task_id` restricted to `[A-Za-z0-9_-]{1,64}` (it becomes a downstream path). Plus PBKDF2
  120k → **600k** (OWASP floor) and a constant-time dummy-hash for unknown-user login (kills the
  enumeration timing side-channel). api suite 54 → **77** (venv) / 74 + skip (CI interpreter),
  ruff clean. **Live-smoked**: unauth mutations → 401, SSRF/bad-URL + bad task_id → 422, forged
  old-default token → 401, valid authed submit → 201. **Residual (documented, not fixed):** no
  rate limiting, signup 409 still enumerates emails, token in localStorage (XSS), no server-side
  token revocation, no email verification, DNS-rebinding bypass of the URL check.
- 2026-07-10 — Tumo (via Claude) — **Closed the residual security items** (tests-first).
  (1) **Rate limiting**: in-memory per-IP sliding window on signup/login/verify → 429 (config
  `RATE_LIMIT_MAX`/`_WINDOW_S`). (2) **Token revocation**: tokens carry a `tv` (token-version)
  claim checked against the DB; `POST /api/auth/logout` bumps it (logout-everywhere) and clears
  the cookie. (3) **Email verification** (config `REQUIRE_VERIFICATION`, default off to keep the
  demo frictionless): `verified` column + token, dev mailer writes the link to
  `<DATA_DIR>/outbox/`, `POST /api/auth/verify` activates + logs in; login blocks unverified with
  a 403 that only surfaces after the password matches (not an oracle). (4) **Signup
  anti-enumeration**: in verification mode signup returns an identical generic 202 whether or not
  the email exists (no 409 oracle); the login timing channel was already closed. (5) **httpOnly
  cookie auth**: login/signup/verify set an httpOnly `session` cookie; `require_user` accepts
  cookie OR Bearer header (frontend sends `credentials:include`) — XSS-safe path for
  same-site/HTTPS deploys, header remains the cross-origin dev fallback. (6) **DNS-rebinding**:
  `submit_tasks` resolves the `video_url` host and rejects internal IPs (config
  `SSRF_RESOLVE_DNS`, off in tests); TOCTOU residual documented — egress filtering is the
  backstop. New `/verify` web page + logout wired to server-side revocation; 429/403/202 handled
  in the auth form. api suite 77 → **87** (venv) / 84 + skip (CI), ruff clean; web lint +
  14-route build green. Live-smoked: revocation 200→logout→401, httpOnly `Set-Cookie`, rate-limit
  429 at the cap.
- 2026-07-10 — Tumo (via Claude) — **Auth DB in-place migration** (tests-first). Signup 500'd
  (`sqlite3.OperationalError: table users has no column named verified`) against an `auth.db`
  created by a pre-verification build: `AuthService._init_db` used `CREATE TABLE IF NOT EXISTS`
  with the full schema, which never adds columns to an already-existing table — so any in-place
  upgrade broke signup, not just a stale dev DB. Fix: a `_COLUMN_MIGRATIONS` pass after table
  creation that `ALTER TABLE ADD COLUMN`s any missing `verified`/`verification_token`/
  `token_version` (defaults keep legacy accounts usable — verified, token-version 0). New
  `tests/test_auth_migration.py` (3 tests: columns added, legacy rows default verified, signup
  succeeds against a migrated legacy DB) — red→green. Full auth/hardening/verification/revocation
  suites 39 green, ruff clean. Live-smoked on the running stack: DB upgraded on restart, signup
  POST → 201. (Surfaced while bringing up the dev stack for UI testing; also hit a dev-only CORS
  gap — a fresh web build on a non-3000 port isn't in the API's default allowlist.)
- 2026-07-10 — Tumo (via Claude) — **Honest run reporting** (Captioner Hub). A run that exits 0 but
  produces empty captions was rendering as a green "last run succeeded" with the diagnostic log
  hidden (the log only showed on non-zero exit). Because `main.run()` always returns 0 (harness
  scores on output presence) and a stage failing *before* synthesis backfills empty caption strings
  in `build_result`, this violated "report failures honestly" at the UI layer. Fix (web-only,
  frontend gate = lint + static-export build, matching the established web lane — no unit runner in
  `apps/web`): new pure `apps/web/src/lib/run-status.ts` (`describeRun`/`countEmptyCaptions`) folds
  the exit-code state together with the actual captions; a succeeded-but-empty run now shows a
  **warn "completed with errors"** badge, an honest note ("exited cleanly but produced N empty
  captions — a stage failed before synthesis"), and the captured stderr/stdout **Diagnostic Log**
  (previously shown only on `failed`). Lint clean, 14-route build green. **Diagnosis note:** empty
  strings (not `[Fallback] …` text) prove synthesis never ran — the underlying failure is a
  pre-synthesis stage (ingestion/audio/vision), most likely the 4K clip's download hitting the 60 s
  `download_timeout_s` or keyframe extraction on 4K frames. The real stderr is now visible in the UI
  on the next run.
- 2026-07-10 — Tumo (via Claude) — **Multi-instance rate limiting** (last residual; tests-first).
  Refactored `ratelimit.py` into a `RateLimiter` protocol + `InMemoryRateLimiter` (default,
  per-process sliding window) + `RedisRateLimiter` (shared fixed-window via atomic INCR/EXPIRE)
  behind a `build_rate_limiter(settings)` factory. `REDIS_URL` (new, optional) selects the shared
  backend; `redis` is an optional lazily-imported dep (not in requirements) so the base image
  stays lean and CI needs no Redis — if the URL is unset or unreachable it degrades to in-memory
  with a warning, and the Redis backend fails **open** on outage (availability over strictness).
  api 87 → **91** (venv) / 88 + skip (CI): new tests cover backend selection, the unavailable-Redis
  fallback, the shared cap (fake client), and fail-open. ruff clean. Documented tradeoffs:
  fixed-window (vs sliding) can briefly allow up to 2× at a window boundary; fail-open means a
  Redis outage disables limiting rather than locking users out.
