# Contract: Pipeline Stage Interfaces

**Related:** [../PLAN.md](../PLAN.md) · [15-data-model.md](15-data-model.md) · [16-io-contract.md](16-io-contract.md) · [01-architecture.md](01-architecture.md)

This defines the interface contract between the **6 pipeline stages**. Every stage is a function that
takes the shared `CaptionState` (plus stage-scoped resources) and returns the mutated state. The
orchestrator (`app/pipeline/orchestrator.py`) runs them in order per task, owns error handling, and
guarantees exit 0. `CaptionState` is defined in [../PLAN.md](../PLAN.md#pipeline-state-object).

General signature:

```python
def stage(state: CaptionState, *, cfg: Settings) -> CaptionState: ...
```

Stages mutate and return `state`. Each stage records its wall-clock into `state.timings[stage_name]`
and appends any non-fatal problem to `state.errors` (never raises past the orchestrator).

---

## Stage 1 — Ingestion (`s1_ingestion.py`)

| | |
| --- | --- |
| **Reads** | `state.task_id`, the task's `video_url`. |
| **Does** | Download `video_url` → `state.video_path`; run ffmpeg → mono 16 kHz WAV at `state.wav_path`. |
| **Writes** | `state.video_path`, `state.wav_path`. |
| **Errors** | Unreachable URL or ffmpeg failure → append to `state.errors`, leave `wav_path=None`; the task continues (vision-only or full fallback downstream). Batch never aborts. |
| **Determinism** | Fixed ffmpeg params; scratch paths keyed by `task_id`. |

## Stage 2 — Audio (`s2_audio.py`)

| | |
| --- | --- |
| **Reads** | `state.wav_path`. |
| **Does** | Load faster-whisper (CTranslate2-HIP) on the AMD device; transcribe → `Transcript` with segment + word timestamps; copy transcript to CPU memory. |
| **Writes** | `state.transcript` (may be **empty-but-valid**). |
| **Handoff out** | **Must** hand the STT model to Stage 3 for teardown before returning control to any GPU stage. |
| **Errors** | Missing `wav_path` or STT failure → `state.transcript = Transcript(empty)`, append error; vision becomes sole evidence. |

## Stage 3 — Memory Reclamation (`s3_reclaim.py`)

| | |
| --- | --- |
| **Reads** | The STT model handle from Stage 2. |
| **Does** | `del model` → `gc.collect()` → `torch.cuda.empty_cache()`; log freed VRAM. |
| **Writes** | Nothing on `state` except `state.timings["reclaim"]`. |
| **Invariant** | On return, **no STT weights remain in VRAM**. This is the VRAM handoff barrier (below). |
| **Errors** | Reclamation is best-effort and idempotent; failures are logged but never fatal. |

## Stage 4 — Vision (`s4_vision.py`)

| | |
| --- | --- |
| **Reads** | `state.video_path`, `state.transcript`. |
| **Does** | OpenCV pixel-variance scene-change detection → bounded keyframe list; align each keyframe to the nearest transcript segment; encode frames to scratch. |
| **Writes** | `state.keyframes` (bounded by `cfg.max_keyframes`, always ≥1). |
| **Errors** | Decode failure → static-clip fallback sampling (first/mid/last); if even that fails, a single synthetic frame or empty list with a recorded error (synthesis then relies on transcript only). |
| **Cost** | CPU-side; no GPU model weight — safe to run before the VLM loads. |

## Stage 5 — Synthesis (`s5_synthesis.py`)

| | |
| --- | --- |
| **Reads** | `state.keyframes`, `state.transcript`, the task's requested+known styles. |
| **Does** | Load Gemma 4 E4B-it (4-bit) on the AMD device; for each requested style, assemble a prompt in the **locked modality order (images → transcript → style prompt)** and generate a `StyleCaption`. `sarcastic` runs the **PMP chain**. Evidence is extracted once and reused across styles. |
| **Writes** | `state.captions[style] = StyleCaption(...)` for every requested+known style. |
| **Handoff in** | **Requires** Stage 3's invariant (STT VRAM already freed) before loading the VLM. |
| **Errors / fallback** | Per-style: on VLM error or per-request timeout, write a **deterministic fallback** `StyleCaption(is_fallback=True)` derived from transcript/keyframes. No style is ever left unset. Quant-backend absent → degrade to bf16/fp16. |

## Stage 6 — Output (`s6_output.py`)

| | |
| --- | --- |
| **Reads** | `state.captions` for all tasks. |
| **Does** | Assemble `ClipResult` per task → `ResultsOutput`; **schema-validate** against the output schema; hand to `results_writer` for an atomic write to `/output/results.json`. |
| **Writes** | `/output/results.json`. |
| **Errors** | Validation failure → repair to a minimal valid shape and write anyway (never emit invalid JSON). |
| **Exit** | After a successful write, the entrypoint calls `sys.exit(0)` regardless of captured per-task errors. |

---

## VRAM handoff protocol (Audio → Vision/Synthesis)

The single most important runtime invariant (non-negotiable II). The two heavy models are **never
co-resident**.

```
S2 Audio (Whisper on GPU)
   │  transcript copied to CPU memory
   ▼
S3 Reclamation ── del model · gc.collect() · torch.cuda.empty_cache()
   │  BARRIER: no STT weights in VRAM
   ▼
S4 Vision (CPU/OpenCV — no GPU weight)
   ▼
S5 Synthesis (Gemma 4 E4B loads into the freed VRAM)
```

Protocol rules:
1. Stage 2 must **not** return until the transcript is safely on CPU memory.
2. Stage 3 is a **mandatory barrier** between any two GPU model stages; the orchestrator refuses to
   enter Stage 5 unless reclamation ran.
3. Stage 4 (vision) is CPU-side and may run either side of the barrier without VRAM contention; it is
   placed after reclamation so the GPU is idle during frame work.
4. Stage 5 loads the VLM only after the barrier, guaranteeing peak VRAM = max(STT, VLM), not their sum
   — the requirement for 8 GB-class cards.
5. A sequential-VRAM assertion (task T084) proves both models are never simultaneously allocated.

---

## Error & fallback behavior (summary)

| Failure | Stage | Behavior | Result |
| --- | --- | --- | --- |
| Bad `video_url` / download fail | S1 | Record error, `wav_path=None`, continue | Vision-only or full fallback captions |
| ffmpeg decode fail | S1 | Record error, continue | As above |
| STT model / transcribe fail | S2 | Empty-but-valid transcript | Vision is sole evidence |
| No speech in clip | S2 | Empty transcript (not an error) | Vision-grounded captions |
| Reclamation hiccup | S3 | Log, continue (best-effort) | Barrier still enforced by orchestrator |
| Video decode fail | S4 | Static-clip fallback → ≥1 frame | Keyframes still produced |
| VLM load / quant fail | S5 | Degrade bf16; if still failing → fallback captions | Every style still emitted |
| Per-request timeout | S5 | Trip deterministic fallback for that style | Keeps <30 s/request |
| Output schema invalid | S6 | Repair to valid shape, write | Valid `results.json` |
| Any captured error | — | Never propagates to exit code | Process exits **0** |

Every path preserves the two hard guarantees: **a caption for every requested+known style** and
**exit 0** (spec AC6.1–AC6.3).
