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
| `POST` | `/api/auth/signup` | Create an account → `{email, token}` (409 on duplicate) |
| `POST` | `/api/auth/login` | Authenticate → `{email, token}` (401 on bad credentials) |
| `GET` | `/api/auth/me` | Identity for the `Authorization: Bearer <token>` header (401 otherwise) |
| `GET` | `/api/tasks` | List tasks from `tasks.json` |
| `POST` | `/api/tasks` | Submit task(s) — validates, dedupes styles, writes `tasks.json` |
| `DELETE` | `/api/tasks` | Clear the whole manifest (204) |
| `DELETE` | `/api/tasks/{task_id}` | Remove one queued task (204; 404 if unknown) |
| `POST` | `/api/tasks/run` | Trigger a pipeline run (202; 409 if one is already running) |
| `GET` | `/api/tasks/run` | Poll run status (`idle`/`running`/`succeeded`/`failed`) |
| `GET` | `/api/results` | Read `results.json` (empty list until the pipeline has run) |
| `GET` | `/api/results/{task_id}` | Captions for one task (404 if unknown) |
| `DELETE` | `/api/results` | Delete all generated captions (204) |
| `DELETE` | `/api/results/{task_id}` | Delete one clip's captions (204; 404 if unknown) |
| `GET` | `/api/media/{filename}` | Serve a file from `<DATA_DIR>/media` (traversal-safe) |
| `POST` | `/api/keys/validate` | Check a Fireworks API key against the upstream API |
| `POST` | `/api/search` | Semantic moment search (501 until the oracle index is built) |
| `POST` | `/api/qa` | Grounded RAG QA (501 until the oracle index is built) |

Auth tokens are HMAC-signed (stdlib) and carry an expiry + a revocable version; accounts live in a
SQLite file at `<DATA_DIR>/auth.db` with PBKDF2-hashed passwords. Leave `AUTH_SECRET` unset to
auto-generate a persisted random key (single instance), or set it explicitly for multi-instance.
Auth endpoints are rate-limited per client IP — per-process by default, or shared across instances
via `REDIS_URL` (needs the optional `redis` package; degrades to in-memory if unreachable).

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
