# OmniCaption — Plan (human seed, the HOW)

> Seed for Bob's `/speckit.plan`. This is the master implementation plan. The generated, detailed
> version lives at [specs/001-omnicaption-captioning/plan.md](001-omnicaption-captioning/plan.md).
> Companion docs: [00-project-plan](../docs/00-project-plan.md) · [01-architecture](../docs/01-architecture.md) ·
> [03-captioning-pipeline](../docs/03-captioning-pipeline.md) · [05-amd-rocm-optimization](../docs/05-amd-rocm-optimization.md).

## Summary

Build a Dockerized (linux/amd64) **dual-model hybrid captioning pipeline**. It reads
`/input/tasks.json`, runs six sequential stages per clip, and writes four stylistic captions per
clip to `/output/results.json`. The core design constraint driving every decision is the
**VRAM budget**: Whisper and the Gemma 4 VLM are loaded one at a time, with an explicit memory
reclamation step between them, so the pipeline runs on 8–16 GB cards without OOM.

## Locked stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.11 | ecosystem for CV / ASR / VLM; matches hackathon tooling |
| Container | Docker, `linux/amd64` | harness requirement; public-registry submission |
| Audio (ASR) | faster-whisper on **CTranslate2-HIP** | GPU-accelerated Whisper on AMD via ROCm |
| Audio extract | ffmpeg → mono 16 kHz WAV | Whisper's expected input |
| Vision | OpenCV pixel-variance scene detection | cheap keyframe selection, saves visual tokens |
| Synthesis | **Gemma 4 E4B-it** (4-bit) VLM via HF Transformers | native multimodal, fits container/VRAM |
| Runtime | PyTorch (ROCm) | AMD-compute requirement |
| Config | pydantic-settings | validated env config, fails fast |
| Quality | pytest + Ruff (100-col) | test gate + lint |
| Track 3 (stretch) | vLLM-ROCm + Gemma 4 31B + CLIP/USM index | high-throughput serving + semantic search |

## Monorepo layout

```
OmniCaption/
├── docs/                     00–14 planning docs + deployment
├── specs/                    seeds + 001-omnicaption-captioning/ generated artifacts
├── .specify/                 Spec-Kit engine (constitution + templates)
├── services/captioner/       the Python pipeline (see below)
└── apps/web/  (stretch)      Track 3 Video-Oracle demo
```

## The pipeline package (`services/captioner/`)

```
app/
  main.py                 entrypoint: read /input/tasks.json → run → write /output/results.json → exit 0
  pipeline/
    orchestrator.py       runs the 6 stages per task, sequential model loading, timing guard
    ingestion.py          download video · ffmpeg → WAV
    audio.py              faster-whisper transcription (load/transcribe/unload)
    memory.py             reclaim_vram(): gc + empty_cache
    vision.py             OpenCV keyframe extraction + transcript alignment
    synthesis.py          Gemma 4 VLM: images → transcript → style prompt; batch styles
    output.py             schema-validate + write results.json
  prompts/                styles.py (4 style system prompts) · pmp.py (sarcasm chain)
  core/                   config.py · schema.py · gpu.py · logging.py
  models/                 loader.py (Whisper + Gemma load, quantization)
tests/                    unit · integration · contract · fixtures
Dockerfile · pyproject.toml · requirements*.txt · README.md · .env.example
```

## The pipeline state object

The orchestrator threads a single dataclass through the stages (see
[001-*/plan.md](001-omnicaption-captioning/plan.md) and [data-model](001-omnicaption-captioning/data-model.md)):

```python
@dataclass
class CaptionState:
    task_id: str
    styles: list[str]
    video_path: Path | None = None
    wav_path: Path | None = None
    transcript: Transcript | None = None
    keyframes: list[Keyframe] = field(default_factory=list)
    captions: dict[str, str] = field(default_factory=dict)   # style -> caption
    timings: dict[str, float] = field(default_factory=dict)  # stage -> seconds
    errors: list[str] = field(default_factory=list)
```

## Build phases (MVP-first)

| Phase | Delivers | Story |
|-------|----------|-------|
| 0 | AMD access, hooks, container skeleton, config + schema | — |
| 1 | Ingestion + strict I/O contract (tasks.json → results.json) | US1, US6 shell |
| 2 | Audio stage (Whisper-HIP) + word timestamps | US2 |
| 3 | Vision stage (keyframes) + transcript alignment | US3 |
| 4 | Synthesis: formal caption, then the 3 humor/sarcasm styles + PMP | US4, US5 |
| 5 | Container hardening: budgets, sequential VRAM, AMD-compute proof | US6 |
| 6 | Polish, golden-clip validation, submission | — |
| 7 (stretch) | Track 3 Video-Oracle serving + index + RAG QA | US7 |

## Testing gate

- Unit tests **mock** Whisper + VLM (no GPU/downloads needed) — run in the pre-push hook and CI.
- Contract tests assert `results.json` matches the schema and includes every requested style.
- Golden-clip tests run the real pipeline against v1/v2/v3 before any submission.
- Latency-budget tests assert per-request timing stays under 30 s.
- See [docs/04-testing-strategy.md](../docs/04-testing-strategy.md).

## Constitution check

This plan satisfies all seven principles — grounding (I) via evidence-only prompts; budgets (II) via
sequential VRAM loading; test-first (III) via the phase structure; phased delivery (IV) via the table
above; AMD compute (V) via ROCm runtimes + `gpu.py`; shared state (VI) via AGENTS/STATUS/tasks;
branch-only (VII) via the hooks + CI. Detailed gate in
[001-*/plan.md](001-omnicaption-captioning/plan.md).
