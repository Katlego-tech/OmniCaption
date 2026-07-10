"""Auth endpoints are rate-limited per client IP."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _client(tmp_path, max_hits: int) -> TestClient:
    settings = Settings(
        data_dir=tmp_path,
        rate_limit_max=max_hits,
        ssrf_resolve_dns=False,
        _env_file=None,
    )
    return TestClient(create_app(settings))


def test_login_is_rate_limited(tmp_path) -> None:
    client = _client(tmp_path, max_hits=3)
    creds = {"email": "x@example.com", "password": "password-123"}
    # First 3 attempts pass the limiter (they 401 on bad creds); the 4th is 429.
    codes = [client.post("/api/auth/login", json=creds).status_code for _ in range(4)]
    assert codes[:3] == [401, 401, 401]
    assert codes[3] == 429


def test_signup_is_rate_limited(tmp_path) -> None:
    client = _client(tmp_path, max_hits=2)
    for i in range(2):
        client.post("/api/auth/signup", json={"email": f"u{i}@e.com", "password": "password-123"})
    resp = client.post("/api/auth/signup", json={"email": "u9@e.com", "password": "password-123"})
    assert resp.status_code == 429
