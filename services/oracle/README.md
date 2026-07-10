# OmniCaption Video-Oracle (`services/oracle`) — Track 3

Semantic moment search + grounded RAG QA over captioned clips. **Text-modality MVP**: the index
embeds captions (and optional transcript segments) via the Fireworks AI embeddings API and answers
questions with the Fireworks VLM, strictly grounded in retrieved moments with `[task_id @ t]`
citations. CLIP visual embeddings over keyframes are documented future work.

Ships **separate from the Track 2 image** (AC7.4): pure-Python index, two runtime deps
(`httpx`, `pydantic`), no model weights.

## Usage

```bash
cd services/oracle
pip install -r requirements-dev.txt
python -m pytest -q && ruff check .          # the gate (all model calls mocked)

export FIREWORKS_API_KEY=fw-…
python -m oracle.cli build  --results ../captioner/out/results.json --out ./index.json
python -m oracle.cli search --index ./index.json "person on a bike"
python -m oracle.cli ask    --index ./index.json "what happens in v1?"
```

## Serving through the backend API

`services/api` picks the index up automatically: place it at `<DATA_DIR>/oracle/index.json`
(or run the CLI with that path) and `/api/search` + `/api/qa` switch from 501 stubs to live
answers. The Fireworks key comes from the `X-Fireworks-Key` request header (the web frontend
sends the key stored on its Accounts page) or the backend's `FIREWORKS_API_KEY` env var.
