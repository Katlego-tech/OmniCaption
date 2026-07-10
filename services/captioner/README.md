# OmniCaption — Captioner Service

Stylistic video captioning agent for the **AMD Developer Hackathon (ACT II),
Track 2**. A Dockerized (`linux/amd64`) dual-model hybrid pipeline that reads a
batch of video tasks, transcribes and analyzes each clip, and emits captions in
four distinct styles.

The container reads `/input/tasks.json`, writes `/output/results.json`, and exits
`0`. It always produces a schema-valid output file, even on partial failure.

## Styles

- `formal` — objective, inverted-pyramid archivist prose.
- `sarcastic` — dry, deadpan critic; understated, never zany.
- `humorous_tech` — DevOps engineer software-metaphor jokes.
- `humorous_non_tech` — observational stand-up, no jargon.

## The six-stage pipeline

1. **Ingestion** (`pipeline/ingestion.py`) — read `tasks.json`, download each
   `video_url`, extract mono 16 kHz WAV via an `ffmpeg` subprocess. Clips with
   no audio track yield an empty (but valid) transcript instead of an error.
2. **Audio** (`pipeline/audio.py`) — local faster-whisper (CTranslate2)
   transcription with word-level timestamps: HIP/ROCm in the container, int8
   CPU fallback for local dev.
3. **Memory reclamation** (`pipeline/memory.py`) — `del` the Whisper model,
   `gc.collect()`, `torch.cuda.empty_cache()` (guarded for ROCm/CPU) before any
   synthesis work.
4. **Vision** (`pipeline/vision.py`) — OpenCV pixel-variance scene-change
   keyframe extraction (max 8, downsampled to ≤1024 px); align keyframes to
   transcript timestamps.
5. **Synthesis** (`pipeline/synthesis.py`) — remote **Fireworks AI** VLM
   (default `accounts/fireworks/models/kimi-k2p6`, served on Fireworks'
   AMD MI300X backend). Messages: system prompt = style persona + output-tag
   rules; user prompt = keyframe images (base64 JPEG) then transcript text.
   Temperature 0. The model reasons freely but must emit the final caption
   inside `<captionStyle>…</captionStyle>` tags; only the tagged text is kept.
   Any per-style failure produces a deterministic fallback caption — a
   requested style is never missing from the output.
6. **Output** (`pipeline/output.py`) — validate against the schema, write
   `/output/results.json`, exit `0`.

> The PMP (Pragmatic Metacognitive Prompting) chain in `prompts/pmp.py` is
> retained as an optional module but is **not** in the runtime path — it was
> removed from sarcasm generation to avoid token truncation on reasoning VLMs.

## Architecture map

```
app/
  main.py            entrypoint (load -> run -> write -> exit 0)
  pipeline/          the six stages + orchestrator
  prompts/           style system prompts (+ unused PMP module)
  core/              config, schema, errors, timing, GPU/ROCm, logging
  models/            faster-whisper loader (+ legacy local-VLM loader)
tests/               unit / integration / contract + fixtures
run_local_test.py    real end-to-end run against Fireworks (needs API key)
```

## Configuration

Settings come from `OMNICAPTION_*` environment variables (see
[`.env.example`](.env.example)), plus `FIREWORKS_API_KEY` for the synthesis
stage. Key knobs: `OMNICAPTION_FIREWORKS_VLM_MODEL`, `OMNICAPTION_MAX_KEYFRAMES`
(default 8), `OMNICAPTION_MAX_NEW_TOKENS` (default 4096 — reasoning VLMs spend
tokens thinking before the tagged caption), and the budget/timeout values.

## Build the image

```bash
docker build --platform linux/amd64 -t omnicaption-captioner .
```

Whisper weights should be baked into the image (see the model-cache layer in
the `Dockerfile`) so container startup does no model download and stays under
the 60 s budget. The VLM needs no weights — it is a remote API.

## Run locally

```bash
# tasks.json in ./input, results.json appears in ./output
docker run --rm \
  --device=/dev/kfd --device=/dev/dri \
  -e FIREWORKS_API_KEY=fw_... \
  -v "$(pwd)/input:/input" \
  -v "$(pwd)/output:/output" \
  omnicaption-captioner
```

Select a specific GPU arch by overriding the ROCm env vars, e.g. for an
RX 7900 XTX: `-e PYTORCH_ROCM_ARCH=gfx1100 -e HSA_OVERRIDE_GFX_VERSION=11.0.0`.

You can also run outside Docker for development. With a `.env` at the repo root
(copy `.env.example` and set `FIREWORKS_API_KEY`), the end-to-end smoke script
downloads a real clip, runs the full pipeline, and prints `results.json`:

```bash
pip install -r requirements-dev.txt
python run_local_test.py
```

Or point the entrypoint at your own directories:

```bash
OMNICAPTION_INPUT_DIR=./input OMNICAPTION_OUTPUT_DIR=./output python -m app.main
```

## Run tests

```bash
pip install -r requirements-dev.txt
ruff check .
pytest            # unit + integration + contract; STT and VLM calls are mocked
```

No API key or GPU is needed for the test suite.

## Constraints honored

- ≤ 10 min total runtime, < 30 s/request (soft-guarded in the orchestrator).
- ≤ 10 GB image, startup < 60 s (baked Whisper weights; the VLM is remote).
- AMD compute end to end: local STT on ROCm/HIP (MI300X gfx942, RX 7900 XTX
  gfx1100, RX 6600 gfx1032, Ryzen AI gfx1103/gfx1150; honors
  `PYTORCH_ROCM_ARCH` / `HSA_OVERRIDE_GFX_VERSION`), and VLM synthesis on
  Fireworks AI's AMD MI300X-powered platform.
