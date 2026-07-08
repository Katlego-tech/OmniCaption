# 04 — Testing Strategy

## Always-green main

`main` is always green. Nothing merges that is not covered by a passing test gate. Work happens on
branches and lands via PR (see [08-git-workflow](08-git-workflow.md)). If `main` ever goes red, fixing
it is the team's top priority over any feature work.

## The test gate (pre-push + CI)

Two enforcement points, same command:

- **Pre-push hook** (`.githooks/pre-push`, wired via `git config core.hooksPath .githooks`) runs Ruff
  + pytest locally before a push leaves your machine.
- **CI** re-runs the same suite on the PR. Both must be green to merge.

Keep the gate fast enough that people actually run it — mock the heavy models (below) so unit runs
finish in seconds.

## Test layers

### Schema / contract tests

The most important tests. `/output/results.json` must be valid or the run scores 0.

- Assert output is valid against the results schema: every task present, every requested style
  present, correct types.
- Assert the missing-style rule: if a style fails internally, the fallback caption is still emitted
  (never an absent key).
- Assert `tasks.json` parsing tolerates the real input shape (`{task_id, video_url, styles[]}`).

### Golden-clip regression tests

Three baseline clips lock behavior across changes:

- **v1 boulevard** (urban/motion)
- **v2 kitten** (animals)
- **v3 office worker** (human actions / indoor)

Each golden test runs the pipeline (or a mocked-model variant) and compares structure + key
properties of the captions, catching regressions in keyframe selection, alignment, and style routing.

### Latency budget tests

Guard the hard constraints from [06-judging-criteria](06-judging-criteria.md):

- Per-request generation stays **<30 s**.
- Full baseline batch stays **≤10 min**.
- Cold start (import + first model load path) stays within the **60 s** startup gate.

### Mocking the VLM / Whisper in unit tests

Unit tests must not download or run multi-GB models. Inject fakes:

- Mock faster-whisper to return a canned word-level transcript.
- Mock Gemma 4 E4B to return deterministic per-style strings.

This keeps unit tests cheap, hermetic, and CI-friendly. Reserve real-model runs for a small,
opt-in integration lane that runs on ROCm hardware, not on every push.
