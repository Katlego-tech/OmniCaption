"""Security hardening: secret handling, SSRF/URL validation, task_id charset."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.core.auth import AuthError, AuthService
from app.core.config import Settings

BASE_TASK = {"task_id": "v1", "styles": ["formal"]}


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _forge(secret: str, payload: dict) -> str:
    pb = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64url(hmac.new(secret.encode(), pb.encode(), hashlib.sha256).digest())
    return f"{pb}.{sig}"


# --- secret handling (Critical #1) ------------------------------------------
def test_token_forged_with_old_public_default_is_rejected(tmp_path) -> None:
    svc = AuthService(Settings(data_dir=tmp_path, auth_secret="", _env_file=None))
    forged = _forge(
        "dev-insecure-change-me", {"uid": 1, "email": "x@x.com", "exp": time.time() + 9999}
    )
    with pytest.raises(AuthError):
        svc.verify_token(forged)


def test_generated_secret_persists_across_restart(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path, auth_secret="", _env_file=None)
    token = AuthService(settings).issue_token(1, "x@x.com")
    # A second service over the same data dir must accept the token (same key).
    assert AuthService(settings).verify_token(token)["email"] == "x@x.com"


def test_explicit_secret_isolates_signers(tmp_path) -> None:
    token = AuthService(
        Settings(data_dir=tmp_path / "a", auth_secret="secret-A", _env_file=None)
    ).issue_token(1, "x@x.com")
    with pytest.raises(AuthError):
        AuthService(
            Settings(data_dir=tmp_path / "b", auth_secret="secret-B", _env_file=None)
        ).verify_token(token)


# --- SSRF / URL validation (High #3) ----------------------------------------
@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://localhost:8000/x",
        "http://127.0.0.1/x",
        "http://10.0.0.5/x",
        "http://192.168.1.1/x",
        "http://[::1]/x",
        "file:///etc/passwd",
        "ftp://example.com/x",
        "not-a-url",
    ],
)
def test_ssrf_and_non_http_urls_are_rejected(auth_client: TestClient, url: str) -> None:
    resp = auth_client.post("/api/tasks", json=[{**BASE_TASK, "video_url": url}])
    assert resp.status_code == 422


def test_public_https_url_is_accepted(auth_client: TestClient) -> None:
    resp = auth_client.post(
        "/api/tasks", json=[{**BASE_TASK, "video_url": "https://example.com/clip.mp4"}]
    )
    assert resp.status_code == 201


# --- task_id charset (Medium #8) --------------------------------------------
@pytest.mark.parametrize("task_id", ["../etc", "a/b", "a b", "a;b", "..", "a$(x)"])
def test_dangerous_task_ids_are_rejected(auth_client: TestClient, task_id: str) -> None:
    resp = auth_client.post(
        "/api/tasks",
        json=[{"task_id": task_id, "video_url": "https://example.com/c.mp4", "styles": ["formal"]}],
    )
    assert resp.status_code == 422
