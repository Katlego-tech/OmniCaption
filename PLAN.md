# OmniCaption — Implementation Plan (the HOW)

**Track:** AMD Developer Hackathon (ACT II) — Track 2 (primary), Track 3 "Video-Oracle" (stretch).
**Companions:** [SPEC.md](SPEC.md) (the WHAT) · [TASKS.md](TASKS.md) (the task list) ·
[docs/15-data-model.md](docs/15-data-model.md) · [docs/16-io-contract.md](docs/16-io-contract.md) ·
[docs/17-pipeline-stages.md](docs/17-pipeline-stages.md) · [docs/09-research-summary.md](docs/09-research-summary.md).

---

## Summary

OmniCaption is a Dockerized (`linux/amd64`) batch job that reads `/input/tasks.json`, runs a
**6-stage dual-model hybrid pipeline** per clip, and writes `/output/results.json` with a caption for
each requested style, then exits `0`. The model split is **hybrid**: speech-to-text runs **locally**
with faster-whisper (CTranslate2 — HIP in the container, int8 CPU fallback for dev), and
vision-language synthesis runs **remotely** on the **Fireworks AI API** (Kimi-K2P6, served on
Fireworks' AMD MI300X platform). Local VRAM therefore still matters for the STT stage: Whisper is
unloaded and VRAM reclaimed before synthesis. Evidence (transcript + keyframes) is extracted once
per clip and reused across every requested style. All styles are single-shot persona prompts; the
model's reasoning is kept outside `<captionStyle>` tags and only the tagged caption is extracted
(the PMP chain was retired from the runtime path to avoid token truncation on reasoning VLMs).
Everything runs inside hard budgets: **≤10 min** batch, **<30 s** per request, **<60 s** startup,
**≤10 GB** image, and must **provably use AMD compute** (local ROCm/HIP for STT + Fireworks'
AMD-powered backend for the VLM).

The build is delivered in **phased, independently testable user stories** (US1–US6 MVP; US7 stretch),
test-first, on an always-green `main`.

---

## Non-negotiables (project principles)

These are the values every change is held to. They replace what used to be a formal "constitution" —
same substance, no ceremony.

1. **Faithful & grounded captions.** Say only what the transcript + keyframes support. Style changes
   tone, never facts. (Scored as Accuracy.)
2. **Hard runtime & memory budgets.** ≤10 min batch, <30 s/request, <60 s startup, ≤10 GB image.
3. **Test-first.** Each user story writes failing tests before implementation; the JSON I/O contract
   is bound by contract tests.
4. **Phased delivery.** Independent user stories, MVP = US1–US6, each phase ends demoable.
5. **AMD compute is mandatory.** STT runs on local ROCm/HIP inside the container (device logged at
   runtime); VLM synthesis runs on Fireworks AI's AMD-powered compute platform (MI300X GPUs), with
   requests and model ids logged. Local dev/fallback paths (CPU whisper) are flagged in logs.
6. **Coordinate through shared state.** [STATUS.md](STATUS.md), [AGENTS.md](AGENTS.md), and
   [TASKS.md](TASKS.md) are the only coordination surfaces; one writer per task.
7. **Branch-only, always-green `main`.** No direct pushes; every change lands via PR with a green gate.

---

## Technical Context

| Dimension | Value |
| --- | --- |
| **Language** | Python 3.11 |
| **Container** | Docker, `linux/amd64` |
| **STT** | faster-whisper `large-v3` (CTranslate2 — HIP in container, int8 CPU for dev), local |
| **Audio extraction** | ffmpeg → mono 16 kHz WAV |
| **Keyframes** | OpenCV pixel-variance scene-change detection (CPU-side), ≤1024 px per frame |
| **VLM** | Kimi-K2P6 via Fireworks AI API (`OMNICAPTION_FIREWORKS_VLM_MODEL`) |
| **API Backend** | Fireworks AI AMD-powered compute platform (MI300X) for the VLM stage |
| **Config** | pydantic-settings (env-driven, `OMNICAPTION_*` / `FIREWORKS_API_KEY`) |
| **Storage** | Filesystem only — JSON in/out, temp WAV/keyframes in a scratch dir |
| **Testing** | pytest (unit + contract + integration; API calls mocked), Ruff (line length 100) |
| **Perf goals** | Batch ≤10 min · per request <30 s · startup <60 s |
| **Constraints** | Image ≤10 GB · AMD/ROCm backend platform compute |
| **Scale** | ~12 hidden clips × up to 4 styles; baseline set of 3 clips (v1/v2/v3) |
| **Stretch (Track 3)** | Fireworks AI models + CLIP/USM multimodal vector index |

---

## Project Structure (as scaffolded)

The pipeline package already exists under `services/captioner/`. This is the **actual** layout the
tasks build against — the six stages live in `app/pipeline/` as one module each, pydantic I/O models
in `app/core/schema.py`, and AMD detection in `app/core/gpu.py`.

```
services/captioner/
├── Dockerfile                  # linux/amd64 ROCm base, ≤10 GB, bakes model weights for <60 s start
├── .dockerignore
├── pyproject.toml              # Ruff (100 col) + pytest config
├── requirements.txt            # runtime deps (ROCm builds via base image)
├── requirements-dev.txt        # pytest, ruff, jsonschema, etc.
├── app/
│   ├── main.py                 # entrypoint: read /input, run batch, write /output, sys.exit(0)
│   ├── core/
│   │   ├── config.py           # pydantic-settings Settings (paths, budgets, model ids, thresholds)
│   │   ├── schema.py           # pydantic I/O models: Task, StyleCaption, ClipResult, ResultsOutput
│   │   ├── gpu.py              # AMD/ROCm detection, gfx-arch map, HSA overrides, device logging
│   │   └── logging.py          # single-line greppable stdout logging
│   ├── pipeline/
│   │   ├── orchestrator.py     # CaptionPipeline: threads CaptionState through the 6 stages; fallbacks
│   │   ├── ingestion.py        # S1: download video + ffmpeg → mono 16 kHz WAV
│   │   ├── audio.py            # S2: faster-whisper (HIP) transcript + word timestamps (+ Transcript types)
│   │   ├── memory.py           # S3: reclaim_vram() — del model, gc.collect(), empty_cache()
│   │   ├── vision.py           # S4: OpenCV keyframes + transcript alignment (+ Keyframe type)
│   │   ├── synthesis.py        # S5: Fireworks VLM API; system=persona+tag rules, user=images→transcript
│   │   └── output.py           # S6: assemble ClipResult, schema-validate, atomic write
│   ├── prompts/
│   │   ├── styles.py           # the 4 style system prompts
│   │   └── pmp.py              # PMP chain (retired from runtime; kept as documented fallback)
│   └── models/
│       └── loader.py           # load_whisper (CT2 device placement) + legacy local-VLM loader
└── tests/
    ├── unit/                   # test_schema, test_vision, test_styles (models mocked)
    ├── integration/            # test_pipeline_smoke (full run, mocked models)
    ├── contract/               # test_output_contract (results.json schema)
    └── fixtures/               # tasks.sample.json, results.sample.json (v1/v2/v3)
```

**Stage ↔ module map** (used throughout [TASKS.md](TASKS.md)):
S1 Ingestion → `ingestion.py` · S2 Audio → `audio.py` · S3 Reclaim → `memory.py` ·
S4 Vision → `vision.py` · S5 Synthesis → `synthesis.py` · S6 Output → `output.py`.

The optional Track 3 code (US7) lives under a separate `services/oracle/` tree and is **not** part of
the MVP image; it is only built when the stretch is pursued.

---

## Pipeline state object

The orchestrator threads a single mutable state object through the six stages. Each stage reads what
it needs and writes its output back. See [docs/17-pipeline-stages.md](docs/17-pipeline-stages.md) and
[docs/15-data-model.md](docs/15-data-model.md).

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class CaptionState:
    """Mutable state threaded through the 6 pipeline stages for a single task."""
    task_id: str
    styles: list[str]
    video_path: Path | None = None                 # local path after download (S1)
    wav_path: Path | None = None                    # mono 16 kHz WAV (S1 / ffmpeg)
    transcript: "Transcript | None" = None          # word-level transcript (S2)
    keyframes: list["Keyframe"] = field(default_factory=list)   # scene-change frames (S4)
    captions: dict[str, str] = field(default_factory=dict)      # style_key -> caption (S5/S6)
    timings: dict[str, float] = field(default_factory=dict)     # stage name -> seconds
    errors: list[str] = field(default_factory=list)             # structured, non-fatal errors
```

Notes:
- `transcript` may be an **empty-but-valid** `Transcript` (no speech) — vision becomes the sole
  evidence source.
- `captions` always contains an entry for every **requested + known** style by the time S6 runs; a
  failed style holds a deterministic **fallback** caption.
- `timings` feeds the latency assertions; `errors` are surfaced in logs but never cause a non-zero exit.

---

## Build phases (MVP-first)

Mirrors [TASKS.md](TASKS.md):

1. **Setup** — repo skeleton, Dockerfile, pyproject/Ruff/pytest, config, JSON schemas.
2. **Foundational (blocking)** — AMD detection + assertion (`core/gpu.py`), logging, I/O contract
   (`core/schema.py`, `pipeline/output.py`), ffmpeg wrapper (`pipeline/ingestion.py`), `CaptionState`.
3. **US1 Ingestion** — download + WAV extraction (S1).
4. **US2 Audio** — faster-whisper HIP transcription + word timestamps (S2) + memory reclamation (S3).
5. **US3 Vision** — OpenCV keyframes + transcript alignment (S4).
6. **US4 Formal synthesis** — Fireworks VLM, modality ordering, `formal` caption (S5) + fallback.
7. **US5 Humor/sarcasm** — `sarcastic`, `humorous_tech`, `humorous_non_tech` (S5; single-shot
   persona prompts — PMP retired to avoid reasoning-VLM token truncation).
8. **US6 Output + limits + container** — schema-valid `results.json`, exit 0, budget/latency
   enforcement, ≤10 GB image, <60 s startup, sequential VRAM verified (S6).
9. **US7 Video-Oracle (stretch)** — vLLM-ROCm + Gemma 4 31B + CLIP/USM index.
10. **Polish / submission** — AMD-compute proof, docs, judging checklist, image push.

Each user-story phase is independently demoable at its checkpoint.

---

## Testing gate

- **Test-first:** every story phase writes failing tests before implementation.
- **Unit tests** cover config, device detection, keyframe selection, alignment, prompt assembly, and
  the PMP chain — with STT/VLM **mocked** so they run on CPU in CI.
- **Contract tests** validate `/input` and `/output` against the schemas in
  [docs/16-io-contract.md](docs/16-io-contract.md); a requested style missing from output is a
  contract failure.
- **Integration smoke test** runs the full 6-stage pipeline end-to-end with mocked models.
- **Latency test** asserts the per-request (<30 s) and batch (≤10 min) budgets (real-model, GPU lane).
- **Gate:** the [pre-push hook](.githooks/pre-push) runs Ruff + the fast suite; [CI](.github/workflows/ci.yml)
  re-runs them plus the GPU-gated latency/AMD-compute checks. `main` stays green.

See [docs/04-testing-strategy.md](docs/04-testing-strategy.md).
