# 00 — Project Plan

## Mission

Build **OmniCaption**: a Dockerized, dual-model hybrid pipeline that watches a video clip and writes
a styled caption for each requested style. It must run on AMD compute (ROCm/HIP), stay inside a tight
runtime and image-size budget, and produce schema-valid output that the hackathon harness can score.

The container reads `/input/tasks.json` (a list of `{task_id, video_url, styles[]}`) and writes
`/output/results.json` with a caption for every requested style per clip, then exits with code 0.
Four target styles: `formal`, `sarcastic`, `humorous_tech`, `humorous_non_tech`.

## Tracks we target

- **Track 2 — Stylistic Video Captioning Agent (PRIMARY).** This is the whole batteries-included
  submission. Everything in [01-architecture](01-architecture.md) and
  [03-captioning-pipeline](03-captioning-pipeline.md) serves Track 2.
- **Track 3 — "Video-Oracle" (STRETCH).** vLLM-ROCm serving Gemma 4 31B plus a multimodal vector
  index (CLIP/USM embeddings) for semantic video search + RAG QA. Only pursued if Track 2 is fully
  green and time remains. See [05-amd-rocm-optimization](05-amd-rocm-optimization.md) and
  [14-optimization-suggestions](14-optimization-suggestions.md).

## Phased timeline

Concrete dates are **TBD — confirm hackathon deadline**.

| Phase | Goal | Exit criteria |
| --- | --- | --- |
| Phase 0 — Setup | ROCm/AMD access, repo clone, hooks, baseline build | Container builds; 3 baseline clips run end-to-end. See [11-phase0-runbook](11-phase0-runbook.md) |
| Phase 1 — Ingestion + Audio | tasks.json parsing, ffmpeg WAV, faster-whisper HIP | Word-level transcript for a real clip |
| Phase 2 — Vision | OpenCV scene-change keyframes, timestamp alignment | Keyframes selected and aligned to transcript |
| Phase 3 — Synthesis | Gemma 4 E4B 4-bit, modality ordering, one style end-to-end | `formal` caption generated on GPU |
| Phase 4 — All styles + PMP | sarcastic (PMP), humorous_tech, humorous_non_tech | All 4 styles produce distinct captions |
| Phase 5 — Hardening | schema validation, memory reclamation, latency/OOM fallback | Full run under 10 min, schema-valid, no OOM |
| Phase 6 — Submission/polish | image push, AMD compute proof, docs, judging checklist | Public image + passing [06-judging-criteria](06-judging-criteria.md) checklist |

## Scope

**In scope:** the 6-stage Track 2 pipeline, the four styles, AMD/ROCm execution, sequential model
loading, schema-valid output, reproducible Docker build.

**Out of scope (unless stretch time):** Track 3 Video-Oracle, a web UI, fine-tuning any model,
support for GPUs outside the listed AMD targets.

## Cut order (what gets dropped first under time pressure)

Drop from the top down when the clock runs out:

1. Track 3 Video-Oracle entirely.
2. `apps/web` demo UI.
3. Adaptive keyframe budgeting and any self-critique/LLM-judge loop (ship fixed heuristics instead).
4. `humorous_tech` and `humorous_non_tech` refinement (keep them functional, stop polishing tone).
5. PMP sophistication for `sarcastic` (fall back to a simpler single-shot sarcastic prompt).

Never cut: schema-valid `/output/results.json`, exit 0, demonstrable AMD compute usage, and the
`formal` style. A missing style scores 0, so always emit *something* valid for every requested style
even if it is the deterministic fallback caption.
