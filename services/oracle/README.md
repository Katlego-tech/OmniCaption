# OmniCaption Video-Oracle (`services/oracle`) — Track 3

Semantic moment search + grounded RAG QA over captioned clips. The index embeds captions and
transcript segments via the Fireworks AI embeddings API, and — optionally — **keyframe images via
CLIP** (`pip install open_clip_torch pillow`; skipped gracefully when absent). Answers come from
the Fireworks VLM, strictly grounded in retrieved moments with `[task_id @ t]` citations.

Ships **separate from the Track 2 image** (AC7.4): pure-Python index, two runtime deps
(`httpx`, `pydantic`), no model weights.

## Usage

```bash
cd services/oracle
pip install -r requirements-dev.txt
python -m pytest -q && ruff check .          # the gate (all model calls mocked)

export FIREWORKS_API_KEY=fw-…
python -m oracle.cli build  --results ../captioner/out/results.json \
  --transcripts ../captioner/out/transcripts.json \
  --keyframes ../captioner/out/keyframes \
  --out ./index.json
python -m oracle.cli search --index ./index.json "person on a bike"
python -m oracle.cli ask    --index ./index.json "what happens in v1?"
```

The captioner emits the sidecars automatically: `transcripts.json` by default, keyframe JPEGs
when `OMNICAPTION_EMIT_KEYFRAMES=1`.

## Serving through the backend API

`services/api` picks the index up automatically: place it at `<DATA_DIR>/oracle/index.json`
(or run the CLI with that path) and `/api/search` + `/api/qa` switch from 501 stubs to live
answers. The Fireworks key comes from the `X-Fireworks-Key` request header (the web frontend
sends the key stored on its Accounts page) or the backend's `FIREWORKS_API_KEY` env var.
