# OmniCaption — Tasks

**Plan:** [PLAN.md](PLAN.md) · **Spec:** [SPEC.md](SPEC.md) · **Contracts:** [docs/16-io-contract.md](docs/16-io-contract.md), [docs/17-pipeline-stages.md](docs/17-pipeline-stages.md)

> One of the three shared-state files (with [AGENTS.md](AGENTS.md) and [STATUS.md](STATUS.md)).
> **One writer per task** — claim it in STATUS.md before you start. The `services/captioner/`
> skeleton already exists; most tasks are about filling in the `# TODO(hackathon)` stubs.

## Legend

Format: `[ID] [P?] [Story] Description`

- **[ID]** — task identifier `Tnnn`.
- **[P]** — parallelizable: touches different files from its siblings and has no unmet dependency, so
  it may run concurrently with other `[P]` tasks in the same group.
- **[Story]** — the user-story label the task serves (`US1`–`US7`, `SET` setup, `FND` foundational,
  `POL` polish).
- Checkboxes are **all unchecked** `[ ]` — this project is just starting.
- Commit format: `feat(scope): Tnnn short description` (e.g. `feat(audio): T041 add HIP whisper loader`).

Each user-story phase is ordered **Tests FIRST (must FAIL) → Implementation → Checkpoint**.

---

## Phase 1 — Setup

- [x] T001 [SET] Initialize `services/captioner/` package skeleton (`app/`, `tests/`, `__init__.py` files) per [PLAN.md](PLAN.md) structure.
- [x] T002 [P] [SET] Add `pyproject.toml` with Ruff (line length 100) + pytest config (already scaffolded — verify markers `integration`, `contract`).
- [x] T003 [P] [SET] Pin runtime deps in `requirements.txt` and dev deps in `requirements-dev.txt` (pytest, ruff, jsonschema).
- [x] T004 [P] [SET] Author `Dockerfile` on a ROCm `linux/amd64` base; multi-stage to keep the image ≤10 GB; add `.dockerignore`.
- [x] T005 [SET] Add `app/core/config.py` `Settings` (pydantic-settings): input/output paths, scratch dir, model ids, keyframe cap, seeds, budgets, enforce-AMD flag.
- [x] T006 [P] [SET] Add JSON Schema files for input & output under `tests/fixtures/schemas/` mirroring [docs/16-io-contract.md](docs/16-io-contract.md).
- [x] T007 [P] [SET] Add `tests/fixtures/tasks.sample.json` (v1/v2/v3 baseline tasks) for quickstart + tests.
- [x] T008 [P] [SET] Add `.githooks/pre-push` (Ruff + fast test suite) and document `git config core.hooksPath .githooks`.
- [x] T009 [SET] Add CI workflow: lint + unit/contract/integration on CPU; GPU-gated lane for latency + AMD-compute checks.
- [x] T010 [SET] Seed `STATUS.md` and `AGENTS.md` coordination files (shared-state protocol) and link this tasks file.

**Checkpoint:** repo builds a skeleton image, lint + empty test run pass, schemas and sample input in place.

---

## Phase 2 — Foundational (blocking; no user story is complete without these)

- [x] T011 [FND] Implement `app/core/gpu.py`: detect AMD/ROCm device (torch HIP), log active device, `assert_amd()` that fails loudly in enforced mode.
- [x] T012 [P] [FND] Verify/extend `app/core/logging.py` single-line greppable stdout format (exists) and add a run-id prefix.
- [x] T013 [P] [FND] Implement `app/core/timing.py`: per-stage timer context manager writing into `CaptionState.timings`; budget-assertion helpers.
- [x] T014 [P] [FND] Implement `app/core/errors.py`: typed pipeline errors + `fallback_caption(evidence)` deterministic helper.
- [x] T015 [FND] Implement `app/pipeline/orchestrator.py` `CaptionState` dataclass exactly as in [PLAN.md](PLAN.md).
- [x] T016 [FND] Implement `app/core/schema.py` pydantic models: `Task`, `StyleCaption`, `ClipResult`, `ResultsOutput` per [docs/15-data-model.md](docs/15-data-model.md).
- [x] T017 [P] [FND] Implement `app/pipeline/audio.py`: `Word`, `Segment`, `Transcript` with validation rules.
- [x] T018 [P] [FND] Implement `app/pipeline/vision.py`: `Keyframe` (timestamp, image ref, aligned segment idx).
- [x] T019 [FND] Implement `app/core/schema.py`: parse + validate `/input/tasks.json`, skip unknown styles, fail fast on malformed top-level.
- [x] T020 [FND] Implement `app/pipeline/output.py`: schema-validate then atomically write `/output/results.json`; repair-to-valid on validation failure.
- [x] T021 [P] [FND] Implement `app/pipeline/ingestion.py`: fetch `video_url` to scratch with timeout + structured error on failure.
- [x] T022 [FND] Implement `app/pipeline/ingestion.py`: subprocess wrapper extracting mono 16 kHz WAV; raise typed error on non-zero ffmpeg exit.
- [x] T023 [FND] Implement `app/pipeline/orchestrator.py` skeleton: iterate tasks, thread `CaptionState` through stage hooks, own fallbacks + exit-0 guarantee.
- [x] T024 [FND] Implement `app/main.py` entrypoint: load config, assert device, load tasks, run orchestrator, write results, `sys.exit(0)`.
- [x] T025 [P] [FND] Add `tests/conftest.py` fixtures: mocked STT/VLM, sample `CaptionState`, temp scratch dir.

**Checkpoint:** an empty-but-valid `results.json` is produced end-to-end from `tasks.sample.json` with all stages stubbed; process exits 0; AMD device logged.

---

## Phase 3 — US1 Ingestion (P1)

### Tests FIRST (ensure they FAIL)

- [x] T026 [P] [US1] `tests/unit/test_tasks_loader.py`: valid parse, unknown style dropped, malformed top-level fails fast (AC1.1, AC1.4, AC1.5).
- [x] T027 [P] [US1] `tests/unit/test_ffmpeg.py`: WAV output is mono/16 kHz; ffmpeg failure raises typed error (AC1.2).
- [x] T028 [P] [US1] `tests/unit/test_downloader.py`: successful fetch; unreachable URL records structured error, no raise (AC1.3).
- [x] T029 [US1] `tests/integration/test_ingestion.py`: task → local video → WAV present in `CaptionState`; one bad task does not abort the batch (AC1.3).

### Implementation

- [x] T030 [US1] Implement `app/pipeline/ingestion.py`: download video (T021) + extract WAV (T022); populate `video_path`, `wav_path`.
- [x] T031 [US1] Wire S1 into orchestrator; per-task error isolation (continue on single-task failure).
- [x] T032 [P] [US1] Handle unknown/duplicate styles at ingestion; normalize requested styles list on `Task`.
- [x] T033 [US1] Make ingestion deterministic (stable scratch paths keyed by `task_id`) for reproducibility (CC5).

**Checkpoint:** every task in a batch yields a local WAV or a recorded, isolated error; unit + integration ingestion tests green.

---

## Phase 4 — US2 Audio (P1)

### Tests FIRST (ensure they FAIL)

- [ ] T034 [P] [US2] `tests/unit/test_transcript_model.py`: word/segment timestamp ordering + monotonicity validation (AC2.1).
- [ ] T035 [P] [US2] `tests/unit/test_audio_stage.py` (mocked whisper): produces word-level transcript; empty audio → empty-but-valid transcript (AC2.1, AC2.3).
- [ ] T036 [P] [US2] `tests/unit/test_reclaim.py`: reclamation calls `del` + `gc.collect()` + empty-cache; asserts STT handle released (AC2.4, AC6.6).
- [ ] T037 [US2] `tests/integration/test_audio_amd.py` (GPU-gated): transcription executes on AMD device; logs show HIP backend (AC2.2).

### Implementation

- [ ] T038 [US2] Implement faster-whisper loader in `app/pipeline/audio.py` using CTranslate2-HIP backend; device from `core/device.py`.
- [ ] T039 [US2] Transcribe WAV → `Transcript` with segment + word timestamps; capture transcript to CPU memory.
- [ ] T040 [US2] Handle no-speech clips: return empty `Transcript` (empty segments) without error.
- [ ] T041 [US2] Implement `app/pipeline/memory.py`: `del model`, `gc.collect()`, `torch.cuda.empty_cache()`; log freed VRAM.
- [ ] T042 [US2] Wire S2 → S3 in orchestrator so VRAM is reclaimed before any VLM stage loads.

**Checkpoint:** real clip yields a word-level transcript on AMD compute; empty-audio clip handled; STT VRAM demonstrably released before vision/synthesis.

---

## Phase 5 — US3 Vision (P1)

### Tests FIRST (ensure they FAIL)

- [ ] T043 [P] [US3] `tests/unit/test_keyframes.py`: scene-change selection respects max-count cap; static clip → ≥1 fallback keyframe (AC3.1, AC3.3).
- [ ] T044 [P] [US3] `tests/unit/test_alignment.py`: each keyframe aligns to nearest transcript segment/word by timestamp (AC3.2).
- [ ] T045 [US3] `tests/integration/test_vision.py`: video → bounded keyframe list with timestamps in `CaptionState` (AC3.1, AC3.4).

### Implementation

- [ ] T046 [US3] Implement pixel-variance scene-change detection in `app/pipeline/vision.py` (OpenCV, CPU-side).
- [ ] T047 [US3] Enforce configurable `max_keyframes` cap (token-budget guardrail) with even-coverage selection when over cap.
- [ ] T048 [US3] Implement static-clip fallback sampling (first/mid/last) guaranteeing ≥1 keyframe.
- [ ] T049 [US3] Align keyframes to transcript timeline; store aligned segment index on `Keyframe`.
- [ ] T050 [US3] Persist keyframes to scratch (encoded for VLM ingestion) and record refs in `CaptionState.keyframes`.
- [ ] T051 [US3] Wire S4 into orchestrator after reclamation.

**Checkpoint:** any clip (including static) yields a bounded, timestamp-aligned keyframe set with no GPU model weight added.

---

## Phase 6 — US4 Formal synthesis (P1)

### Tests FIRST (ensure they FAIL)

- [ ] T052 [P] [US4] `tests/unit/test_prompts.py`: modality order is images → transcript → style prompt for `formal` (AC4.1).
- [ ] T053 [P] [US4] `tests/unit/test_formal_grounding.py` (mocked VLM): caption contains only evidence-supported tokens; no invented entities (AC4.2).
- [ ] T054 [P] [US4] `tests/unit/test_fallback.py`: VLM failure/timeout yields deterministic fallback caption; style never missing (AC4.4).
- [ ] T055 [US4] `tests/integration/test_synthesis_amd.py` (GPU-gated): `formal` caption generated on AMD compute (AC4.3).

### Implementation

- [ ] T056 [US4] Implement Gemma 4 E4B-it 4-bit loader in `app/pipeline/synthesis.py` (HF Transformers, PyTorch ROCm); graceful degrade to bf16 if quant backend absent.
- [ ] T057 [US4] Implement `app/prompts/templates.py`: assemble prompt in locked modality order (images → transcript → style prompt).
- [ ] T058 [P] [US4] Add `formal` system prompt in `app/prompts/styles.py` (neutral, objective, grounded).
- [ ] T059 [US4] Generate `formal` `StyleCaption`; pin low/zero temperature + fixed seed for reproducibility (CC5).
- [ ] T060 [US4] Implement deterministic fallback path (transcript/keyframe summary) invoked on VLM error or per-request timeout.
- [ ] T061 [US4] Wire S5 (formal only) into orchestrator; record synthesis timing.

**Checkpoint:** `formal` caption is generated on AMD compute for baseline clips; on forced VLM failure a valid deterministic fallback is emitted instead.

---

## Phase 7 — US5 Humor/sarcasm styles + PMP (P2)

### Tests FIRST (ensure they FAIL)

- [ ] T062 [P] [US5] `tests/unit/test_pmp.py`: PMP chain runs perceive → interpret → invert → phrase for `sarcastic` (AC5.1).
- [ ] T063 [P] [US5] `tests/unit/test_style_prompts.py`: distinct system prompts for all 4 styles; humor styles stay grounded (AC5.2, AC5.3, AC5.4).
- [ ] T064 [P] [US5] `tests/unit/test_evidence_reuse.py`: multiple styles for one clip reuse one transcript + keyframe set (AC5.5).
- [ ] T065 [US5] `tests/integration/test_all_styles.py` (mocked VLM): a task requesting all 4 styles gets 4 distinct captions (US5).

### Implementation

- [ ] T066 [US5] Implement `app/prompts/pmp.py`: the PMP metacognitive chain (perceive → interpret → invert → phrase).
- [ ] T067 [P] [US5] Add `sarcastic` style using the PMP chain; simpler single-shot sarcastic prompt as documented cut-order fallback.
- [ ] T068 [P] [US5] Add `humorous_tech` system prompt (software/engineering framing, grounded).
- [ ] T069 [P] [US5] Add `humorous_non_tech` system prompt (everyday humor, grounded).
- [ ] T070 [US5] Extend S5 to iterate requested styles over the shared evidence (extract-once, style-many).
- [ ] T071 [US5] Guarantee every requested+known style produces a `StyleCaption` (fallback per style) before S6.
- [ ] T072 [P] [US5] Add per-style grounding guard: strip/regenerate captions that introduce unsupported entities (CC4).

**Checkpoint:** all four styles produce distinct, grounded captions from a single evidence extraction; sarcasm uses PMP; humor styles stay on-topic.

---

## Phase 8 — US6 Output + limits + container (P1)

### Tests FIRST (ensure they FAIL)

- [ ] T073 [P] [US6] `tests/contract/test_output_schema.py`: `results.json` validates against output schema; every requested style present (AC6.1, AC6.2).
- [ ] T074 [P] [US6] `tests/contract/test_input_schema.py`: input loader accepts valid, rejects invalid per [docs/16-io-contract.md](docs/16-io-contract.md).
- [ ] T075 [P] [US6] `tests/unit/test_exit_code.py`: pipeline exits 0 even when some tasks failed (AC6.3).
- [ ] T076 [US6] `tests/integration/test_latency.py` (GPU-gated): per-request <30 s and batch ≤10 min budgets asserted (AC6.4).
- [ ] T077 [P] [US6] `tests/integration/test_missing_style_scores_zero.py`: a dropped style is absent → documented 0-score behavior verified.

### Implementation

- [ ] T078 [US6] Implement `app/pipeline/output.py`: assemble `ClipResult`/`ResultsOutput`, schema-validate, hand to `results_writer`.
- [ ] T079 [US6] Enforce per-request timeout in orchestrator that trips the fallback path (keeps <30 s).
- [ ] T080 [US6] Add batch-level budget guard + timing summary log (≤10 min); log per-stage timings.
- [ ] T081 [US6] Verify `main.py` always `sys.exit(0)` after writing results (even on captured errors).
- [ ] T082 [US6] Optimize container startup <60 s: pre-stage/cache model weights in the image; lazy-import heavy deps.
- [ ] T083 [US6] Trim image to ≤10 GB: multi-stage build, remove build toolchain, prune caches; add image-size CI check.
- [ ] T084 [US6] Add a sequential-VRAM assertion test/log proving STT and VLM are never co-resident (AC6.6).
- [ ] T085 [US6] Full end-to-end run against `tasks.sample.json` producing a schema-valid `/output/results.json`.

**Checkpoint (MVP COMPLETE):** batch of v1/v2/v3 runs ≤10 min, each request <30 s, startup <60 s, image ≤10 GB, output schema-valid, exit 0, AMD compute logged for both model stages.

---

## Phase 9 — US7 Video-Oracle (P3, STRETCH — Track 3)

### Tests FIRST (ensure they FAIL)

- [ ] T086 [P] [US7] `tests/stretch/test_index.py`: multimodal vector index builds over frames/transcripts (AC7.1).
- [ ] T087 [P] [US7] `tests/stretch/test_search.py`: NL query returns similarity-ranked clips/moments (AC7.2).
- [ ] T088 [US7] `tests/stretch/test_rag_answer.py`: question yields grounded RAG answer citing moments (AC7.3).

### Implementation

- [ ] T089 [US7] Scaffold `services/oracle/` separate from the Track 2 image (must not regress its budgets — AC7.4).
- [ ] T090 [P] [US7] Implement CLIP/USM embedding extraction over keyframes + transcript segments.
- [ ] T091 [P] [US7] Build the multimodal vector index + persistence.
- [ ] T092 [US7] Implement semantic search (query embedding → top-k moments).
- [ ] T093 [US7] Serve Gemma 4 31B via vLLM-ROCm; implement RAG QA over retrieved moments.
- [ ] T094 [US7] Wire an Oracle CLI/entrypoint; gate behind a fully-green Track 2.

**Checkpoint:** semantic search + grounded QA work on a small corpus without touching the Track 2 image budgets.

---

## Phase 10 — Polish / submission

- [ ] T095 [P] [POL] Produce AMD-compute proof artifact (device logs + `rocm-smi` capture) for judging.
- [ ] T096 [P] [POL] Golden-clip regression tests on v1/v2/v3 to catch tone/fidelity drift.
- [ ] T097 [P] [POL] Fill `docs/06-judging-criteria` submission checklist; cross-check against [docs/06-judging-criteria.md](docs/06-judging-criteria.md).
- [ ] T098 [P] [POL] Ruff clean pass (100 col) + type/docstring sweep across `app/`.
- [ ] T099 [POL] Build, tag, and push the `linux/amd64` image; verify pulled image runs the sample batch.
- [ ] T100 [POL] Local smoke test from a clean checkout following [services/captioner/README.md](services/captioner/README.md); fix any drift.
- [ ] T101 [P] [POL] Update `STATUS.md`/`AGENTS.md`, tag a release, and note any change to the project non-negotiables in [PLAN.md](PLAN.md).
- [ ] T102 [POL] Final always-green `main` verification: CI green, image-size + latency + AMD-compute gates pass.

---

## Dependencies / Execution Order

- **Phase 1 (Setup)** → everything. **Phase 2 (Foundational)** → all user-story phases.
- **US1 → US2 → US3 → US4 → US5 → US6** is the primary chain: audio needs a WAV (US1); reclamation
  sits between audio (US2) and vision/synthesis; keyframes (US3) + transcript (US2) feed synthesis
  (US4/US5); output (US6) needs captions.
- **US4 before US5**: humor/sarcasm reuse the synthesis loader, modality templates, and fallback path
  built in US4.
- **US6** depends on US1–US5 producing captions to serialize.
- **US7 (stretch)** depends on a fully-green US1–US6 and reuses keyframes/transcripts, but ships in a
  separate image.
- **Phase 10 (Polish)** runs last, after MVP (US6) is complete.
- Within each story: **Tests FIRST** tasks precede their Implementation tasks.

## Parallel Opportunities

- Setup: T002, T003, T004, T006, T007, T008 are `[P]` (distinct files).
- Foundational: T012, T013, T014, T017, T018, T021, T025 are `[P]`.
- Every story's "Tests FIRST" block is largely `[P]` (separate test files) and can be written
  concurrently before implementation begins.
- US5 style prompts T067/T068/T069 are `[P]` (separate prompt definitions).
- Polish T095–T098 and T101 are `[P]`.
- Model stages themselves are **not** parallel at runtime — STT and VLM are strictly sequential
  (non-negotiable II / VRAM budget).

## MVP-first strategy

Ship **US1–US6** first — that is a complete, scorable Track 2 submission. Cut order under time
pressure (from [docs/00-project-plan](docs/00-project-plan.md)): drop US7 entirely first, then
demo UI, then adaptive keyframe budgeting/self-critique, then humor-style polish, then PMP
sophistication (fall back to single-shot sarcasm). **Never cut:** schema-valid `results.json`, exit 0,
demonstrable AMD compute, and the `formal` style. Always emit a fallback for every requested style —
a missing style scores 0.

## Format Validation checklist

- [ ] Every task has an `[ID]`, optional `[P]`, a `[Story]` label, and a description.
- [ ] Each user-story phase begins with "Tests FIRST (ensure they FAIL)" before implementation.
- [ ] Each user-story phase ends with a **Checkpoint** line.
- [ ] Phases are dependency-ordered (Setup → Foundational → US1…US7 → Polish).
- [ ] `[P]` tasks touch distinct files and have no unmet dependency.
- [ ] All checkboxes are unchecked `[ ]` (project just starting).
- [ ] Task IDs are contiguous `T001`–`T102`.
- [ ] MVP (US1–US6), stretch (US7), dependencies, parallelism, and cut order are documented.

**Total tasks: 102** (T001–T102). MVP scope: T001–T085. Stretch: T086–T094. Polish: T095–T102.
