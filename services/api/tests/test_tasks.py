"""/api/tasks — CRUD over the tasks.json manifest (the captioner input contract)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

VALID_TASK = {
    "task_id": "v1",
    "video_url": "https://example.com/clip.mp4",
    "styles": ["formal", "sarcastic"],
}


def test_list_tasks_empty_when_no_manifest(client: TestClient) -> None:
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


def test_submit_task_persists_to_manifest(client: TestClient, settings) -> None:
    resp = client.post("/api/tasks", json=[VALID_TASK])
    assert resp.status_code == 201
    assert resp.json() == [VALID_TASK]

    on_disk = json.loads(settings.tasks_path.read_text(encoding="utf-8"))
    assert on_disk == [VALID_TASK]

    listed = client.get("/api/tasks")
    assert listed.json() == [VALID_TASK]


def test_submit_accepts_single_object_too(client: TestClient) -> None:
    resp = client.post("/api/tasks", json=VALID_TASK)
    assert resp.status_code == 201
    assert resp.json() == [VALID_TASK]


def test_unknown_styles_are_dropped(client: TestClient) -> None:
    task = {**VALID_TASK, "styles": ["formal", "shakespearean"]}
    resp = client.post("/api/tasks", json=[task])
    assert resp.status_code == 201
    assert resp.json()[0]["styles"] == ["formal"]


def test_task_with_no_valid_style_is_rejected(client: TestClient) -> None:
    task = {**VALID_TASK, "styles": ["shakespearean"]}
    resp = client.post("/api/tasks", json=[task])
    assert resp.status_code == 422


def test_resubmitting_a_task_id_replaces_it(client: TestClient) -> None:
    client.post("/api/tasks", json=[VALID_TASK])
    updated = {**VALID_TASK, "styles": ["humorous_tech"]}
    resp = client.post("/api/tasks", json=[updated])
    assert resp.status_code == 201

    listed = client.get("/api/tasks").json()
    assert listed == [updated]


def test_malformed_body_fails_fast(client: TestClient) -> None:
    resp = client.post("/api/tasks", json={"nope": True})
    assert resp.status_code == 422
