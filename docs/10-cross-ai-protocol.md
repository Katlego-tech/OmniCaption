# 10 — Cross-AI Protocol

Two AI assistants operate on one repo: **Claude** (via [../CLAUDE.md](../CLAUDE.md), with Tumo) and
**Gemini** (via [../GEMINI.md](../GEMINI.md), with Katlego). This protocol keeps them from colliding.

## Shared-state files (the coordination surface)

| File | Role |
| --- | --- |
| [../AGENTS.md](../AGENTS.md) | The rules every assistant must follow. Read first, every session. |
| [../STATUS.md](../STATUS.md) | The live board: who is doing what, right now. Kept current. |
| [../TASKS.md](../TASKS.md) | The checkbox task list (task ids like `T012`). The unit of work. |

## Core rules

### Single-writer-per-task

A task in [../TASKS.md](../TASKS.md) has exactly **one owner at a time**. Before starting, claim it in
[../STATUS.md](../STATUS.md) (your name + the task id). Two assistants must never edit the same task's
files concurrently. If a task is already claimed, pick another.

### Lane labels

Work is organized into **lanes** matching the pipeline (`audio`, `vision`, `synthesis`, `output`,
`docs`, `infra`). Branches use the lane (`feat/audio`) and commits carry the scope
(`feat(audio): T012 ...`). Lanes keep parallel work in disjoint file regions — see
[08-git-workflow](08-git-workflow.md).

### Read-before-write

Always **pull latest and read STATUS.md + AGENTS.md before touching anything.** State changes between
sessions and between assistants. Never write from a stale view of the board.

### Keep STATUS.md current

STATUS.md is only useful if it is true. Update it when you **claim**, **finish**, or **hand off** a
task, and when you hit a blocker. A finished task gets its checkbox ticked in [../TASKS.md](../TASKS.md)
and its line cleared/updated in STATUS.md.

## Who ratifies changes

There is no automated "system of record." Changes to [../SPEC.md](../SPEC.md), [../PLAN.md](../PLAN.md),
and [../TASKS.md](../TASKS.md) land like any other change — via a PR reviewed by the other builder.
Katlego (team leader, repo owner) has the final call on scope and the project non-negotiables. See
[07-planning-workflow](07-planning-workflow.md).

## Collision avoidance in one line

Pull → read STATUS.md/AGENTS.md → claim a task (single writer) → work in your lane branch →
update STATUS.md → PR into green `main`.
