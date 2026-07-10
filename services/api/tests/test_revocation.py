"""Server-side token revocation (logout-everywhere)."""

from __future__ import annotations

from fastapi.testclient import TestClient

CREDS = {"email": "revoke@example.com", "password": "password-123"}


def test_logout_revokes_existing_tokens(client: TestClient) -> None:
    token = client.post("/api/auth/signup", json=CREDS).json()["token"]
    auth = {"Authorization": f"Bearer {token}"}

    # Token works before logout.
    assert client.get("/api/auth/me", headers=auth).status_code == 200

    # Logout revokes all outstanding tokens for the user.
    assert client.post("/api/auth/logout", headers=auth).status_code == 204

    # The same token is now rejected.
    assert client.get("/api/auth/me", headers=auth).status_code == 401


def test_logout_requires_auth(client: TestClient) -> None:
    assert client.post("/api/auth/logout").status_code == 401
