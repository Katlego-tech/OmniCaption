"""/api/search and /api/qa — Track 3 stubs: contract pinned, implementation pending."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_search_is_501_until_track3_lands(client: TestClient) -> None:
    resp = client.post("/api/search", json={"query": "person on a bike"})
    assert resp.status_code == 501
    assert "Track 3" in resp.json()["detail"]


def test_qa_is_501_until_track3_lands(client: TestClient) -> None:
    resp = client.post("/api/qa", json={"question": "what happens at 0:12?"})
    assert resp.status_code == 501
    assert "Track 3" in resp.json()["detail"]


def test_search_still_validates_its_contract(client: TestClient) -> None:
    # The request model is enforced now so the frontend can build against it.
    assert client.post("/api/search", json={}).status_code == 422
    assert client.post("/api/qa", json={}).status_code == 422
