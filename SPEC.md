# OmniCaption — Specification (the WHAT)

**Track:** AMD Developer Hackathon (ACT II) — Track 2 (primary), Track 3 "Video-Oracle" (stretch)
**Related:** [PLAN.md](PLAN.md) · [TASKS.md](TASKS.md) · [docs/15-data-model.md](docs/15-data-model.md) · [docs/16-io-contract.md](docs/16-io-contract.md) · [docs/17-pipeline-stages.md](docs/17-pipeline-stages.md) · [docs/09-research-summary.md](docs/09-research-summary.md)

---

## Overview

OmniCaption is a Dockerized, batch, dual-model hybrid pipeline that turns short video clips into
**styled natural-language captions**. It is a headless job — not a server. An automated evaluation
harness mounts a task file into the container, the container processes every task, writes a results
file, and exits cleanly.

For each `(clip, style)` pair requested, OmniCaption produces one caption that is (a) **faithful** to
what actually happens in the clip (grounded in the transcribed audio and sampled keyframes) and (b)
**stylistically on-tone** for the requested register. Four styles are in scope:

| Style key | Register |
| --- | --- |
| `formal` | Neutral, objective, precise description of events. |
| `sarcastic` | Dry, ironic, understated; says the opposite of the literal praise. |
| `humorous_tech` | Playful humor using software/engineering framing and metaphors. |
| `humorous_non_tech` | Playful, everyday humor with no technical framing. |

The whole system is optimized to run inside hard runtime and memory budgets on **AMD compute
(ROCm/HIP)**. Missing or malformed output for a requested style scores **0**, so the pipeline is
built to always emit *something schema-valid* for every requested style, even under failure.

This specification describes **WHAT** OmniCaption must do and the criteria by which it is judged. The
**HOW** (concrete stack, module layout, build phases) lives in [PLAN.md](PLAN.md) and
[docs/09-research-summary.md](docs/09-research-summary.md).

### Goals

- Accept a batch of captioning tasks and produce a caption per requested style per clip.
- Ground every caption in evidence extracted from the clip (audio transcript + visual keyframes).
- Stay inside the runtime, per-request, startup, and image-size budgets.
- Provably use AMD compute for both model stages.
- Emit strictly schema-valid `/output/results.json` and exit `0`.

### Non-goals

- Real-time / streaming captioning (this is a batch job).
- A web UI or interactive product surface (Track 3 UI is out of scope for the core submission).
- Fine-tuning or training any model.
- Supporting GPUs outside the declared AMD target range.

---

## Actors

### Primary actor — the automated evaluation harness

The **evaluation harness** is the sole runtime caller. It:

1. Mounts `/input/tasks.json`, a list of `{task_id, video_url, styles[]}` objects.
2. Starts the container (`linux/amd64`).
3. Waits for the container to write `/output/results.json` and exit `0`.
4. Scores each `(clip, style)` on **Accuracy** (visual fidelity) and **Style Match** (tone).

The harness never sees pipeline internals. Its entire contract is the two mounted JSON files, the
exit code, and the wall-clock/resource budgets. See [docs/16-io-contract.md](docs/16-io-contract.md).

### Secondary actors

- **The development team** (Katlego — leader, repo owner, works with Gemini; Tumo — co-builder,
  works with Claude). They build, test, and iterate on the pipeline. They need reproducible builds, a
  green `main`, and shared coordination state (see [AGENTS.md](AGENTS.md)).
- **Track-3 "Video-Oracle" end users** (stretch only). Humans who issue natural-language search and
  question-answering queries against an indexed video corpus. Only relevant if US7 is pursued.

---

## User Stories

Each story is independently testable and maps to a delivery phase in [TASKS.md](TASKS.md). Stories
US1–US6 form the **MVP** (a complete, scorable Track 2 submission). US7 is a stretch goal.

### US1 — Ingest tasks and video (priority: P1)

**As** the evaluation harness, **I want** OmniCaption to read my task file and fetch each video **so
that** every clip is available locally as decoded audio for downstream processing.

Acceptance criteria:

- **AC1.1** Given a valid `/input/tasks.json`, the pipeline parses it into a typed list of tasks
  without error, preserving `task_id`, `video_url`, and the requested `styles[]`.
- **AC1.2** Given a task, the pipeline downloads `video_url` to local storage and extracts a
  **mono, 16 kHz WAV** track via ffmpeg.
- **AC1.3** Given an unreachable `video_url` or a decode failure, the pipeline records a structured
  error for that task and continues with the remaining tasks (no whole-batch abort).
- **AC1.4** Given a `styles[]` entry that is not one of the four known styles, the pipeline ignores
  the unknown style and still processes the known ones (unknown styles are simply not emitted).
- **AC1.5** Given a malformed top-level `tasks.json` (not a list, missing required keys), the
  pipeline fails fast with a clear, greppable error message.

### US2 — Transcribe audio (priority: P1)

**As** the evaluation harness, **I want** the clip's speech transcribed with word-level timing **so
that** captions can be grounded in what is said and aligned to the timeline.

Acceptance criteria:

- **AC2.1** Given a WAV file, the pipeline produces a transcript with **segment- and word-level
  timestamps**.
- **AC2.2** Transcription runs on **AMD compute** (Fireworks AI API hosted on AMD MI300X), verifiable from logs.
- **AC2.3** Given a clip with no intelligible speech, the pipeline returns an **empty but valid**
  transcript (empty segment list) rather than erroring; downstream stages treat vision as the sole
  evidence source.
- **AC2.4** After transcription completes, the transcript is captured to CPU memory; since inferences are remote, local VRAM footprint is negligible.

### US3 — Extract keyframes (priority: P1)

**As** the evaluation harness, **I want** representative frames sampled from the clip **so that**
captions reflect what is visually happening, not only what is spoken.

Acceptance criteria:

- **AC3.1** Given a video, the pipeline selects **scene-change keyframes** using a pixel-variance
  heuristic (OpenCV), bounded by a configurable maximum count (token-budget guardrail).
- **AC3.2** Each selected keyframe carries its **timestamp** and is aligned to the nearest transcript
  segment/word so image and speech evidence share a timeline.
- **AC3.3** Given a static clip with no scene changes, the pipeline still returns at least one
  keyframe (e.g. first/mid/last sampling fallback).
- **AC3.4** Keyframe extraction is CPU-side and adds no additional GPU model weight.

### US4 — Generate a formal, objective caption (priority: P1)

**As** the evaluation harness, **I want** a neutral, accurate description of the clip **so that** I
can score visual fidelity against ground truth.

Acceptance criteria:

- **AC4.1** Given a transcript and aligned keyframes, the pipeline generates a `formal` caption using
  the vision-language model with the locked modality order (images → transcript → style prompt).
- **AC4.2** The `formal` caption describes **only** content supported by the audio and/or frames — no
  invented objects, actors, or events (faithful & grounded).
- **AC4.3** VLM synthesis runs on **AMD compute** (Fireworks AI API hosted on AMD MI300X), verifiable from logs.
- **AC4.4** Given a VLM failure or timeout, the pipeline emits a **deterministic fallback caption**
  derived from available evidence (e.g. transcript summary) so the style is never missing.

### US5 — Generate the humor and sarcasm styles (priority: P2)

**As** the evaluation harness, **I want** the sarcastic and two humorous styles **so that** I can
score tonal match in addition to fidelity.

Acceptance criteria:

- **AC5.1** For a requested `sarcastic` style, the pipeline runs the **PMP metacognitive chain**
  (perceive → interpret → invert → phrase) and emits a caption whose literal reading diverges from a
  straight description while remaining recognizably about the same events.
- **AC5.2** For `humorous_tech`, the caption stays grounded but frames events with software /
  engineering metaphors.
- **AC5.3** For `humorous_non_tech`, the caption stays grounded and is playful without technical
  framing.
- **AC5.4** All styled captions remain **evidence-grounded** — tone is layered over true content, not
  fabricated content.
- **AC5.5** Requesting multiple styles for one clip reuses the same transcript and keyframes (evidence
  is extracted once per clip, not once per style).

### US6 — Produce schema-valid results within all limits (priority: P1)

**As** the evaluation harness, **I want** a single well-formed results file produced inside the
runtime and memory budgets **so that** the run is scorable and not disqualified.

Acceptance criteria:

- **AC6.1** The pipeline writes `/output/results.json` containing, for every task, a caption for every
  **requested and known** style, matching the output schema in
  [docs/16-io-contract.md](docs/16-io-contract.md).
- **AC6.2** The output is **schema-validated** before writing; a validation failure is repaired to a
  valid fallback shape rather than emitting invalid JSON.
- **AC6.3** The process **exits `0`** on completion, even when individual tasks failed (their errors
  are captured; their styles carry fallback captions).
- **AC6.4** The whole batch completes in **≤10 minutes**; each request resolves in **<30 seconds**.
- **AC6.5** Container **startup is <60 seconds**; the built image is **≤10 GB**.
- **AC6.6** Both model stages run remotely via Fireworks AI API, ensuring no local model co-residency or local VRAM constraints exist.

### US7 — Video-Oracle semantic search + QA (priority: P3, stretch — Track 3)

**As** a Track-3 end user, **I want** to search an indexed video corpus in natural language and ask
questions about it **so that** I can retrieve relevant clips/moments and get grounded answers.

Acceptance criteria:

- **AC7.1** Given a corpus of clips, the system builds a **multimodal vector index** (CLIP/USM
  embeddings) over frames/transcripts.
- **AC7.2** Given a natural-language query, the system returns the most relevant clips/moments ranked
  by similarity.
- **AC7.3** Given a question about retrieved content, the system produces a **grounded RAG answer**
  citing the supporting moment(s), served via vLLM-ROCm (Gemma 4 31B).
- **AC7.4** Track 3 is only enabled when Track 2 (US1–US6) is fully green; it must not regress the
  Track 2 runtime or image budgets.

---

## Cross-cutting requirements

These apply to the whole pipeline regardless of story.

### CC1 — Runtime & throughput

- Whole batch **≤10 min**; per request **<30 s**; startup **<60 s**. Budgets are measured, logged,
  and asserted in latency tests.

### CC2 — Memory

- The built image is **≤10 GB**.
- STT and VLM are loaded **sequentially**; a dedicated memory-reclamation step (`del` → `gc.collect()`
  → empty GPU cache) runs between them so the pipeline fits **8 GB-class AMD cards**.

### CC3 — AMD compute is mandatory

- Both model stages must **provably execute on AMD ROCm/HIP**. Absence of AMD compute is an automatic
  disqualification, so the pipeline logs the active device and fails loudly if no AMD device is
  present in the enforced (non-dev) mode. See principle **V** in [PLAN.md](PLAN.md).

### CC4 — Faithfulness & grounding

- No caption may assert content not supported by the transcript and/or sampled keyframes. Style
  transforms tone, never facts.

### CC5 — Determinism where possible

- Given identical inputs and seeds, evidence extraction (WAV, transcript, keyframe selection) is
  deterministic. VLM sampling is pinned to low/zero temperature with a fixed seed to maximize
  reproducibility; the **fallback caption path is fully deterministic**.

### CC6 — Robustness / graceful degradation

- Any single-task or single-stage failure degrades to a **valid fallback** for the affected style and
  never aborts the batch or produces a non-zero exit.

---

## Demo acceptance criteria (baseline clips)

Three internal baseline clips are used to demonstrate end-to-end behavior before the hidden
evaluation set. These are the "definition of done" for the MVP demo.

| Clip | Content | Demo expectation |
| --- | --- | --- |
| **v1** | Nature / landscape, minimal speech | Produces a grounded `formal` caption describing the scene from **keyframes alone**; empty transcript handled cleanly (AC2.3, AC3.3). |
| **v2** | Human action with clear speech | Produces all four styles; `formal` matches the action, `sarcastic` inverts tone while staying on-topic, both humor styles stay grounded (US4, US5). |
| **v3** | Technology / device demo | `humorous_tech` uses apt engineering framing; full batch of v1+v2+v3 completes **≤10 min**, each request **<30 s**, output schema-valid, exit `0`, AMD device logged (US6, CC1–CC3). |

Demo is accepted when: all three clips run in a single batch, `/output/results.json` validates against
the output schema, every requested style is present, the run exits `0` within budget, and logs show
AMD/ROCm execution for both model stages.

---

## Success metrics (how the harness scores us)

For each clip `v` and style `s`, the harness assigns:

- **Accuracy** `A ∈ [0,1]` — visual/semantic fidelity to the clip.
- **Style Match** `M ∈ [0,1]` — how well the caption matches the requested tone.

The aggregate score over the hidden set is:

```
Φ = (1 / (|V| · |S|)) · Σ_v Σ_s ( α · A(v,s) + β · M(v,s) )
```

over ~12 hidden clips spanning **nature, urban, animals, human actions, sports, food, weather, and
technology**, each evaluated across the requested styles. A missing/invalid `(clip, style)` caption
contributes **0** to the sum — hence the always-emit-a-fallback rule (AC4.4, AC6.2).
