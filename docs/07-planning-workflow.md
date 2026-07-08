# 07 — Planning workflow

OmniCaption is planned with plain, self-driven documents — no external orchestrator, no Spec-Kit
tooling. Three living documents plus a live board are all we need.

## The planning documents

| Document | Role | Analogue |
|----------|------|----------|
| [SPEC.md](../SPEC.md) | **The WHAT** — user stories US1–US7, acceptance criteria, scoring. | the requirements |
| [PLAN.md](../PLAN.md) | **The HOW** — stack, non-negotiables, code layout, build phases, test gate. | the design |
| [TASKS.md](../TASKS.md) | **The task list** — dependency-ordered `T001…T102`, checkbox per task. | the backlog |
| [STATUS.md](../STATUS.md) | **The live board** — who owns what right now, timeline, log. | the standup |

Supporting detail lives in [docs/15-data-model.md](15-data-model.md),
[docs/16-io-contract.md](16-io-contract.md), and [docs/17-pipeline-stages.md](17-pipeline-stages.md).

## The loop

1. **Agree the WHAT.** Edit [SPEC.md](../SPEC.md) — user stories + acceptance criteria. Keep it
   implementation-agnostic.
2. **Design the HOW.** Edit [PLAN.md](../PLAN.md) — stack, module layout, phases. Check it against the
   seven **non-negotiables** listed there before building.
3. **Break it down.** Edit [TASKS.md](../TASKS.md) — one checkbox task per unit of work, each tagged
   with its user story and marked `[P]` if parallelizable.
4. **Claim & build.** Claim a task/lane in [STATUS.md](../STATUS.md), branch, write the test first,
   implement, open a PR. One writer per task.
5. **Land & update.** Merge via a green PR, tick the task in TASKS.md, update STATUS.md.

## Who ratifies changes

There is no automated "system of record." Changes to SPEC/PLAN/TASKS land like any other change — via
a PR reviewed by the other builder. Katlego (team leader, repo owner) has the final call on scope and
the non-negotiables; both builders keep the documents current.

## What changed from the original scaffold

This project was bootstrapped from a template that used IBM Bob + GitHub Spec-Kit. That apparatus has
been **removed**: the two-layer `specs/` tree and `.specify/` engine are gone, the constitution's
substance now lives as **Non-negotiables** in [PLAN.md](../PLAN.md), and planning is driven directly by
the team through the four documents above.
