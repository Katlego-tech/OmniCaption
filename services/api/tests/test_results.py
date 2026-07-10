"""/api/results — read-only view over the captioner's results.json output."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

SAMPLE_RESULTS = [
    {"task_id": "v1", "captions": {"formal": "A person speaks.", "sarcastic": "Riveting."}},
    {"task_id": "v2", "captions": {"formal": "A cat sits."}},
]


def _write_results(settings) -> None:
    settings.results_path.parent.mkdir(parents=True, exist_ok=True)
    settings.results_path.write_text(json.dumps(SAMPLE_RESULTS), encoding="utf-8")


def test_results_empty_when_pipeline_has_not_run(client: TestClient) -> None:
    resp = client.get("/api/results")
    assert resp.status_code == 200
    assert resp.json() == []


def test_results_lists_all_clips(client: TestClient, settings) -> None:
    _write_results(settings)
    resp = client.get("/api/results")
    assert resp.status_code == 200
    assert resp.json() == SAMPLE_RESULTS


def test_results_by_task_id(client: TestClient, settings) -> None:
    _write_results(settings)
    resp = client.get("/api/results/v2")
    assert resp.status_code == 200
    assert resp.json() == SAMPLE_RESULTS[1]


def test_unknown_task_id_is_404(client: TestClient, settings) -> None:
    _write_results(settings)
    assert client.get("/api/results/v999").status_code == 404
