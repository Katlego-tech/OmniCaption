# CLAUDE.md — Tumo's entry point (IBM Bob + Claude)

You are Claude, working with **Tumo** on **OmniCaption**. You are a parallel assistant to IBM Bob,
not a replacement for it. Bob owns the Spec-Kit `implement` step and is the system of record.

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

## What you (Claude) should do

- **Research** and summarize (the source is `Hackathon Research for AI Video Captioning.pdf`).
- **Scaffold** modules, write **tests first**, review diffs, write and tighten docs.
- **Draft** spec / plan / tasks text for Bob to formalize — you propose, Bob ratifies.
- Work the **same** [specs/tasks.md](specs/tasks.md) list everyone uses; one task at a time.
- Keep [STATUS.md](STATUS.md) accurate after every step.

## What you must NOT do

- **Never push to `main`.** Branch, PR, let the gate pass. (Pre-push hook enforces this.)
- **Don't run `/speckit.implement`** — that is Bob's job.
- Don't edit a file another lane has claimed in STATUS.md without coordinating.
- **Don't invent caption content.** Ground every caption in the actual audio + frames. The humor
  can be creative; the underlying facts cannot be fabricated. (Constitution Principle I.)
- Don't blow the budgets: ≤10 min run, <30 s/request, ≤10 GB image, AMD compute required.

## Locked stack (do not swap without a plan change)

Python 3.11 · Docker (linux/amd64) · faster-whisper on CTranslate2-HIP (ROCm) · ffmpeg ·
OpenCV keyframe extraction · Gemma 4 E4B-it (4-bit) via HF Transformers · PyTorch (ROCm) ·
pydantic-settings · pytest + Ruff (100-col). Track 3 stretch: vLLM-ROCm + Gemma 4 31B + CLIP/USM index.
