# 03 — Captioning Pipeline

This is the heart of OmniCaption: six stages that turn a `video_url` into styled captions. See the
diagram in [01-architecture](01-architecture.md).

## Stage 1 — Ingestion

- Read `/input/tasks.json` and validate it as a list of `{task_id, video_url, styles[]}`.
- Download each `video_url` to local scratch.
- Run **ffmpeg** to extract audio as **mono, 16 kHz WAV** — the exact format faster-whisper expects.
  Downmixing to mono and resampling to 16 kHz avoids Whisper doing it internally and keeps decode
  deterministic.

## Stage 2 — Audio

- Load **faster-whisper** backed by **CTranslate2-HIP**, targeting the host gfx architecture.
- Transcribe the WAV and emit **word-level timestamps**. Word-level timing is what lets Stage 4 align
  keyframes to the moments they describe.
- Keep the transcript in CPU memory; it must survive the Whisper teardown in Stage 3.

## Stage 3 — Memory Reclamation

The reason the pipeline runs on 8 GB cards. After transcription:

```python
del whisper_model
gc.collect()
torch.cuda.empty_cache()
```

This returns Whisper's VRAM to the allocator **before** the VLM loads. Without it, loading Gemma 4 on
top of a resident Whisper OOMs on 8–16 GB cards. This is the sequential-VRAM-execution rationale in
one stage: only one heavy model is resident at any instant.

## Stage 4 — Vision

- Run **OpenCV pixel-variance scene-change detection** over the decoded frames. When frame-to-frame
  pixel variance crosses a threshold, a scene boundary is likely — pick a representative keyframe from
  each detected scene.
- **Align** keyframes to transcript timestamps so each image is paired with the words spoken around
  it. This gives Stage 5 grounded visual + textual evidence rather than random frames.
- Keep the keyframe budget small; more frames means more visual tokens and slower synthesis. See
  adaptive budgeting proposals in [14-optimization-suggestions](14-optimization-suggestions.md).

## Stage 5 — Synthesis

- Load **Gemma 4 E4B in 4-bit** via Hugging Face Transformers (now that VRAM is free).
- **Modality-ordering rule — this is not optional.** Gemma 4 requires visual tokens **before** text
  and audio **after** text. Build the prompt strictly as:

  ```
  [ keyframes (images) ]  →  [ transcript text ]  →  [ style system prompt ]
  ```

- Generate the styled caption for each requested style. Style system prompts live in
  [13-prompt-engineering-playbook](13-prompt-engineering-playbook.md).
- **Sarcasm uses Pragmatic Metacognitive Prompting (PMP)** — a metacognitive chain:
  1. Analyze the **literal facts** in the scene.
  2. Identify **contradictions** or incongruities between expectation and reality.
  3. Determine the **pragmatic meaning** (what a dry observer would actually imply).
  4. Write the **dry caption** — understated, no cheesy puns.

## Stage 6 — Output

- Validate every caption against the results schema.
- Write `/output/results.json` with a caption for **every requested style of every task**.
- Exit with code **0**. A missing style scores 0, so if a style failed, emit the deterministic
  fallback caption rather than omitting it (see [14-optimization-suggestions](14-optimization-suggestions.md)).
