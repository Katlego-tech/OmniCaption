"""httpOnly session cookie auth + DNS-resolution SSRF guard."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.routers import tasks as tasks_router

CREDS = {"email": "cookie@example.com", "password": "password-123"}
TASK = {"task_id": "v1", "video_url": "https://example.com/a.mp4", "styles": ["formal"]}


def test_login_sets_httponly_cookie_and_me_works_via_cookie(client: TestClient) -> None:
    resp = client.post("/api/auth/signup", json=CREDS)
    assert resp.status_code == 201
    # The session cookie was set (TestClient persists it in its jar).
    assert "session" in client.cookies

    # /me with no Authorization header resolves identity from the cookie alone.
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == CREDS["email"]


def test_dns_resolution_blocks_internal_hosts(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A hostname that (per our resolver) maps to an internal IP is rejected even
    # though it is not a literal private IP — DNS-rebinding mitigation.
    monkeypatch.setattr(
        tasks_router, "resolve_host_is_internal", lambda host: host == "sneaky.example"
    )

    settings = Settings(data_dir=tmp_path, ssrf_resolve_dns=True, _env_file=None)
    client = TestClient(create_app(settings))
    token = client.post("/api/auth/signup", json=CREDS).json()["token"]
    auth = {"Authorization": f"Bearer {token}"}

    bad = {**TASK, "video_url": "https://sneaky.example/clip.mp4"}
    assert client.post("/api/tasks", json=[bad], headers=auth).status_code == 422

    good = {**TASK, "video_url": "https://public.example/clip.mp4"}
    assert client.post("/api/tasks", json=[good], headers=auth).status_code == 201
