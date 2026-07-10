"""DELETE endpoints for the tasks manifest and the results output."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

TASK_A = {"task_id": "v1", "video_url": "https://example.com/a.mp4", "styles": ["formal"]}
TASK_B = {"task_id": "v2", "video_url": "https://example.com/b.mp4", "styles": ["sarcastic"]}

RESULTS = [
    {"task_id": "v1", "captions": {"formal": "A."}},
    {"task_id": "v2", "captions": {"formal": "B."}},
]


def test_delete_one_task(client: TestClient) -> None:
    client.post("/api/tasks", json=[TASK_A, TASK_B])
    resp = client.delete("/api/tasks/v1")
    assert resp.status_code == 204
    remaining = client.get("/api/tasks").json()
    assert [t["task_id"] for t in remaining] == ["v2"]


def test_delete_unknown_task_is_404(client: TestClient) -> None:
    client.post("/api/tasks", json=[TASK_A])
    assert client.delete("/api/tasks/nope").status_code == 404


def test_delete_all_tasks(client: TestClient) -> None:
    client.post("/api/tasks", json=[TASK_A, TASK_B])
    resp = client.delete("/api/tasks")
    assert resp.status_code == 204
    assert client.get("/api/tasks").json() == []


def _seed_results(settings) -> None:
    settings.results_path.parent.mkdir(parents=True, exist_ok=True)
    settings.results_path.write_text(json.dumps(RESULTS), encoding="utf-8")


def test_delete_one_result(client: TestClient, settings) -> None:
    _seed_results(settings)
    resp = client.delete("/api/results/v1")
    assert resp.status_code == 204
    remaining = client.get("/api/results").json()
    assert [c["task_id"] for c in remaining] == ["v2"]


def test_delete_unknown_result_is_404(client: TestClient, settings) -> None:
    _seed_results(settings)
    assert client.delete("/api/results/nope").status_code == 404


def test_delete_all_results(client: TestClient, settings) -> None:
    _seed_results(settings)
    resp = client.delete("/api/results")
    assert resp.status_code == 204
    assert client.get("/api/results").json() == []


def test_delete_all_results_when_none_exist_is_noop(client: TestClient) -> None:
    resp = client.delete("/api/results")
    assert resp.status_code == 204
    assert client.get("/api/results").json() == []
