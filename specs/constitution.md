# OmniCaption — Constitution (human seed)

> Seed for Bob's `/speckit.constitution`. The ratified version lives at
> [.specify/memory/constitution.md](../.specify/memory/constitution.md) — edit that after ratification.

## Mission

Win **Track 2** of the AMD Developer Hackathon (ACT II): produce the most visually-faithful,
tonally-accurate stylistic captions per video clip, on AMD compute, inside the harness's hard
budgets. Set up **Track 3 "Video-Oracle"** (semantic search + RAG QA) as a clean stretch.

## Seven non-negotiable principles

1. **Faithful & Grounded Captions** — caption only what audio + frames support; no fabricated facts.
2. **Hard Runtime & Memory Budgets** — ≤10 min, <30 s/req, ≤10 GB, <60 s start; Whisper and VLM
   never co-resident in VRAM.
3. **Test-First Development** — tests (especially the JSON contract) written first, must fail first.
4. **Phased Delivery via Independent User Stories** — MVP = US1–US6; Track 3 is separated.
5. **AMD Compute as a Requirement** — provably use ROCm/HIP; absence = disqualification.
6. **Multi-AI Coordination via Shared State** — Bob (record) + Claude + Gemini share only
   AGENTS.md / STATUS.md / specs/tasks.md; one writer per task.
7. **Branch-Only, Always-Green main** — no direct pushes; PRs with a green gate only.

## Architecture commitments

- Dual-model hybrid pipeline; sequential model loading with VRAM reclamation between stages.
- Locked stack: Python 3.11 · faster-whisper (CTranslate2-HIP) · OpenCV keyframes · Gemma 4 E4B
  (4-bit) VLM · ffmpeg · pydantic-settings · pytest + Ruff.
- Strict JSON I/O contract: `/input/tasks.json` → `/output/results.json`, exit 0, missing style = 0.

## Out of scope (and cut order under time pressure)

Cut in this order if the deadline squeezes: **(1)** Track 3 Video-Oracle → **(2)** advanced
keyframe/audio-event refinements → **(3)** per-style few-shot exemplars → **(4)** the humor styles'
polish (keep them functional). **Never cut:** a schema-valid `results.json`, AMD-compute usage, or
grounding.
