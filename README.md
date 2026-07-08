# OmniCaption

**Stylistic AI video captioning for the AMD Developer Hackathon (ACT II) — Track 2.**

OmniCaption is a Dockerized, dual-model hybrid captioning pipeline. The evaluation harness
mounts a list of video clips at `/input/tasks.json`; OmniCaption transcribes the audio, reads the
visuals, and writes four stylistic captions per clip — **formal**, **sarcastic**, **humorous_tech**,
**humorous_non_tech** — to `/output/results.json`, entirely on AMD compute.

> Primary target: **Track 2 — Stylistic Video Captioning Agent.**
> Stretch target: **Track 3 — "Video-Oracle"** multimodal semantic search + RAG QA.

---

## Who is building this

| Person | Role | AI copilots | Entry point |
|--------|------|-------------|-------------|
| **Katlego** | Team leader, repo owner | IBM Bob + Gemini | [GEMINI.md](GEMINI.md) |
| **Tumo** | Co-builder | IBM Bob + Claude | [CLAUDE.md](CLAUDE.md) |

**IBM Bob** is the system of record and drives the [Spec-Kit](docs/07-ibm-bob-spec-kit.md) lifecycle.
Claude and Gemini work in parallel as assistants. All three coordinate only through the three
shared-state files below.

## Read these first, in order

1. [STATUS.md](STATUS.md) — the live board. What's happening right now, who owns what.
2. [AGENTS.md](AGENTS.md) — the universal contract every human and AI follows.
3. [docs/10-cross-ai-protocol.md](docs/10-cross-ai-protocol.md) — how we share state without colliding.
4. [docs/00-project-plan.md](docs/00-project-plan.md) — the master plan and timeline.

## The pipeline (Track 2)

```
/input/tasks.json
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│ 1. Ingestion   download video · ffmpeg → mono 16 kHz WAV   │
├───────────────────────────────────────────────────────────┤
│ 2. Audio       faster-whisper (CTranslate2-HIP)            │
│                transcript + word-level timestamps          │
├───────────────────────────────────────────────────────────┤
│ 3. Reclaim     del Whisper · gc · torch.cuda.empty_cache() │
├───────────────────────────────────────────────────────────┤
│ 4. Vision      OpenCV scene-change keyframes               │
│                aligned to transcript timestamps            │
├───────────────────────────────────────────────────────────┤
│ 5. Synthesis   Gemma 4 E4B (4-bit) VLM                     │
│                images → transcript → style prompt          │
│                (PMP metacognitive chain for sarcasm)       │
├───────────────────────────────────────────────────────────┤
│ 6. Output      validate schema → /output/results.json → 0  │
└───────────────────────────────────────────────────────────┘
```

Sequential model loading (evict Whisper before loading the VLM) is what keeps the pipeline
inside an 8–16 GB VRAM budget. See [docs/03-captioning-pipeline.md](docs/03-captioning-pipeline.md).

## Repository layout

```
OmniCaption/
├── README.md · AGENTS.md · CLAUDE.md · GEMINI.md   shared-state entry points
├── STATUS.md · STATUS.template.md                  the live board
├── docs/                     00–14 numbered planning docs + deployment
├── specs/                    Spec-Kit: human seeds + generated feature artifacts
├── .specify/                 Spec-Kit engine (constitution + templates)
├── services/captioner/       the Python captioning pipeline + Dockerfile
└── apps/web/  (stretch)      Track 3 Video-Oracle demo
```

Full detail in [docs/12-project-structure.md](docs/12-project-structure.md).

## Quick start

```bash
git clone https://github.com/Katlego-tech/OmniCaption.git
cd OmniCaption
git config core.hooksPath .githooks          # enable the test gate

# Build & run the captioner against the sample tasks
cd services/captioner
docker build -t omnicaption:dev .
docker run --rm \
  -v "$PWD/tests/fixtures:/input" \
  -v "$PWD/out:/output" \
  omnicaption:dev
cat out/results.json
```

More in [docs/11-phase0-runbook.md](docs/11-phase0-runbook.md).

## Four golden rules

1. **`main` is always green.** Branch, PR, let the gate pass. Never push to `main`.
2. **Ground every caption.** Say only what the audio + frames support. No invented events.
3. **Respect the budgets.** ≤10 min per run, <30 s per request, ≤10 GB image, must use AMD compute.
4. **Update [STATUS.md](STATUS.md) after every step.** It is the shared brain.
