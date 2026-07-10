"""POST /api/keys/validate — Fireworks API key validation (probe is stubbed)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.routers import keys as keys_router


def test_valid_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(keys_router, "probe_fireworks_key", lambda api_key, base_url: True)
    resp = client.post("/api/keys/validate", json={"api_key": "fw-good"})
    assert resp.status_code == 200
    assert resp.json() == {"valid": True}


def test_invalid_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(keys_router, "probe_fireworks_key", lambda api_key, base_url: False)
    resp = client.post("/api/keys/validate", json={"api_key": "fw-bad"})
    assert resp.status_code == 200
    assert resp.json() == {"valid": False}


def test_unreachable_upstream_is_502(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(api_key: str, base_url: str) -> bool:
        raise keys_router.UpstreamError("connection refused")

    monkeypatch.setattr(keys_router, "probe_fireworks_key", _boom)
    assert client.post("/api/keys/validate", json={"api_key": "fw-any"}).status_code == 502


def test_missing_key_is_422(client: TestClient) -> None:
    assert client.post("/api/keys/validate", json={}).status_code == 422
