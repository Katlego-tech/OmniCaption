# Implementation Plan: OmniCaption Stylistic Video Captioning Agent

**Feature branch:** `001-omnicaption-captioning`
**Spec:** [spec.md](spec.md)
**Input artifacts:** [research.md](research.md) · [data-model.md](data-model.md) · [contracts/io-schemas.md](contracts/io-schemas.md) · [contracts/pipeline-stages.md](contracts/pipeline-stages.md)
**Downstream:** [tasks.md](tasks.md)

---

## Summary

OmniCaption is a Dockerized (`linux/amd64`) batch job that reads `/input/tasks.json`, runs a
**6-stage dual-model hybrid pipeline** per clip, and writes `/output/results.json` with a caption for
each requested style, then exits `0`. The two heavy models — **faster-whisper** (STT, CTranslate2-HIP)
and **Gemma 4 E4B-it** (VLM, 4-bit, HF Transformers on PyTorch ROCm) — are loaded **sequentially**,
never co-resident, so the pipeline fits AMD cards as small as 8 GB. Evidence (transcript + keyframes)
is extracted once per clip and reused across all requested styles. The `sarcastic` style adds a **PMP
metacognitive chain**. Everything runs inside hard budgets: **≤10 min** batch, **<30 s** per request,
**<60 s** startup, **≤10 GB** image, and must **provably use AMD compute**.

The build is delivered in **phased, independently testable user stories** (US1–US6 MVP; US7 stretch),
test-first, on an always-green `main`.

---

## Technical Context

| Dimension | Value |
| --- | --- |
| **Language** | Python 3.11 |
| **Container** | Docker, `linux/amd64` |
| **STT** | faster-whisper on CTranslate2-HIP (ROCm) |
| **Audio extraction** | ffmpeg → mono 16 kHz WAV |
| **Keyframes** | OpenCV pixel-variance scene-change detection (CPU-side) |
| **VLM** | Gemma 4 E4B-it, 4-bit, via Hugging Face Transformers |
| **GPU runtime** | PyTorch ROCm |
| **Config** | pydantic-settings (env-driven) |
| **Dependencies** | faster-whisper, ctranslate2, torch (ROCm), transformers, accelerate, bitsandbytes, opencv-python-headless, numpy, pillow, pydantic, pydantic-settings, requests |
| **Storage** | Filesystem only — JSON in/out, temp WAV/keyframes in a scratch dir |
| **Testing** | pytest (unit + contract + integration; models mocked for cheap runs), Ruff (line length 100) |
| **Perf goals** | Batch ≤10 min · per request <30 s · startup <60 s |
| **Constraints** | Image ≤10 GB · AMD/ROCm compute mandatory · STT+VLM never co-resident in VRAM |
| **Scale** | ~12 hidden clips × up to 4 styles; baseline set of 3 clips (v1/v2/v3) |
| **Stretch (Track 3)** | vLLM-ROCm + Gemma 4 31B + CLIP/USM multimodal vector index |

Unknowns / assumptions are recorded in [research.md](research.md). No `NEEDS CLARIFICATION` items
remain open for the MVP scope.

---

## Constitution Check (pre-design gate)

The project [constitution](../../specs/constitution.md) defines seven principles. Each is evaluated
below; all must pass before design proceeds.

| # | Principle | Status | Note |
| --- | --- | --- | --- |
| I | **Faithful & Grounded Captions** | ✅ PASS | Captions are synthesized only from extracted evidence (transcript + keyframes). Style transforms tone, not facts (spec CC4, AC4.2, AC5.4). Fallback caption is derived from real evidence. |
| II | **Hard Runtime & Memory Budgets** | ✅ PASS | Budgets are first-class: ≤10 min / <30 s / <60 s / ≤10 GB, plus sequential VRAM loading with an explicit reclamation stage (spec CC1, CC2, AC6.4–AC6.6). Latency tests assert them. |
| III | **Test-First Development** | ✅ PASS | Every user-story phase in [tasks.md](tasks.md) begins with "Tests FIRST (ensure they FAIL)" before implementation. Contract tests bind the JSON I/O. |
| IV | **Phased Delivery via Independent User Stories** | ✅ PASS | Work is decomposed into US1–US7, each independently testable with its own checkpoint; MVP = US1–US6. |
| V | **AMD Compute as a Requirement** | ✅ PASS | Both model stages run on ROCm/HIP; the active device is logged and asserted. A GPU-detection foundational task fails loudly if AMD compute is absent in enforced mode (spec CC3). |
| VI | **Multi-AI Coordination via Shared State** | ✅ PASS | Coordination happens through `STATUS.md`, `AGENTS.md`, and [specs/tasks.md](tasks.md); IBM Bob is the system of record. Commit format `feat(scope): Tnnn ...` ties commits to tasks. |
| VII | **Branch-Only, Always-Green main** | ✅ PASS | Branch-only workflow with pre-push hook + CI gate; `main` is always green. No direct commits to `main`. |

**Gate result: PASS** — no violations, no complexity deviations to record.

---

## Project Structure

### Documentation (this feature)

```
specs/001-omnicaption-captioning/
├── spec.md                     # WHAT + user stories (US1–US7)
├── plan.md                     # this file — HOW
├── tasks.md                    # dependency-ordered task list
├── research.md                 # technical decisions + rationale
├── data-model.md               # entities, fields, validation, JSON shapes
├── quickstart.md               # clone → hooks → build → run → test
├── contracts/
│   ├── io-schemas.md           # /input & /output JSON contract + JSON Schema
│   └── pipeline-stages.md      # 6-stage interface + VRAM handoff + fallbacks
└── checklists/
    └── requirements.md         # requirements-quality checklist
```

### Source (implementation target)

```
services/captioner/
├── Dockerfile                  # linux/amd64 ROCm base, ≤10 GB
├── .dockerignore
├── pyproject.toml              # Ruff (100 col) + pytest config
├── requirements.txt            # runtime deps (ROCm builds via base image)
├── requirements-dev.txt        # pytest, ruff, etc.
├── app/
│   ├── __init__.py
│   ├── main.py                 # entrypoint: read /input, run batch, write /output, exit 0
│   ├── config.py               # pydantic-settings Settings (paths, budgets, model ids, seeds)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── logging.py          # single-line greppable stdout logging (exists)
│   │   ├── device.py           # AMD/ROCm detection + assertion; active-device logging
│   │   ├── errors.py           # typed pipeline errors + fallback helpers
│   │   └── timing.py           # per-stage timers, budget assertions
│   ├── io/
│   │   ├── __init__.py
│   │   ├── tasks_loader.py     # parse & validate /input/tasks.json
│   │   ├── results_writer.py   # schema-validate & write /output/results.json
│   │   └── downloader.py       # fetch video_url → local file
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── state.py            # CaptionState dataclass (below)
│   │   ├── orchestrator.py     # runs the 6 stages per task; owns fallbacks
│   │   ├── s1_ingestion.py     # download + ffmpeg WAV
│   │   ├── s2_audio.py         # faster-whisper transcript + word timestamps
│   │   ├── s3_reclaim.py       # del model, gc.collect(), empty_cache()
│   │   ├── s4_vision.py        # OpenCV keyframes + transcript alignment
│   │   ├── s5_synthesis.py     # Gemma 4 E4B 4-bit; modality order; PMP for sarcasm
│   │   └── s6_output.py        # assemble ClipResult, validate, hand to writer
│   ├── models/
│   │   ├── __init__.py
│   │   ├── task.py             # Task, StyleCaption, ClipResult, ResultsOutput (pydantic)
│   │   ├── transcript.py       # Transcript, Segment, Word
│   │   └── keyframe.py         # Keyframe
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── styles.py           # the 4 style system prompts
│   │   ├── pmp.py              # PMP metacognitive chain for sarcasm
│   │   └── templates.py        # modality-ordered prompt assembly
│   └── ffmpeg.py               # ffmpeg subprocess wrapper (mono 16 kHz WAV)
└── tests/
    ├── conftest.py             # fixtures: mocked STT/VLM, sample state
    ├── fixtures/
    │   ├── tasks.sample.json   # sample /input for quickstart + tests
    │   └── clips/              # tiny baseline clips v1/v2/v3 (or pointers)
    ├── unit/
    │   ├── test_config.py
    │   ├── test_device.py
    │   ├── test_ffmpeg.py
    │   ├── test_tasks_loader.py
    │   ├── test_keyframes.py
    │   ├── test_alignment.py
    │   ├── test_prompts.py
    │   └── test_pmp.py
    ├── contract/
    │   ├── test_input_schema.py
    │   └── test_output_schema.py
    └── integration/
        ├── test_pipeline_smoke.py   # full run, mocked models
        └── test_latency.py          # budget assertions
```

The optional Track 3 code (US7) lives under a separate `services/oracle/` tree and is **not** part of
the MVP image; it is only built when the stretch is pursued.

---

## Pipeline state object

The orchestrator threads a single mutable state object through the six stages. Each stage reads what
it needs and writes its output back. This is the concrete contract used across
[contracts/pipeline-stages.md](contracts/pipeline-stages.md) and [data-model.md](data-model.md).

```python
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.keyframe import Keyframe
from app.models.task import StyleCaption
from app.models.transcript import Transcript


@dataclass
class CaptionState:
    """Mutable state threaded through the 6 pipeline stages for a single task."""

    task_id: str                                   # from tasks.json
    video_path: str | None = None                  # local path after download (S1)
    wav_path: str | None = None                    # mono 16 kHz WAV (S1 / ffmpeg)
    transcript: Transcript | None = None           # word-level transcript (S2)
    keyframes: list[Keyframe] = field(default_factory=list)   # scene-change frames (S4)
    captions: dict[str, StyleCaption] = field(default_factory=dict)  # style_key -> caption (S5/S6)
    timings: dict[str, float] = field(default_factory=dict)   # stage name -> seconds
    errors: list[str] = field(default_factory=list)           # structured, non-fatal errors
```

Notes:
- `transcript` may be an **empty-but-valid** `Transcript` (no speech) — vision becomes the sole
  evidence source.
- `captions` always contains an entry for every **requested + known** style by the time S6 runs; a
  failed style holds a deterministic **fallback** `StyleCaption`.
- `timings` feeds the latency assertions; `errors` are surfaced in logs but never cause a non-zero
  exit.

---

## Build Phases

The build order mirrors the phases in [tasks.md](tasks.md):

1. **Setup** — repo skeleton, Dockerfile, pyproject/Ruff/pytest, config, JSON schemas.
2. **Foundational (blocking)** — GPU/AMD detection + assertion, logging, I/O contract loader/writer,
   ffmpeg wrapper, `CaptionState`. Nothing user-facing yet, but everything downstream depends on it.
3. **US1 Ingestion** — download + WAV extraction (S1).
4. **US2 Audio** — faster-whisper HIP transcription + word timestamps (S2) + memory reclamation (S3).
5. **US3 Vision** — OpenCV keyframes + transcript alignment (S4).
6. **US4 Formal synthesis** — Gemma 4 E4B 4-bit, modality ordering, `formal` caption (S5) + fallback.
7. **US5 Humor/sarcasm** — `sarcastic` (PMP), `humorous_tech`, `humorous_non_tech` (S5).
8. **US6 Output + limits + container** — schema-valid `results.json`, exit 0, budget/latency
   enforcement, ≤10 GB image, <60 s startup, sequential VRAM verified (S6).
9. **US7 Video-Oracle (stretch)** — vLLM-ROCm + Gemma 4 31B + CLIP/USM index.
10. **Polish / submission** — AMD-compute proof, docs, judging checklist, image push.

Each user-story phase is independently demoable at its checkpoint.

---

## Testing gate

- **Test-first:** every story phase writes failing tests before implementation (constitution III).
- **Unit tests** cover config, device detection, ffmpeg wrapper, tasks loader, keyframe selection,
  alignment, prompt assembly, and the PMP chain — with STT/VLM **mocked** so they run on CPU in CI.
- **Contract tests** validate `/input` and `/output` against the JSON Schemas in
  [contracts/io-schemas.md](contracts/io-schemas.md); a requested style missing from output is a
  contract failure.
- **Integration smoke test** runs the full 6-stage pipeline end-to-end with mocked models on the
  baseline fixtures.
- **Latency test** asserts the per-request (<30 s) and batch (≤10 min) budgets on representative
  inputs (real-model, gated to the GPU CI lane).
- **Gate:** pre-push hook runs Ruff + the fast unit/contract/integration suite; CI re-runs them plus
  the GPU-gated latency/AMD-compute checks. `main` stays green (constitution VII).

---

## Post-Design Constitution Re-Evaluation

After defining the module layout, `CaptionState`, and the stage/IO contracts, the seven principles
are re-checked for any drift introduced by the design:

| # | Principle | Status | Post-design note |
| --- | --- | --- | --- |
| I | Faithful & Grounded Captions | ✅ PASS | `s5_synthesis.py` consumes only `CaptionState.transcript` + `keyframes`; the prompt templates forbid unsupported content; fallback derives from transcript. No design path introduces ungrounded text. |
| II | Hard Runtime & Memory Budgets | ✅ PASS | `s3_reclaim.py` is a dedicated stage between STT and VLM; `core/timing.py` records per-stage timings into `CaptionState.timings`; latency test enforces budgets. Sequential loading is structural, not incidental. |
| III | Test-First Development | ✅ PASS | The `tests/` tree (unit/contract/integration) exists before implementation; every phase in tasks.md leads with failing tests. |
| IV | Phased Delivery via Independent User Stories | ✅ PASS | Module boundaries (`pipeline/s1..s6`, `io/`, `prompts/`) map cleanly onto the story phases; each story can ship and demo alone. |
| V | AMD Compute as a Requirement | ✅ PASS | `core/device.py` centralizes detection/assertion and is invoked at startup and before each model stage; enforced mode disqualifies a CPU-only run. |
| VI | Multi-AI Coordination via Shared State | ✅ PASS | No design element bypasses `STATUS.md` / `AGENTS.md` / tasks.md; task IDs (Tnnn) are the coordination currency. |
| VII | Branch-Only, Always-Green main | ✅ PASS | Test/lint gates are wired into the pre-push hook and CI; design keeps units cheap (mocked models) so the gate stays fast and green. |

**Re-evaluation result: PASS** — the design introduces no new constitutional violations. Proceed to
[tasks.md](tasks.md).
