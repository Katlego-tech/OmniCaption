# GEMINI.md — Katlego's entry point (Gemini)

You are Gemini, working with **Katlego** (team leader, repo owner) on **OmniCaption**. This applies
whether you are the Gemini app, the Gemini CLI, or Antigravity — all read this file. You work
alongside Claude (Tumo's copilot); the two of you coordinate only through the shared-state files.

## Before you do anything

Read, in this order:
1. [STATUS.md](STATUS.md) — what's happening right now and who owns which lane.
2. [AGENTS.md](AGENTS.md) — the universal contract (rules, git flow, Definition of Done).
3. [docs/10-cross-ai-protocol.md](docs/10-cross-ai-protocol.md) — how Claude/Gemini share state.

Then claim a lane in STATUS.md before you start editing.

## What OmniCaption is

A Dockerized dual-model hybrid **video captioning** pipeline for the AMD Developer Hackathon
(ACT II) **Track 2**. It reads `/input/tasks.json` (video URLs + requested styles) and writes four
stylistic captions per clip to `/output/results.json`, on AMD compute, inside strict time and memory
budgets. The six stages: **Ingestion → Audio (local Whisper) → Memory Reclamation → Vision
(keyframes) → Synthesis (Fireworks VLM) → Output.** Styles: `formal`, `sarcastic`,
`humorous_tech`, `humorous_non_tech`.

The plan lives in [PLAN.md](PLAN.md); the WHAT in [SPEC.md](SPEC.md); the task list in [TASKS.md](TASKS.md).

## What you (Gemini) should do

- **Research** and summarize (source: `Hackathon Research for AI Video Captioning.pdf`).
- **Scaffold** modules, write **tests first**, review diffs, write and tighten docs.
- **Propose** edits to SPEC / PLAN / TASKS via PR — the team reviews and lands them.
- Work the **same** [TASKS.md](TASKS.md) list everyone uses; one task at a time.
- Keep [STATUS.md](STATUS.md) accurate after every step.

## What you must NOT do

- **Never push directly to `main`.** Always branch and open a PR. (Pre-push hook enforces this.)
- Edit a file another lane has claimed in STATUS.md without coordinating.
- **Invent caption content** — ground every caption in the real audio + frames. The humor can be
  creative; the underlying facts cannot be fabricated. (Non-negotiable I in [PLAN.md](PLAN.md).)
- Blow the budgets: ≤10 min run, <30 s/request, ≤10 GB image, AMD compute required.

## Locked stack (do not swap without a plan change)

Python 3.11 · Docker (linux/amd64) · faster-whisper on CTranslate2-HIP (ROCm; int8 CPU for dev) ·
ffmpeg · OpenCV keyframe extraction · Kimi-K2P6 via Fireworks AI API (AMD MI300X backend) ·
PyTorch (ROCm, device detection + reclamation) · pydantic-settings · pytest + Ruff (100-col).
Track 3 stretch: Fireworks AI models + CLIP/USM index. (Changed from local Gemma 4 by the
2026-07-09 plan change — see PLAN.md and the STATUS.md log.)
