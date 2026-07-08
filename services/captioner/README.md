# OmniCaption — Captioner Service

Stylistic video captioning agent for the **AMD Developer Hackathon (ACT II),
Track 2**. A Dockerized (`linux/amd64`) dual-model hybrid pipeline that reads a
batch of video tasks, transcribes and analyzes each clip, and emits captions in
four distinct styles.

The container reads `/input/tasks.json`, writes `/output/results.json`, and exits
`0`. It always produces a schema-valid output file, even on partial failure.

## Styles

- `formal` — objective, inverted-pyramid archivist prose.
- `sarcastic` — dry, biting critic (uses Pragmatic Metacognitive Prompting).
- `humorous_tech` — DevOps engineer software-metaphor jokes.
- `humorous_non_tech` — observational stand-up, no jargon.

## The six-stage pipeline

1. **Ingestion** (`pipeline/ingestion.py`) — read `tasks.json`, download each
   `video_url`, extract mono 16 kHz WAV via an `ffmpeg` subprocess.
2. **Audio** (`pipeline/audio.py`) — faster-whisper (CTranslate2-HIP)
   transcription with word-level timestamps.
3. **Memory reclamation** (`pipeline/memory.py`) — `del` the Whisper model,
   `gc.collect()`, `torch.cuda.empty_cache()` (guarded for ROCm/CPU) so the two
   large models never co-reside in VRAM.
4. **Vision** (`pipeline/vision.py`) — OpenCV pixel-variance scene-change
   keyframe extraction; align keyframes to transcript timestamps.
5. **Synthesis** (`pipeline/synthesis.py`) — load Gemma 4 E4B-it (4-bit) via HF
   Transformers; build the chat prompt in order **images → transcript text →
   style system prompt**; generate. Sarcasm runs the PMP chain (literal facts →
   contradictions → pragmatic meaning → dry caption).
6. **Output** (`pipeline/output.py`) — validate against the schema, write
   `/output/results.json`, exit `0`.

## Architecture map

```
app/
  main.py            entrypoint (load -> run -> write -> exit 0)
  pipeline/          the six stages + orchestrator
  prompts/           style system prompts + PMP chain
  core/              config, schema, GPU/ROCm, logging
  models/            model ids + quantization + loaders
tests/               unit / integration / contract + fixtures
```

## Build the image

```bash
docker build --platform linux/amd64 -t omnicaption-captioner .
```

Model weights should be baked into the image (see the model-cache layer in the
`Dockerfile`) so container startup does no network I/O and stays under the 60 s
budget.

## Run locally

```bash
# tasks.json in ./input, results.json appears in ./output
docker run --rm \
  --device=/dev/kfd --device=/dev/dri \
  -v "$(pwd)/input:/input" \
  -v "$(pwd)/output:/output" \
  omnicaption-captioner
```

Select a specific GPU arch by overriding the ROCm env vars, e.g. for an
RX 7900 XTX: `-e PYTORCH_ROCM_ARCH=gfx1100 -e HSA_OVERRIDE_GFX_VERSION=11.0.0`.

You can also run outside Docker for development (models permitting):

```bash
pip install -r requirements-dev.txt
OMNICAPTION_INPUT_DIR=./input OMNICAPTION_OUTPUT_DIR=./output python -m app.main
```

## Run tests

```bash
pip install -r requirements-dev.txt
ruff check .
pytest            # unit + integration + contract; models are mocked
```

## Constraints honored

- ≤ 10 min total runtime, < 30 s/request (soft-guarded in the orchestrator).
- ≤ 10 GB image, startup < 60 s (baked weights, offline HF cache).
- AMD compute across MI300X (gfx942), RX 7900 XTX (gfx1100), RX 6600 (gfx1032),
  and Ryzen AI (gfx1103/gfx1150); honors `PYTORCH_ROCM_ARCH` and
  `HSA_OVERRIDE_GFX_VERSION`.

> Note: this is a hackathon scaffold. Model integration points are marked with
> `# TODO(hackathon):`. The package is importable and testable without the ML
> stack installed (heavy imports are deferred to call time).
