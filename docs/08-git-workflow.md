# 08 — Git Workflow

Mirrors the FrameFlow discipline: **`main` is always green** and all work flows through branches and
PRs. No direct commits to `main`.

## Branch-only workflow

- Never commit directly to `main`. Branch, push, open a PR.
- One lane per branch. Keep branches short-lived and rebased on fresh `main`.

## Branch naming

| Prefix | Use |
| --- | --- |
| `feat/<lane>` | New feature work (e.g. `feat/audio`, `feat/vision`) |
| `fix/<thing>` | Bug fixes (e.g. `fix/vram-oom`) |
| `docs/<thing>` | Documentation (e.g. `docs/pipeline`) |

## Hooks

Wire the shared hooks once after cloning:

```bash
git config core.hooksPath .githooks
```

The **pre-push** hook runs Ruff + pytest (the same gate as CI — see
[04-testing-strategy](04-testing-strategy.md)). A push with a failing gate is blocked before it
leaves your machine.

## Commit format

```
<type>(<scope>): <TASK-ID> <summary>
```

Example:

```
feat(audio): T012 faster-whisper HIP transcription
```

- `<type>` — `feat`, `fix`, `docs`, etc.
- `<scope>` — the pipeline lane (`audio`, `vision`, `synthesis`, `output`, ...).
- `<TASK-ID>` — the id from `specs/tasks.md` (e.g. `T012`), tying the commit to the task list.

## PR flow

1. Branch from fresh `main`.
2. Commit with the format above; keep the branch focused on one lane.
3. Push (pre-push gate runs); open a PR into `main`.
4. CI re-runs the gate. Both green ⇒ mergeable.
5. Merge into `main`; `main` stays green.

## Emergency bypass

Only when genuinely necessary (e.g. hooks themselves are broken):

```bash
git push --no-verify
```

`--no-verify` skips the pre-push hook. Use sparingly, announce it in `STATUS.md`, and follow up
immediately to restore green — CI still gates the PR regardless.
