# Quickstart: OmniCaption

**Feature branch:** `001-omnicaption-captioning`
**Plan:** [plan.md](plan.md) · **Contracts:** [contracts/io-schemas.md](contracts/io-schemas.md)

Get OmniCaption cloned, built, and producing a `results.json` from the sample tasks, then run the
test suite. Commands assume an **AMD ROCm** host for the full GPU run; the mocked test suite runs on
CPU.

---

## Prerequisites

- Docker with `linux/amd64` build support.
- An AMD GPU with ROCm drivers for the real end-to-end run (a supported gfx target; see
  [docs/05-amd-rocm-optimization](../../docs/05-amd-rocm-optimization.md)). The mocked tests do **not**
  need a GPU.
- Python 3.11 + `git` for local test/lint runs.

---

## 1. Clone

```bash
git clone https://github.com/Katlego-tech/OmniCaption.git
cd OmniCaption
```

## 2. Enable the shared git hooks

The pre-push hook runs Ruff + the fast test suite so `main` stays green (constitution VII).

```bash
git config core.hooksPath .githooks
```

## 3. Build the container (linux/amd64)

```bash
cd services/captioner
docker build --platform linux/amd64 -t omnicaption:dev .
```

The build is multi-stage and must produce a **≤10 GB** image. Verify:

```bash
docker image inspect omnicaption:dev --format '{{.Size}}' | awk '{printf "%.2f GB\n", $1/1e9}'
```

## 4. Run against the sample tasks

The pipeline reads `/input/tasks.json` and writes `/output/results.json`. Mount the sample fixture as
input and a local `out/` directory as output.

```bash
mkdir -p out
docker run --rm \
  --device=/dev/kfd --device=/dev/dri \
  --group-add video \
  -v "$PWD/tests/fixtures/tasks.sample.json:/input/tasks.json:ro" \
  -v "$PWD/out:/output" \
  omnicaption:dev
```

The container should log the active **AMD device**, run the 6-stage pipeline per task, write
`/output/results.json`, and **exit 0**. Startup must be <60 s and the whole batch ≤10 min.

> On a non-AMD dev box you can set `OMNICAPTION_ENFORCE_AMD=0` to allow a CPU fallback for a smoke run
> (this is dev-only; a real submission must run on AMD compute — constitution V).

## 5. Inspect the results

```bash
cat out/results.json
```

You should see a `results` array with one entry per task and a caption for every requested style, e.g.

```json
{
  "results": [
    { "task_id": "v1", "captions": { "formal": "A wide waterfall cascades over dark rock..." } }
  ]
}
```

Validate it against the output schema:

```bash
python -m jsonschema -i out/results.json tests/fixtures/schemas/results.schema.json
```

Every requested style must be present — a missing style scores 0 (see
[contracts/io-schemas.md](contracts/io-schemas.md)).

## 6. Run the tests

Create a venv and install dev deps, then run pytest (models are mocked, so no GPU needed):

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

ruff check .
ruff format --check .
pytest                       # unit + contract + integration (mocked models)
pytest -m contract           # just the JSON I/O contract tests
pytest -m integration        # full-pipeline smoke (mocked)
```

The GPU-gated latency and AMD-compute tests run in CI on the ROCm lane; to run them locally on an AMD
host:

```bash
pytest -m "integration" --run-gpu
```

---

## Troubleshooting

- **No AMD device detected** → the container refuses to run in enforced mode. Confirm `/dev/kfd` and
  `/dev/dri` are passed and the `video` group is added. See
  [docs/05-amd-rocm-optimization](../../docs/05-amd-rocm-optimization.md).
- **Image over 10 GB** → prune build caches / model staging in the Dockerfile's final stage (task
  T083 in [tasks.md](tasks.md)).
- **A style is missing from output** → that `(clip, style)` scores 0. The pipeline should have emitted
  a deterministic fallback; check logs for the failed style and the fallback path.
- **Startup over 60 s** → ensure model weights are staged/cached in the image and heavy imports are
  lazy (task T082).
