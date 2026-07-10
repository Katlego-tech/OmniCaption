"""POST /api/tasks/run — trigger the captioner pipeline (subprocess, non-blocking).

Triggering a run is a mutation and requires a bearer token; polling status is open.
"""

from __future__ import annotations

import sys
import time

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

CREDS = {"email": "runner@example.com", "password": "password-123"}


def _authorize(client: TestClient) -> TestClient:
    token = client.post("/api/auth/signup", json=CREDS).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


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


def test_trigger_run_without_token_is_401(client: TestClient) -> None:
    assert client.post("/api/tasks/run").status_code == 401


def test_run_triggers_and_succeeds(auth_client: TestClient) -> None:
    resp = auth_client.post("/api/tasks/run")
    assert resp.status_code == 202
    status = _wait_for_terminal_state(auth_client)
    assert status["state"] == "succeeded"
    assert status["returncode"] == 0


def test_failing_command_reports_failed(tmp_path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        captioner_cmd=f'"{sys.executable}" -c "raise SystemExit(3)"',
        _env_file=None,
    )
    client = _authorize(TestClient(create_app(settings)))
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
    client = _authorize(TestClient(create_app(settings)))
    assert client.post("/api/tasks/run").status_code == 202
    assert client.post("/api/tasks/run").status_code == 409


def test_idle_status_omits_diagnostic_output(client: TestClient) -> None:
    body = client.get("/api/tasks/run").json()
    assert body["state"] == "idle"
    assert "stdout" not in body and "stderr" not in body


def test_succeeded_status_captures_stdout(tmp_path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        captioner_cmd=f'"{sys.executable}" -c "print(\'hello-out\')"',
        _env_file=None,
    )
    client = _authorize(TestClient(create_app(settings)))
    assert client.post("/api/tasks/run").status_code == 202
    status = _wait_for_terminal_state(client)
    assert status["state"] == "succeeded"
    assert "hello-out" in status["stdout"]


def test_failed_status_surfaces_stderr(tmp_path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        captioner_cmd=(
            f'"{sys.executable}" -c '
            "\"import sys; sys.stderr.write('boom-diagnostic'); sys.exit(2)\""
        ),
        _env_file=None,
    )
    client = _authorize(TestClient(create_app(settings)))
    assert client.post("/api/tasks/run").status_code == 202
    status = _wait_for_terminal_state(client)
    assert status["state"] == "failed"
    assert status["returncode"] == 2
    assert "boom-diagnostic" in status["stderr"]
