<!--
SYNC IMPACT REPORT
- Version: 1.0.0 (initial ratification)
- Ratified: 2026-07-08
- Principles: I Faithful & Grounded Captions · II Hard Runtime & Memory Budgets ·
  III Test-First Development · IV Phased Delivery via Independent User Stories ·
  V AMD Compute as a Requirement · VI Multi-AI Coordination via Shared State ·
  VII Branch-Only, Always-Green main
- Templates propagated: .specify/templates/{spec,plan,tasks,checklist,constitution}-template.md
- Downstream sync: AGENTS.md §6/§8, specs/constitution.md (human seed), specs/001-*/plan.md Constitution Check
-->

# OmniCaption Constitution

**Version 1.0.0 · Ratified 2026-07-08**

Mission: win **Track 2** of the AMD Developer Hackathon (ACT II) by producing the most
visually-faithful, tonally-accurate stylistic video captions per clip, on AMD compute, inside the
harness's hard time and memory budgets — and lay the groundwork for the **Track 3 "Video-Oracle"**
stretch. These principles are non-negotiable. When in doubt, the constitution wins over convenience.

---

## Principle I — Faithful & Grounded Captions (non-negotiable)

Every caption describes only what the **audio transcript and the extracted keyframes actually
support**. No invented people, dialogue, places, or events. The humorous and sarcastic styles may
be creative in *tone*, but the *facts they riff on must be real*.

- **Rationale:** the evaluation scores visual **Accuracy** (0–1) alongside Style Match; a witty but
  fabricated caption loses the accuracy half of the score and misrepresents the clip.
- **Enforcement:** grounding is reviewed on the golden clips (v1/v2/v3); synthesis prompts instruct
  the model to caption observed content only; hallucinated specifics are treated as bugs.

## Principle II — Hard Runtime & Memory Budgets

The container operates inside fixed limits and **must not exceed them**: ≤10 min total runtime,
<30 s per request, ≤10 GB image, <60 s cold start. Whisper and the VLM are **never resident in VRAM
at the same time** — the pipeline loads a model, uses it, evicts it (`del` + `gc.collect()` +
`torch.cuda.empty_cache()`), then loads the next.

- **Rationale:** exceeding a budget disqualifies or fails the run; simultaneous model residency OOMs
  on 8–16 GB cards.
- **Enforcement:** sequential-loading memory reclamation between stages; latency-budget tests;
  image-size checks in CI/deployment.

## Principle III — Test-First Development

For every user story, tests are written **first** and must fail before implementation begins. This
includes the JSON I/O contract tests, keyframe-extraction tests, and the schema-validity of
`/output/results.json`.

- **Rationale:** the harness is unforgiving about output shape; a contract test catches a malformed
  results file before the leaderboard does.
- **Enforcement:** the pre-push hook and CI run the suite; a phase's "Tests FIRST" block precedes its
  "Implementation" block in [tasks](../../specs/001-omnicaption-captioning/tasks.md).

## Principle IV — Phased Delivery via Independent User Stories

Work is decomposed into user stories (US1…US7) that deliver value independently and land in phases.
The **MVP is US1–US6** (a working, schema-valid, styled captioner); Track 3 (US7) is a clearly
separated stretch.

- **Rationale:** an always-shippable slice beats a half-finished monolith when the deadline is fixed.
- **Enforcement:** each phase ends with a **Checkpoint**; MVP-first ordering is explicit in tasks.md.

## Principle V — AMD Compute as a Requirement

OmniCaption **must provably run on AMD compute** (ROCm / HIP). Absence of AMD-hardware usage is an
automatic disqualification in Track 2/3, so ROCm device usage is verified and logged at runtime.

- **Rationale:** it is a competition gate, not an optimization.
- **Enforcement:** `gpu.py` detects and logs the `gfx` arch and device; CTranslate2-HIP and
  PyTorch-ROCm are the required runtimes; a CPU-only fallback is for local dev only and is flagged.

## Principle VI — Multi-AI Coordination via Shared State

IBM Bob is the system of record and owns Spec-Kit `implement`. Claude (Tumo) and Gemini (Katlego)
assist in parallel. Coordination happens **only** through three files:
[AGENTS.md](../../AGENTS.md), [STATUS.md](../../STATUS.md), and
[specs/tasks.md](../../specs/tasks.md). One writer per task.

- **Rationale:** three agents editing one repo collide without a single shared brain.
- **Enforcement:** lane claims in STATUS.md; single-writer-per-task; read-before-write; see
  [docs/10-cross-ai-protocol.md](../../docs/10-cross-ai-protocol.md).

## Principle VII — Branch-Only, Always-Green main

Nobody pushes to `main`. All work lands via PR with a green gate. `main` is always deployable.

- **Rationale:** a red `main` blocks the whole team on a fixed timeline.
- **Enforcement:** [.githooks/pre-push](../../.githooks/pre-push) rejects direct pushes and runs the
  test gate; [CI](../../.github/workflows/ci.yml) re-runs it on every PR.

---

## Technology Constraints (locked stack)

Python 3.11 · Docker (linux/amd64) · faster-whisper on CTranslate2-HIP (ROCm) · ffmpeg ·
OpenCV keyframe extraction · Gemma 4 E4B-it (4-bit) via HF Transformers · PyTorch (ROCm) ·
pydantic-settings · pytest + Ruff (line length 100). Track 3 stretch: vLLM-ROCm + Gemma 4 31B +
CLIP/USM vector index. Swapping any locked component requires a plan amendment.

## Cost & Mocking Rules

- Unit tests **mock** Whisper and the VLM — no model downloads or GPU required to run the suite.
- Real inference runs against the 3 baseline clips before any submission run.
- No paid external APIs in the critical path; the container is self-contained and offline-capable
  once weights are baked into the image layer.

## Development Workflow

- **Definition of Done:** see [AGENTS.md §8](../../AGENTS.md).
- **Checkpoint every phase:** each user-story phase ends verifiable and independently demoable.
- Commit format `type(lane): T0xx description`; branch-only; PR into `main`.

## Governance

- This constitution supersedes convenience and habit. A conflict is resolved in its favor.
- **Amendments** are versioned semantically: **MAJOR** = a principle removed/redefined, **MINOR** =
  a principle or material section added, **PATCH** = clarification/wording. Update the Sync Impact
  Report and propagate to the templates + downstream docs.
- Amendments are proposed via PR and ratified by the team leader (Katlego), with Bob recording the
  change of record.
