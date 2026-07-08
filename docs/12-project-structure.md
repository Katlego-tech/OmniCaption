# 12 — Project Structure

## Repo layout

```
OmniCaption/
├── README.md                 # overview + quick start
├── AGENTS.md                 # rules every contributor follows (shared state)
├── STATUS.md                 # live board: who is doing what (shared state)
├── CLAUDE.md · GEMINI.md     # per-assistant entry points (Tumo / Katlego)
├── SPEC.md                   # the WHAT — user stories + acceptance criteria
├── PLAN.md                   # the HOW — stack, non-negotiables, layout, phases
├── TASKS.md                  # the checkbox task list (task ids like T012)
├── Hackathon Research for AI Video Captioning.pdf   # source research
├── docs/                     # this planning documentation set (00–17 + deployment)
├── .githooks/                # pre-push test gate (wired via core.hooksPath)
├── .github/workflows/ci.yml  # CI test gate
├── services/
│   └── captioner/            # the Python pipeline (the product)
│       ├── app/
│       │   ├── main.py       # entry point: runs the 6 stages, exits 0
│       │   ├── core/         # config.py · schema.py · gpu.py · logging.py
│       │   ├── pipeline/     # ingestion · audio · memory · vision · synthesis · output
│       │   ├── prompts/      # styles.py (4 styles) · pmp.py (sarcasm chain)
│       │   └── models/       # loader.py (Whisper + Gemma)
│       ├── tests/            # unit · integration · contract · fixtures
│       └── Dockerfile        # linux/amd64 build
└── apps/
    └── web/                  # OPTIONAL Track-3 "Video-Oracle" demo UI
```

How we plan with the SPEC/PLAN/TASKS/STATUS documents is in
[07-planning-workflow](07-planning-workflow.md); coordination between assistants is in
[10-cross-ai-protocol](10-cross-ai-protocol.md).

## How to run each part

### The captioner pipeline (Track 2)

```bash
docker run --rm -v ./input:/input -v ./output:/output <image>
```

Runs `services/captioner/app/main.py` through the six stages and writes `/output/results.json`. Local
build and smoke-test details are in [deployment](deployment.md).

### Tests

```bash
cd services/captioner
python -m pytest -q      # unit + contract + integration (models mocked)
ruff check .             # lint, line length 100
```

See [04-testing-strategy](04-testing-strategy.md).

### The web demo (Track 3, optional)

`apps/web/` hosts the "Video-Oracle" semantic-search demo. It is a stretch deliverable and the first
thing cut under time pressure ([00-project-plan](00-project-plan.md)); run it only when Track 2 is
green.
