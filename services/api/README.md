# OmniCaption backend API (`services/api`)

The standalone FastAPI bridge between the web frontend ([docs/18-frontend-architecture.md](../../docs/18-frontend-architecture.md))
and the captioner pipeline (`services/captioner`). It **never loads models** — it reads and writes
the captioner's file contract (`tasks.json` / `results.json`) and launches the pipeline as a
subprocess, so it deploys on any cheap host while the captioner stays on AMD compute.

## Quickstart

```bash
cd services/api
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

ruff check . && python -m pytest -q            # the gate
uvicorn app.main:app --reload --port 8000      # dev server
```

Configuration is environment-driven — see [.env.example](.env.example).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Liveness probe |
| `GET` | `/api/tasks` | List tasks from `tasks.json` |
| `POST` | `/api/tasks` | Submit task(s) — validates, dedupes styles, writes `tasks.json` |
| `POST` | `/api/tasks/run` | Trigger a pipeline run (202; 409 if one is already running) |
| `GET` | `/api/tasks/run` | Poll run status (`idle`/`running`/`succeeded`/`failed`) |
| `GET` | `/api/results` | Read `results.json` (empty list until the pipeline has run) |
| `GET` | `/api/results/{task_id}` | Captions for one task (404 if unknown) |
| `GET` | `/api/media/{filename}` | Serve a file from `<DATA_DIR>/media` (traversal-safe) |
| `POST` | `/api/keys/validate` | Check a Fireworks API key against the upstream API |
| `POST` | `/api/search` | **501** — Track 3 Video-Oracle stub (contract pinned) |
| `POST` | `/api/qa` | **501** — Track 3 Video-Oracle stub (contract pinned) |

Task and result bodies mirror the captioner I/O contract
([docs/16-io-contract.md](../../docs/16-io-contract.md)): tasks are
`{task_id, video_url, styles[]}`; results are `{task_id, captions: {style: text}}`.
Unknown styles are dropped on submit (matching the pipeline's ingestion behavior); a task whose
styles are *all* unknown is rejected with 422.

## Docker

```bash
docker build -t omnicaption-api services/api
docker run --rm -p 8000:8000 -e CORS_ORIGINS=https://your-frontend.example omnicaption-api
```

The default `POST /api/tasks/run` command shells out to
`docker run --rm -v <input>:/input -v <output>:/output $CAPTIONER_IMAGE`; override it entirely with
`CAPTIONER_CMD` (e.g. to run the pipeline in-process on the same host during development).
