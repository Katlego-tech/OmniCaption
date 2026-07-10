"""Email verification flow + signup anti-enumeration (verification-required mode)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

CREDS = {"email": "verify@example.com", "password": "password-123"}


def _client(tmp_path: Path) -> tuple[TestClient, Settings]:
    settings = Settings(
        data_dir=tmp_path,
        require_verification=True,
        ssrf_resolve_dns=False,
        _env_file=None,
    )
    return TestClient(create_app(settings)), settings


def _token_from_outbox(settings: Settings, email: str) -> str:
    safe = email.replace("@", "_at_")
    text = (settings.auth_outbox_dir / f"{safe}.txt").read_text(encoding="utf-8")
    return text.strip().splitlines()[-1]


def test_signup_requires_verification_and_returns_generic_202(tmp_path) -> None:
    client, _ = _client(tmp_path)
    resp = client.post("/api/auth/signup", json=CREDS)
    assert resp.status_code == 202
    body = resp.json()
    assert body == {"status": "verification_required", "email": CREDS["email"]}
    assert "token" not in body


def test_duplicate_signup_is_indistinguishable(tmp_path) -> None:
    client, _ = _client(tmp_path)
    first = client.post("/api/auth/signup", json=CREDS)
    second = client.post("/api/auth/signup", json=CREDS)
    # No 409 oracle: a duplicate returns the exact same generic response.
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()


def test_login_blocked_until_verified_then_works(tmp_path) -> None:
    client, settings = _client(tmp_path)
    client.post("/api/auth/signup", json=CREDS)

    # Correct password but unverified → 403 (only visible with the right password).
    assert client.post("/api/auth/login", json=CREDS).status_code == 403

    token = _token_from_outbox(settings, CREDS["email"])
    verified = client.post("/api/auth/verify", json={"token": token})
    assert verified.status_code == 200
    assert verified.json()["token"]

    # Verified → login now succeeds.
    assert client.post("/api/auth/login", json=CREDS).status_code == 200


def test_bad_verification_token_is_400(tmp_path) -> None:
    client, _ = _client(tmp_path)
    assert client.post("/api/auth/verify", json={"token": "nope"}).status_code == 400
