# 06 — Judging Criteria

## Track 2 scoring

Each clip is scored **per style** on two axes, each in `[0, 1]`:

- **Accuracy A(v, s)** — visual fidelity: does the caption match what is actually on screen?
- **Style Match M(v, s)** — tone alignment: does it read like the requested style?

The final score aggregates over all clips `V` and all styles `S`:

```
        1
Φ  =  ───────  ·  Σ_v  Σ_s  ( α·A(v,s)  +  β·M(v,s) )
      |V|·|S|
```

where `α` and `β` weight accuracy vs. style. Evaluation runs over **~12 hidden clips** across diverse
domains: nature, urban, animals, human actions, sports, food, weather, technology. Design for
generality, not for the three baseline clips.

**A missing style scores 0.** Always emit a caption for every requested style — fall back to the
deterministic caption rather than omitting a key (see [03-captioning-pipeline](03-captioning-pipeline.md)).

## Runtime constraints (hard gates)

| Constraint | Limit |
| --- | --- |
| Total container runtime | **≤ 10 min** |
| Per-request response | **< 30 s** |
| Container image size | **≤ 10 GB** |
| Container startup | **within 60 s** |
| AMD compute usage | **Required** — absent ⇒ disqualified |
| Exit code | **0** |

These are enforced in tests — see [04-testing-strategy](04-testing-strategy.md).

## Submission checklist

- [ ] Docker image published to a **public registry** (Docker Hub or GHCR).
- [ ] Image manifest is **linux/amd64**.
- [ ] **AMD compute proof** — logs / evidence the run used ROCm/HIP (not CPU fallback).
- [ ] `/output/results.json` is **schema-valid**: every task, every requested style present.
- [ ] Container **starts within 60 s** and **finishes ≤10 min** on the baseline batch.
- [ ] Per-request latency **< 30 s**.
- [ ] Image is **≤ 10 GB**.
- [ ] Process **exits 0** on success.
- [ ] All four styles (`formal`, `sarcastic`, `humorous_tech`, `humorous_non_tech`) produce distinct,
      on-tone captions.
- [ ] `main` is green; PRs merged; docs current.

See [deployment](deployment.md) for build/push mechanics and [11-phase0-runbook](11-phase0-runbook.md)
for the local verification run.
