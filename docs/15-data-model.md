# Data Model: OmniCaption

**Plan:** [../PLAN.md](../PLAN.md) · **Contracts:** [16-io-contract.md](16-io-contract.md), [17-pipeline-stages.md](17-pipeline-stages.md)

This document defines every data entity in OmniCaption — its fields, types, and validation rules —
plus the exact input and output JSON shapes. Entities are implemented as pydantic models
(`app/core/schema.py`) except `CaptionState`, which is a runtime dataclass (`app/pipeline/orchestrator.py`). The
four known style keys are the closed set `{formal, sarcastic, humorous_tech, humorous_non_tech}`.

---

## Entity overview

| Entity | Kind | Module | Role |
| --- | --- | --- | --- |
| `Task` | input | `app/core/schema.py` | One clip + its requested styles (from `/input`). |
| `StyleCaption` | output leaf | `app/core/schema.py` | One caption for one style. |
| `ClipResult` | output | `app/core/schema.py` | All styled captions for one task. |
| `ResultsOutput` | output root | `app/core/schema.py` | The whole `/output/results.json` document. |
| `Word` | evidence | `app/pipeline/audio.py` | One transcribed word + timing. |
| `Segment` | evidence | `app/pipeline/audio.py` | A contiguous run of words. |
| `Transcript` | evidence | `app/pipeline/audio.py` | The full transcript for a clip. |
| `Keyframe` | evidence | `app/pipeline/vision.py` | One sampled frame + timing/alignment. |
| `CaptionState` | runtime | `app/pipeline/orchestrator.py` | Mutable per-task state threaded through stages. |

---

## Task

One entry of `/input/tasks.json`.

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `task_id` | `str` | yes | Non-empty; unique within the batch; used as the scratch/result key. |
| `video_url` | `str` | yes | Non-empty; URL or resolvable path the downloader can fetch. |
| `styles` | `list[str]` | yes | Non-empty list; each item **should** be one of the 4 known styles. Unknown styles are dropped at load with a warning; duplicates de-duplicated preserving order. |

Rules:
- If `styles` becomes empty after dropping unknowns, the task is recorded as an error and produces an
  empty `ClipResult` (still schema-valid).
- Load fails fast (whole batch) only if the top-level document is not a list or a task is missing
  `task_id`/`video_url`/`styles` entirely.

---

## StyleCaption

One caption for one style — the scored leaf.

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `style` | `str` | yes | One of the 4 known styles. |
| `caption` | `str` | yes | Non-empty after strip; single line preferred; length-bounded. May be a deterministic **fallback** caption. |
| `is_fallback` | `bool` | no (default `false`) | `true` when the deterministic fallback path produced it (internal/telemetry; not scored). |

Rules:
- A `StyleCaption` **must exist for every requested + known style** by output time; the fallback path
  guarantees this. A missing style is scored **0** by the harness (see [16-io-contract.md](16-io-contract.md)).
- `caption` must be grounded — constraint enforced upstream in synthesis, not by the schema.

---

## ClipResult

All styled captions for a single task.

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `task_id` | `str` | yes | Echoes the input `Task.task_id`. |
| `captions` | `dict[str, str]` | yes | Map of `style_key → caption` for every requested + known style. Serialized form of the task's `StyleCaption`s. |

Rules:
- Keys of `captions` are a subset of the 4 known styles and equal the task's requested+known styles.
- Ordering is not significant to scoring; keys are emitted in the closed-set canonical order for
  readability.

---

## ResultsOutput

The root document written to `/output/results.json`.

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `results` | `list[ClipResult]` | yes | One entry per input task, in input order. |

Rules:
- `len(results) == len(tasks)` — every task yields a `ClipResult`, even failed ones (possibly with
  fewer/fallback captions).
- The whole document is schema-validated before writing; on validation failure the writer repairs to
  a minimal valid shape rather than emitting invalid JSON.

---

## Transcript / Segment / Word

Produced by the Audio stage (S2). May be empty-but-valid for silent clips.

### Word

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `text` | `str` | yes | The token text. |
| `start` | `float` | yes | Seconds ≥ 0. |
| `end` | `float` | yes | Seconds ≥ `start`. |
| `probability` | `float` | no | ∈ [0,1] if present (model confidence). |

### Segment

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `id` | `int` | yes | ≥ 0; monotonic within the transcript. |
| `text` | `str` | yes | Concatenated segment text. |
| `start` | `float` | yes | Seconds ≥ 0. |
| `end` | `float` | yes | Seconds ≥ `start`. |
| `words` | `list[Word]` | yes | Word timings within `[start, end]`; may be empty. |

### Transcript

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `language` | `str \| None` | no | Detected language code, if any. |
| `segments` | `list[Segment]` | yes | May be **empty** (no speech). Segment `start` times non-decreasing. |
| `text` | `str` | yes | Full concatenated text; empty string when no speech. |

Rules:
- Timestamps are monotonic and non-negative; a validator rejects `end < start`.
- An empty `segments`/`text` is valid — downstream treats vision as the sole evidence source.

---

## Keyframe

Produced by the Vision stage (S4).

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `index` | `int` | yes | ≥ 0; selection order. |
| `timestamp` | `float` | yes | Seconds ≥ 0; within clip duration. |
| `image_path` | `str` | yes | Scratch path to the encoded frame passed to the VLM. |
| `aligned_segment_id` | `int \| None` | no | Nearest transcript segment id by timestamp; `None` if transcript empty. |
| `score` | `float` | no | Scene-change/variance score used for selection. |

Rules:
- The keyframe list is **bounded** by the configured `max_keyframes` cap.
- At least **one** keyframe exists for every clip (static-clip fallback guarantees this).
- `timestamp`s are non-decreasing across the ordered list.

---

## CaptionState

Runtime dataclass threaded through the six stages (not serialized to output). Defined in full in
[../PLAN.md](../PLAN.md#pipeline-state-object).

| Field | Type | Written by | Notes |
| --- | --- | --- | --- |
| `task_id` | `str` | loader | From `Task`. |
| `video_path` | `str \| None` | S1 | Local downloaded video. |
| `wav_path` | `str \| None` | S1 | Mono 16 kHz WAV. |
| `transcript` | `Transcript \| None` | S2 | Empty-but-valid allowed. |
| `keyframes` | `list[Keyframe]` | S4 | Bounded, ≥1. |
| `captions` | `dict[str, StyleCaption]` | S5/S6 | One per requested+known style; may be fallback. |
| `timings` | `dict[str, float]` | all stages | Stage name → seconds; feeds latency asserts. |
| `errors` | `list[str]` | any stage | Structured, non-fatal; never causes non-zero exit. |

---

## Input JSON shape (`/input/tasks.json`)

```json
[
  {
    "task_id": "v1",
    "video_url": "https://example.com/clips/nature_waterfall.mp4",
    "styles": ["formal"]
  },
  {
    "task_id": "v2",
    "video_url": "https://example.com/clips/human_action_cooking.mp4",
    "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
  },
  {
    "task_id": "v3",
    "video_url": "https://example.com/clips/technology_demo.mp4",
    "styles": ["formal", "humorous_tech"]
  }
]
```

## Output JSON shape (`/output/results.json`)

```json
{
  "results": [
    {
      "task_id": "v1",
      "captions": {
        "formal": "A wide waterfall cascades over dark rock into a mist-covered pool below."
      }
    },
    {
      "task_id": "v2",
      "captions": {
        "formal": "A person dices vegetables on a wooden board, then slides them into a hot pan.",
        "sarcastic": "Ah yes, another culinary genius rediscovering that knives cut vegetables.",
        "humorous_tech": "Chopping veggies with zero latency — the prep pipeline is fully parallelized.",
        "humorous_non_tech": "Someone is on a mission to defeat an innocent onion, and it's winning the tear war."
      }
    },
    {
      "task_id": "v3",
      "captions": {
        "formal": "A hand demonstrates a foldable device, opening and closing the hinged screen.",
        "humorous_tech": "Ship it: the hinge passed its open/close smoke test on the first commit."
      }
    }
  ]
}
```

The authoritative JSON Schemas and the missing-style-scores-0 rule live in
[16-io-contract.md](16-io-contract.md).
