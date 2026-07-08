# AGENTS.md — the OmniCaption contract

This is the single contract every contributor follows — **human or AI, Bob, Claude, or Gemini**.
Read it before you touch anything. If a rule here conflicts with a habit, the rule wins.

Entry points funnel here: [CLAUDE.md](CLAUDE.md) (Tumo) and [GEMINI.md](GEMINI.md) (Katlego) both
say "read AGENTS.md first." This file is the source of truth for *how we work*; the
[constitution](.specify/memory/constitution.md) is the source of truth for *what is non-negotiable*.

---

## 1. Team & lanes

| Person | Role | AI copilots |
|--------|------|-------------|
| **Katlego** | Team leader, repo owner (`Katlego-tech/OmniCaption`) | IBM Bob + Gemini |
| **Tumo** | Co-builder | IBM Bob + Claude |

Both are full-stack on this project. We do **not** hard-partition file ownership; we coordinate with
**lane labels** in [STATUS.md](STATUS.md) (e.g. `audio`, `vision`, `synthesis`, `container`, `docs`).
Before working a lane, claim it in the STATUS.md "Current focus" table so two people don't collide.

## 2. Multi-AI workflow

- **IBM Bob is the system of record.** Bob drives the Spec-Kit lifecycle:
  `/speckit.constitution → /speckit.specify → /speckit.clarify → /speckit.plan → /speckit.tasks → /speckit.implement`.
- **Claude and Gemini run in parallel** as assistants — research, scaffolding, tests, review, docs,
  drafting spec/plan text. They do **not** own `implement`; Bob does.
- **Shared state lives in exactly three places:** [AGENTS.md](AGENTS.md) (rules),
  [STATUS.md](STATUS.md) (live board), [specs/tasks.md](specs/tasks.md) (the checkbox task list).
  Everything else is derived. If it isn't reflected in these three, it didn't happen.
- **Single writer per task.** One task ID (`T0xx`) is worked by one person at a time. Claim it in
  STATUS.md before you start; release it when the PR merges.

See [docs/10-cross-ai-protocol.md](docs/10-cross-ai-protocol.md) for the collision-avoidance detail.

## 3. `main` is always green

- **Branch-only.** Nobody pushes to `main`, ever. The pre-push hook rejects it.
- Enable the hooks once per clone: `git config core.hooksPath .githooks`.
- The [pre-push hook](.githooks/pre-push) runs the test gate locally; [CI](.github/workflows/ci.yml)
  re-runs it on every PR. A red `main` blocks the whole team, so we never let it happen.

## 4. Branch & commit flow

- Branch names: `feat/<lane>`, `fix/<thing>`, `docs/<thing>`, `chore/<thing>`.
  Examples: `feat/audio`, `fix/keyframe-threshold`, `docs/rocm`.
- Open a PR into `main`. The gate must be green. Get a quick review from the other builder.
- Commit format ties work back to a task ID:
  `feat(audio): T012 faster-whisper HIP transcription`
  `type(lane): T0xx short description`.

## 5. Update STATUS.md every step

After any meaningful step, update [STATUS.md](STATUS.md):
1. Tick / add the relevant checkbox and task ID.
2. Update the lane's **Status** column and the phase timeline.
3. Add a dated line to the **Log** at the bottom.

Format the header line as: `_Last updated: YYYY-MM-DD — by <name> (via Bob|Claude|Gemini)_`.

## 6. Grounding & honesty rules

- **Caption only what the evidence supports.** A caption describes what the transcript and the
  keyframes actually show. No invented people, places, dialogue, or events — even in the humorous
  styles, the *joke* can be creative but the *facts* it riffs on must be real. This is
  Principle I of the [constitution](.specify/memory/constitution.md).
- **Respect the budgets.** ≤10 min total runtime, <30 s per request, ≤10 GB image, <60 s startup,
  and the container **must provably use AMD compute** (absence = disqualification).
- **Deterministic I/O.** The output must always be schema-valid JSON at `/output/results.json`,
  even on partial failure — write a graceful fallback caption rather than crashing. Exit code 0.
- **Report failures honestly.** If a stage OOMs, a clip won't download, or a style comes out weak,
  say so in STATUS.md. Don't paper over a broken run.

## 7. Repository map

```
OmniCaption/
├── README.md · AGENTS.md · CLAUDE.md · GEMINI.md   shared-state entry points
├── STATUS.md · STATUS.template.md                  the live board + its template
├── docs/                     00–14 numbered planning docs + deployment.md
├── specs/                    human seeds (spec/plan/tasks/constitution) +
│   └── 001-omnicaption-captioning/   generated Spec-Kit artifacts
├── .specify/                 Spec-Kit engine (memory/constitution.md + templates/)
├── .claude/                  Claude permission allowlist
├── .github/workflows/ci.yml  the CI test gate
├── .githooks/pre-push        the local test gate + main-branch protection
├── services/captioner/       the Python captioning pipeline + Dockerfile + tests
└── apps/web/  (stretch)      Track 3 Video-Oracle demo
```

## 8. Definition of Done

A task is done when **all** of these hold:
- [ ] Code + tests written; tests were written **first** and now pass.
- [ ] `ruff` clean; the pipeline still imports; the sample task still produces schema-valid output.
- [ ] Runs inside the budgets (no new OOM, no blown latency).
- [ ] STATUS.md updated (checkbox + lane status + Log line); task ID referenced in the commit.
- [ ] PR opened into `main`, CI green, reviewed by the other builder, merged.

<!-- SPECKIT START -->
Active feature: [specs/001-omnicaption-captioning/plan.md](specs/001-omnicaption-captioning/plan.md)
<!-- SPECKIT END -->
