"""/api/auth — signup, login, and bearer-token identity."""

from __future__ import annotations

from fastapi.testclient import TestClient

CREDS = {"email": "tumo@example.com", "password": "correct-horse-battery"}


def test_signup_creates_user_and_returns_token(client: TestClient) -> None:
    resp = client.post("/api/auth/signup", json=CREDS)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == CREDS["email"]
    assert body["token"]


def test_signup_duplicate_email_is_409(client: TestClient) -> None:
    client.post("/api/auth/signup", json=CREDS)
    resp = client.post("/api/auth/signup", json=CREDS)
    assert resp.status_code == 409


def test_signup_rejects_short_password(client: TestClient) -> None:
    resp = client.post("/api/auth/signup", json={"email": "a@b.com", "password": "short"})
    assert resp.status_code == 422


def test_signup_rejects_bad_email(client: TestClient) -> None:
    resp = client.post("/api/auth/signup", json={"email": "not-an-email", "password": "longenough"})
    assert resp.status_code == 422


def test_login_with_valid_credentials(client: TestClient) -> None:
    client.post("/api/auth/signup", json=CREDS)
    resp = client.post("/api/auth/login", json=CREDS)
    assert resp.status_code == 200
    assert resp.json()["token"]


def test_login_wrong_password_is_401(client: TestClient) -> None:
    client.post("/api/auth/signup", json=CREDS)
    resp = client.post("/api/auth/login", json={**CREDS, "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_unknown_user_is_401(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json=CREDS)
    assert resp.status_code == 401


def test_me_returns_identity_for_valid_token(client: TestClient) -> None:
    token = client.post("/api/auth/signup", json=CREDS).json()["token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == CREDS["email"]


def test_me_without_token_is_401(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_tampered_token(client: TestClient) -> None:
    token = client.post("/api/auth/signup", json=CREDS).json()["token"]
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401


def test_password_is_not_stored_in_plaintext(client: TestClient, settings) -> None:
    client.post("/api/auth/signup", json=CREDS)
    raw = settings.auth_db_path.read_bytes()
    assert CREDS["password"].encode() not in raw
