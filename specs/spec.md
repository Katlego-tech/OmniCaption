# OmniCaption — Specification (human seed, the WHAT)

> Seed for Bob's `/speckit.specify`. Implementation-agnostic. The generated, detailed version lives
> at [specs/001-omnicaption-captioning/spec.md](001-omnicaption-captioning/spec.md).

## Overview

OmniCaption is a stylistic video-captioning agent for the AMD Developer Hackathon (ACT II) Track 2.
Given a list of video clips and a set of requested styles, it emits, for each clip, one caption per
style that is both **visually accurate** and **tonally on-style**, produced entirely on AMD compute
inside strict time and memory budgets.

## Actors

- **Primary — the evaluation harness** (automated): mounts `/input/tasks.json`, runs the container,
  reads `/output/results.json`, scores it, and enforces the runtime limits.
- **Secondary — the dev team** (Katlego, Tumo + Bob/Claude/Gemini): build, test, and submit.
- **Secondary — Track 3 end users** (stretch): people searching a video corpus in natural language.

## User stories

- **US1 — Ingest tasks & video.** As the harness, I provide `[{task_id, video_url, styles[]}]`; the
  agent downloads each video and extracts a mono 16 kHz WAV. *Accept:* every task's media is fetched
  or the failure is recorded and does not crash the run.
- **US2 — Transcribe audio.** The agent transcribes speech with word-level timestamps. *Accept:* a
  clip with speech yields a non-empty transcript; a silent clip yields an empty transcript, not an error.
- **US3 — Extract keyframes.** The agent selects representative keyframes via scene-change detection
  and aligns them to transcript timestamps. *Accept:* a static clip yields few keyframes; a
  fast-cutting clip yields more; the token/frame budget is respected.
- **US4 — Generate the formal caption.** The agent produces an objective, factual, third-person
  caption. *Accept:* no subjective adjectives or invented facts; describes the primary event first.
- **US5 — Generate the humor/sarcasm styles.** The agent produces `sarcastic`, `humorous_tech`, and
  `humorous_non_tech` captions, each authentically on-style. *Accept:* sarcastic is dry/biting (no
  cheesy puns); humorous_tech uses dev metaphors; humorous_non_tech avoids jargon.
- **US6 — Produce schema-valid results within limits.** The agent writes `/output/results.json` with
  every requested style for every clip, and exits 0, inside the budgets. *Accept:* output validates
  against the contract; no missing styles; runtime and image size within limits.
- **US7 — (stretch) Video-Oracle.** As an end user, I search a video corpus in natural language and
  get a context-aware, timestamped answer via multimodal RAG. *Accept:* a query returns the relevant
  segment + a grounded answer.

## Cross-cutting requirements

- **Runtime & memory:** ≤10 min per run, <30 s per request, ≤10 GB image, <60 s cold start.
- **AMD compute:** the pipeline provably uses ROCm/HIP; usage is logged.
- **Determinism of shape:** output is always schema-valid JSON, even on partial failure (fallback
  caption), exit code 0.
- **Grounding:** captions describe only observed content.

## Demo acceptance criteria

Against the three baseline clips (v1 urban autumn boulevard, v2 orange kitten in a garden, v3 office
worker typing), OmniCaption produces four schema-valid, grounded, on-style captions per clip, within
the runtime budget, on AMD hardware.
