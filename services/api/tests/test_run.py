"""POST /api/tasks/run — trigger the captioner pipeline (subprocess, non-blocking)."""

from __future__ import annotations

import sys
import time

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _wait_for_terminal_state(client: TestClient, timeout_s: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        status = client.get("/api/tasks/run").json()
        if status["state"] in ("succeeded", "failed"):
            return status
        time.sleep(0.05)
    raise AssertionError(f"run never finished: {status}")


def test_run_status_starts_idle(client: TestClient) -> None:
    resp = client.get("/api/tasks/run")
    assert resp.status_code == 200
    assert resp.json()["state"] == "idle"


def test_run_triggers_and_succeeds(client: TestClient) -> None:
    resp = client.post("/api/tasks/run")
    assert resp.status_code == 202
    status = _wait_for_terminal_state(client)
    assert status["state"] == "succeeded"
    assert status["returncode"] == 0


def test_failing_command_reports_failed(tmp_path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        captioner_cmd=f'"{sys.executable}" -c "raise SystemExit(3)"',
        _env_file=None,
    )
    client = TestClient(create_app(settings))
    assert client.post("/api/tasks/run").status_code == 202
    status = _wait_for_terminal_state(client)
    assert status["state"] == "failed"
    assert status["returncode"] == 3


def test_concurrent_run_is_rejected(tmp_path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        captioner_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
        _env_file=None,
    )
    client = TestClient(create_app(settings))
    assert client.post("/api/tasks/run").status_code == 202
    assert client.post("/api/tasks/run").status_code == 409
