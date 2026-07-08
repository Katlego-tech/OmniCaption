# 10 — Cross-AI Protocol

Three assistants operate on one repo: **IBM Bob** (system of record, owns `implement`), **Claude**
(via [../CLAUDE.md](../CLAUDE.md)), and **Gemini** (via [../GEMINI.md](../GEMINI.md)). Katlego drives
Bob + Gemini; Tumo drives Bob + Claude. This protocol keeps them from colliding.

## Shared-state files (the coordination surface)

| File | Role |
| --- | --- |
| `AGENTS.md` | The rules every assistant must follow. Read first, every session. |
| `STATUS.md` | The live board: who is doing what, right now. Kept current. |
| `specs/tasks.md` | The checkbox task list (task ids like `T012`). The unit of work. |

## Core rules

### Single-writer-per-task

A task in `specs/tasks.md` has exactly **one owner at a time**. Before starting, claim it in
`STATUS.md` (your name + the task id). Two assistants must never edit the same task's files
concurrently. If a task is already claimed, pick another.

### Lane labels

Work is organized into **lanes** matching the pipeline (`audio`, `vision`, `synthesis`, `output`,
`docs`, `infra`). Branches use the lane (`feat/audio`) and commits carry the scope
(`feat(audio): T012 ...`). Lanes keep parallel work in disjoint file regions — see
[08-git-workflow](08-git-workflow.md).

### Read-before-write

Always **pull latest and read `STATUS.md` + `AGENTS.md` before touching anything.** State changes
between sessions and between assistants. Never write from a stale view of the board.

### Keep STATUS.md current

`STATUS.md` is only useful if it is true. Update it when you **claim**, **finish**, or **hand off** a
task, and when you hit a blocker. A finished task gets its checkbox ticked in `specs/tasks.md` and its
line cleared/updated in `STATUS.md`.

## Who owns what

- **Bob** is authoritative for `implement` and the Spec-Kit lifecycle
  ([07-ibm-bob-spec-kit](07-ibm-bob-spec-kit.md)). What Bob lands is canonical.
- **Claude / Gemini** draft, research, and prepare changes in their lanes, then land via PR into a
  green `main`. They defer to Bob on lifecycle and to the single-writer rule on tasks.

## Collision avoidance in one line

Pull → read `STATUS.md`/`AGENTS.md` → claim a task (single writer) → work in your lane branch →
update `STATUS.md` → PR into green `main`.
