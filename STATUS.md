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
