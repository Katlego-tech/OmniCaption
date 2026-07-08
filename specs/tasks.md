# OmniCaption — Tasks (human seed)

> Seed for Bob's `/speckit.tasks`. This is the shared checkbox list — one of the three shared-state
> files (with [AGENTS.md](../AGENTS.md) and [STATUS.md](../STATUS.md)). The full generated task list
> lives at [specs/001-omnicaption-captioning/tasks.md](001-omnicaption-captioning/tasks.md).
>
> Format: `[ ] [ID] [P?] [Story] Description` — `[P]` = parallelizable, `[Story]` = US label.
> **One writer per task.** Claim it in STATUS.md before you start.

## Phase 0 — Setup
- [ ] T001 [Story:—] Get AMD Developer Cloud / local ROCm access; record in STATUS.md
- [ ] T002 [P] [Story:—] Enable hooks: `git config core.hooksPath .githooks`
- [ ] T003 [Story:—] Container skeleton (Dockerfile builds, prints ROCm device, exits 0)
- [ ] T004 [P] [Story:—] `core/config.py` (pydantic-settings) + `core/schema.py` (I/O models)

## Phase 1 — Ingestion + I/O contract (US1)
- [ ] T010 [Story:US1] Contract tests FIRST for tasks.json → results.json shape
- [ ] T011 [Story:US1] `ingestion.py` download video + ffmpeg → mono 16 kHz WAV
- [ ] T012 [Story:US6] `output.py` schema-validate + write results.json + exit 0 (fallback caption)

## Phase 2 — Audio (US2)
- [ ] T020 [Story:US2] Tests FIRST for transcript shape (speech vs silent)
- [ ] T021 [Story:US2] `audio.py` faster-whisper (CTranslate2-HIP) + word timestamps
- [ ] T022 [Story:US2] `memory.py` VRAM reclamation between models

## Phase 3 — Vision (US3)
- [ ] T030 [Story:US3] Tests FIRST for keyframe extraction (static vs fast-cut)
- [ ] T031 [Story:US3] `vision.py` OpenCV scene-change keyframes + transcript alignment

## Phase 4 — Synthesis + styles (US4, US5)
- [ ] T040 [Story:US4] Tests FIRST: 4 style prompts non-empty; unknown style raises
- [ ] T041 [Story:US4] `synthesis.py` Gemma 4 E4B (4-bit); images→transcript→style prompt
- [ ] T042 [Story:US4] `prompts/styles.py` formal prompt
- [ ] T043 [Story:US5] `prompts/styles.py` sarcastic + humorous_tech + humorous_non_tech
- [ ] T044 [Story:US5] `prompts/pmp.py` metacognitive chain for sarcasm
- [ ] T045 [P] [Story:US5] Batch the 4 styles in one VLM call (latency)

## Phase 5 — Container + budgets (US6)
- [ ] T050 [Story:US6] Sequential model loading verified (no co-resident VRAM)
- [ ] T051 [Story:US6] Latency-budget test (<30 s/request) + runtime (<10 min)
- [ ] T052 [Story:US6] Image ≤10 GB; startup <60 s (bake weights into image layer)
- [ ] T053 [Story:US6] AMD-compute proof logged at runtime (Principle V)

## Phase 6 — Polish & submission
- [ ] T060 [Story:—] Golden-clip validation (v1/v2/v3) end-to-end on AMD
- [ ] T061 [Story:—] Push image to public registry (linux/amd64 manifest)
- [ ] T062 [Story:—] Submission checklist (docs/06-judging-criteria.md) complete

## Phase 7 — (stretch) Track 3 Video-Oracle (US7)
- [ ] T070 [Story:US7] vLLM-ROCm serving Gemma 4 31B
- [ ] T071 [Story:US7] Multimodal vector index (CLIP/USM) + semantic retrieval
- [ ] T072 [Story:US7] Interactive multimodal RAG QA with timestamps

---

**MVP = US1–US6** (Phases 0–6). Track 3 (Phase 7) is a separated stretch and the first thing cut
under time pressure — see the [cut order](constitution.md).
