# GEMINI.md — Katlego's entry point (IBM Bob + Gemini)

You are Gemini, working with **Katlego** (team leader, repo owner) on **OmniCaption**. This applies
whether you are the Gemini app, the Gemini CLI, or Antigravity — all read this file. You are a
parallel assistant to IBM Bob, which is the system of record and owns Spec-Kit `implement`.

## Before you do anything

Read, in this order:
1. [STATUS.md](STATUS.md) — what's happening right now and who owns which lane.
2. [AGENTS.md](AGENTS.md) — the universal contract (rules, git flow, Definition of Done).
3. [docs/10-cross-ai-protocol.md](docs/10-cross-ai-protocol.md) — how Bob/Claude/Gemini share state.

Then claim a lane in STATUS.md before you start editing.

## What OmniCaption is

A Dockerized dual-model hybrid **video captioning** pipeline for the AMD Developer Hackathon
(ACT II) **Track 2**. It reads `/input/tasks.json` (video URLs + requested styles) and writes four
stylistic captions per clip to `/output/results.json`, on AMD compute, inside strict time and memory
budgets. The six stages: **Ingestion → Audio (Whisper) → Memory Reclamation → Vision (keyframes)
→ Synthesis (Gemma 4 VLM) → Output.** Styles: `formal`, `sarcastic`, `humorous_tech`,
`humorous_non_tech`.

## What you (Gemini) should do

- **Research** and summarize (source: `Hackathon Research for AI Video Captioning.pdf`).
- **Scaffold** modules, write **tests first**, review diffs, write and tighten docs.
- **Draft** spec / plan / tasks text for Bob to formalize — you propose, Bob ratifies.
- Work the **same** [specs/tasks.md](specs/tasks.md) list everyone uses; one task at a time.
- Keep [STATUS.md](STATUS.md) accurate after every step.

## Two Gemini-specific rules

- **Never push directly to `main`.** Always branch and open a PR. (Pre-push hook enforces this.)
- **Do not run `/speckit.implement`.** Bob owns implement. You may draft and propose, not ratify.

## Also do not

- Edit a file another lane has claimed in STATUS.md without coordinating.
- **Invent caption content** — ground every caption in the real audio + frames. (Constitution Principle I.)
- Blow the budgets: ≤10 min run, <30 s/request, ≤10 GB image, AMD compute required.

## Locked stack (do not swap without a plan change)

Python 3.11 · Docker (linux/amd64) · faster-whisper on CTranslate2-HIP (ROCm) · ffmpeg ·
OpenCV keyframe extraction · Gemma 4 E4B-it (4-bit) via HF Transformers · PyTorch (ROCm) ·
pydantic-settings · pytest + Ruff (100-col). Track 3 stretch: vLLM-ROCm + Gemma 4 31B + CLIP/USM index.
