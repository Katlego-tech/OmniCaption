"""Shared fixtures: isolated data dir + a TestClient wired to it."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    """Settings pointing every path at a throwaway temp directory."""
    return Settings(
        data_dir=tmp_path,
        # A no-op command so /api/tasks/run never touches Docker in tests.
        captioner_cmd=f'"{sys.executable}" -c "print(42)"',
        _env_file=None,
    )


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    """TestClient against an app built from the isolated settings."""
    return TestClient(create_app(settings))


SIGNUP_CREDS = {"email": "tester@example.com", "password": "password-123"}


def authorize(client: TestClient) -> TestClient:
    """Sign up a throwaway user and attach its bearer token to the client."""
    token = client.post("/api/auth/signup", json=SIGNUP_CREDS).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture()
def auth_client(client: TestClient) -> TestClient:
    """An authenticated TestClient (a valid bearer token is pre-attached)."""
    return authorize(client)
