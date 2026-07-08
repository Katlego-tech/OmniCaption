# 01 — Architecture

## Container I/O contract

OmniCaption is a batch job, not a server. The evaluation harness controls everything through two
mounted paths:

- **Input:** `/input/tasks.json` — a JSON list of tasks, each `{task_id, video_url, styles[]}`.
- **Output:** `/output/results.json` — captions for every requested style of every task.
- **Exit:** the process must exit with code **0**. A crash or non-zero exit forfeits the run.

```
/input/tasks.json  ──►  [ OmniCaption container ]  ──►  /output/results.json  (exit 0)
```

The container must **start within 60 s**, complete the whole batch in **≤10 min**, respond in
**<30 s per request**, and ship as a **≤10 GB** image for **linux/amd64**. It must demonstrably use
AMD compute or it is disqualified. See [06-judging-criteria](06-judging-criteria.md).

## The 6-stage pipeline

```
 tasks.json
    │
    ▼
┌─────────────────┐   ffmpeg: mono 16 kHz WAV
│ 1. INGESTION    │   download video_url ──────────────┐
└────────┬────────┘                                    │
         ▼                                              │
┌─────────────────┐   faster-whisper on CTranslate2-HIP│
│ 2. AUDIO        │   word-level timestamps ◄───────────┘
└────────┬────────┘
         ▼
┌─────────────────┐   del whisper; gc.collect();
│ 3. MEMORY       │   torch.cuda.empty_cache()
│    RECLAMATION  │   ── frees VRAM before the VLM loads
└────────┬────────┘
         ▼
┌─────────────────┐   OpenCV pixel-variance scene change
│ 4. VISION       │   keyframes aligned to transcript ts
└────────┬────────┘
         ▼
┌─────────────────┐   Gemma 4 E4B (4-bit) via Transformers
│ 5. SYNTHESIS    │   prompt order: images → text → audio
│                 │   sarcasm uses PMP chain
└────────┬────────┘
         ▼
┌─────────────────┐   validate schema, write results.json
│ 6. OUTPUT       │   exit 0 (missing style → 0 score)
└────────┬────────┘
         ▼
   /output/results.json
```

Each stage is covered in depth in [03-captioning-pipeline](03-captioning-pipeline.md).

## Sequential model loading keeps VRAM within budget

The two heavy models — faster-whisper (STT) and Gemma 4 E4B (VLM) — never live in VRAM at the same
time. This is the single most important architectural decision, because the pipeline must run on
cards as small as the **RX 6600 (8 GB)**.

1. Load Whisper, transcribe the whole clip, capture the transcript to CPU memory.
2. **Stage 3 explicitly tears Whisper down** — `del`, `gc.collect()`, `torch.cuda.empty_cache()` —
   so its VRAM is returned to the allocator.
3. Only then load Gemma 4 E4B in 4-bit and run Stage 5 synthesis.

Loading both concurrently would OOM on 8–16 GB cards. Sequential execution trades a little wall-clock
time (a second model load) for the ability to run on the entire AMD GPU target range. See
[05-amd-rocm-optimization](05-amd-rocm-optimization.md) for the gfx target details.
