# Requirements Quality Checklist: OmniCaption

**Feature branch:** `001-omnicaption-captioning`
**Reviews:** [../spec.md](../spec.md) · [../plan.md](../plan.md) · [../data-model.md](../data-model.md) · [../contracts/io-schemas.md](../contracts/io-schemas.md) · [../contracts/pipeline-stages.md](../contracts/pipeline-stages.md)

This checklist audits the **quality of the requirements** themselves (are they complete, testable,
measurable, unambiguous) before implementation begins. Check an item only when the reviewer can point
to the artifact text that satisfies it. All boxes start unchecked — this project is just starting.

---

## User stories are testable

- [ ] Every user story US1–US7 has explicit, numbered acceptance criteria.
- [ ] Each acceptance criterion is objectively verifiable (a test could pass/fail on it).
- [ ] Stories are independently deliverable and each maps to a phase + checkpoint in [../tasks.md](../tasks.md).
- [ ] The MVP boundary (US1–US6) vs stretch (US7) is unambiguous.
- [ ] Each story identifies the actor (harness / dev team / Track-3 user).
- [ ] Failure and degraded-input behavior is specified per story (empty audio, static clip, bad URL, VLM failure).

## Constraints are measurable

- [ ] Runtime budget is a concrete number (batch ≤10 min).
- [ ] Per-request budget is a concrete number (<30 s).
- [ ] Startup budget is a concrete number (<60 s).
- [ ] Image-size budget is a concrete number (≤10 GB).
- [ ] Memory constraint is concrete and testable (STT + VLM never co-resident; fits 8 GB-class card).
- [ ] Each budget has a corresponding assertion/test identified in [../tasks.md](../tasks.md) (latency, image-size, startup, sequential-VRAM).

## The JSON contract is fully specified

- [ ] Input `/input/tasks.json` shape is defined with a JSON Schema and a field table.
- [ ] Output `/output/results.json` shape is defined with a JSON Schema and a field table.
- [ ] The closed set of 4 style keys is stated and enforced in both schemas.
- [ ] Behavior for unknown style strings is defined (dropped, not fatal).
- [ ] Behavior for malformed input is defined (structural = fail fast; unknown style = lenient).
- [ ] The missing-style-scores-0 rule is stated and drives the always-emit-fallback requirement.
- [ ] Output validation-before-write and repair-to-valid behavior is specified.
- [ ] The exit-code-0 guarantee is stated and tied to a test.

## AMD compute usage is provable

- [ ] AMD/ROCm compute is stated as a mandatory, disqualifying requirement.
- [ ] Both model stages (STT + VLM) are required to run on AMD compute.
- [ ] A device-detection/assertion mechanism is specified (fails loudly in enforced mode).
- [ ] A concrete proof artifact is planned (device logs + `rocm-smi` capture) for judging.
- [ ] A dev-only CPU fallback flag is documented and clearly excluded from a real submission.

## Grounding & faithfulness are specified

- [ ] Captions are required to be grounded in transcript + keyframes only (no hallucination).
- [ ] Style is defined as a tone transform over true content, never fabricated content.
- [ ] A per-style grounding guard is planned.
- [ ] The deterministic fallback caption is derived from real evidence.

## Data model is complete & consistent

- [ ] Every entity (Task, StyleCaption, ClipResult, ResultsOutput, Transcript/Segment/Word, Keyframe, CaptionState) has fields, types, and validation rules.
- [ ] `CaptionState` fields match between [../plan.md](../plan.md) and [../data-model.md](../data-model.md).
- [ ] Input/output example JSON matches the schemas in [../contracts/io-schemas.md](../contracts/io-schemas.md).
- [ ] Empty-but-valid transcript and ≥1-keyframe guarantees are stated.
- [ ] Timestamp monotonicity/non-negativity rules are stated.

## Pipeline contract is complete

- [ ] All 6 stages have defined inputs, outputs, and error behavior.
- [ ] The VRAM handoff protocol (Audio → Reclamation → Vision/Synthesis) is specified as a hard barrier.
- [ ] The locked modality order (images → transcript → style prompt) is stated.
- [ ] The PMP chain for sarcasm is described.
- [ ] Per-stage error/fallback paths all preserve the two hard guarantees (every style emitted, exit 0).

## Process & governance

- [ ] All 7 constitution principles are checked in [../plan.md](../plan.md) (pre- and post-design).
- [ ] Test-first ordering is enforced in every user-story phase.
- [ ] Branch-only / always-green main and the pre-push + CI gate are specified.
- [ ] Multi-AI coordination via `STATUS.md` / `AGENTS.md` / tasks.md is specified.
- [ ] Commit format `feat(scope): Tnnn ...` is stated.
- [ ] The cut order under time pressure is documented and never sacrifices the non-negotiables.

## Ambiguity & completeness sweep

- [ ] No requirement uses vague terms ("fast", "good") without a measurable definition.
- [ ] No `NEEDS CLARIFICATION` markers remain unresolved for MVP scope.
- [ ] Open assumptions are listed and confirmed non-blocking for the MVP.
- [ ] Cross-links between sibling artifacts resolve and are consistent.
- [ ] Success metric Φ (α·A + β·M over ~12 clips × styles) is stated and matches the missing-style rule.
