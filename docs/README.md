# OmniCaption Documentation

OmniCaption is a submission for the **AMD Developer Hackathon (ACT II)**, primarily targeting
**Track 2: Stylistic Video Captioning Agent**. It is a Dockerized (linux/amd64) dual-model hybrid
captioning pipeline that reads `/input/tasks.json`, generates styled captions per clip, and writes
`/output/results.json`.

## Document index

| Doc | Description |
| --- | --- |
| [00-project-plan](00-project-plan.md) | Master plan: mission, tracks, phased timeline, scope, cut order |
| [01-architecture](01-architecture.md) | Container I/O contract, 6-stage pipeline diagram, VRAM budgeting |
| [02-tech-stack](02-tech-stack.md) | The locked stack as a component/choice/why table |
| [03-captioning-pipeline](03-captioning-pipeline.md) | Deep dive on the 6 stages, keyframes, modality ordering |
| [04-testing-strategy](04-testing-strategy.md) | Always-green main, test gate, contract + golden-clip tests |
| [05-amd-rocm-optimization](05-amd-rocm-optimization.md) | CTranslate2-HIP build, gfx targets, MI300X/vLLM tunables |
| [06-judging-criteria](06-judging-criteria.md) | Track 2 scoring, runtime constraints, submission checklist |
| [07-planning-workflow](07-planning-workflow.md) | How we plan: SPEC.md + PLAN.md + TASKS.md + STATUS.md |
| [08-git-workflow](08-git-workflow.md) | Branch-only workflow, hooks, commit format, PR flow |
| [09-research-summary](09-research-summary.md) | Condensed hackathon research summary |
| [10-cross-ai-protocol](10-cross-ai-protocol.md) | How Claude + Gemini coordinate without collisions |
| [11-phase0-runbook](11-phase0-runbook.md) | Concrete "start here" runbook + learning checklist |
| [12-project-structure](12-project-structure.md) | Repo layout and how to run each part |
| [13-prompt-engineering-playbook](13-prompt-engineering-playbook.md) | The four style system prompts + PMP chain |
| [14-optimization-suggestions](14-optimization-suggestions.md) | Forward-looking improvement proposals |
| [15-data-model](15-data-model.md) | Entities, fields, validation, and the exact JSON shapes |
| [16-io-contract](16-io-contract.md) | Authoritative `/input` & `/output` JSON schemas |
| [17-pipeline-stages](17-pipeline-stages.md) | The 6-stage interface contract + VRAM handoff + fallbacks |
| [18-frontend-architecture](18-frontend-architecture.md) | Technical specs and design systems for Next.js web application |
| [19-notebook-environment](19-notebook-environment.md) | Notebook implementation and testing plan for ROCm 7.2 + vLLM |
| [report-scoreboard-pivot](report-scoreboard-pivot.md) | Strategy report to recover Track 2 style quality from 93rd place |
| [submission-amd-proof](submission-amd-proof.md) | Official AMD/ROCm hardware acceleration proof and logs |
| [submission-descriptions](submission-descriptions.md) | Pitch descriptions, categories, and technology tags |
| [deployment](deployment.md) | Build/tag/push linux/amd64 image + local smoke test |

The top-level planning documents — [SPEC.md](../SPEC.md), [PLAN.md](../PLAN.md), [TASKS.md](../TASKS.md) —
live in the repo root.

## Read these first, in order

1. [00-project-plan](00-project-plan.md) — what we are building and why.
2. [01-architecture](01-architecture.md) — the shape of the system.
3. [03-captioning-pipeline](03-captioning-pipeline.md) — the heart of the project.
4. [11-phase0-runbook](11-phase0-runbook.md) — get your environment running.
5. [08-git-workflow](08-git-workflow.md) and [10-cross-ai-protocol](10-cross-ai-protocol.md) — how we work together without stepping on each other.
