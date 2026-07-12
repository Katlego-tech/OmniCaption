"""Auto-build of the Track 3 oracle index after a successful run.

The runner-mechanism tests run everywhere; the actual index build is guarded
behind the oracle package (installed only in the API venv / CI), matching
test_oracle_live.py.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.runner import PipelineRunner

_NOOP_OK = [sys.executable, "-c", "print('ok')"]


def _wait(runner: PipelineRunner, timeout_s: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        st = runner.status()
        if st["state"] in ("succeeded", "failed"):
            return st
        time.sleep(0.02)
    raise AssertionError("run never finished")


# --- runner post_run mechanism (no oracle needed) ---------------------------


def test_post_run_hook_runs_on_success_and_reports_built() -> None:
    runner = PipelineRunner()
    ran: dict[str, bool] = {}
    runner.start(_NOOP_OK, post_run=lambda: ran.__setitem__("x", True))
    st = _wait(runner)
    assert st["state"] == "succeeded"
    assert ran.get("x") is True
    assert st.get("index") == "built"


def test_post_run_failure_does_not_fail_the_run() -> None:
    runner = PipelineRunner()

    def boom() -> None:
        raise RuntimeError("embed failed")

    runner.start(_NOOP_OK, post_run=boom)
    st = _wait(runner)
    assert st["state"] == "succeeded"  # captions are primary; index is best-effort
    assert st.get("index") == "failed"


def test_no_post_run_leaves_index_field_absent() -> None:
    runner = PipelineRunner()
    runner.start(_NOOP_OK)
    st = _wait(runner)
    assert st["state"] == "succeeded"
    assert "index" not in st


# --- actual index build (needs the oracle package) --------------------------


class _FakeEmbedder:
    """Deterministic embedder — no network."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)), 1.0, 0.0] for t in texts]


def test_build_index_from_run_writes_index(tmp_path: Path) -> None:
    pytest.importorskip("oracle.index", reason="oracle package not installed")
    from app.core.oracle_build import build_index_from_run

    settings = Settings(data_dir=tmp_path, _env_file=None)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.results_path.write_text(
        json.dumps([{"task_id": "v1", "captions": {"formal": "A cat sits.", "sarcastic": "Wow."}}]),
        encoding="utf-8",
    )

    n = build_index_from_run(settings, "unused-key", embedder=_FakeEmbedder())

    assert n == 2
    assert settings.oracle_index_path.is_file()
    saved = json.loads(settings.oracle_index_path.read_text(encoding="utf-8"))
    assert len(saved) == 2
    assert all("vector" in m for m in saved)
