"""/api/search + /api/qa with a built oracle index — the live Track 3 path.

Skipped wholesale when the oracle package is not installed (the stub behavior
for that case is covered in test_stretch_stubs.py).
"""

from __future__ import annotations

import math
import zlib

import pytest
from fastapi.testclient import TestClient

oracle_index = pytest.importorskip("oracle.index", reason="oracle package not installed")

from oracle.index import Moment, MomentIndex  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

DIMS = 32


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * DIMS
            for word in text.lower().split():
                vec[zlib.crc32(word.encode()) % DIMS] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class FakeChat:
    def complete(self, system: str, user: str) -> str:
        return "At [v1 @ 0.0s] a chef whisks eggs."


@pytest.fixture()
def live_client(tmp_path) -> TestClient:
    settings = Settings(data_dir=tmp_path, _env_file=None)
    embedder = FakeEmbedder()
    index = MomentIndex.build(
        [
            Moment(task_id="v1", kind="caption", style="formal", text="a chef whisks eggs"),
            Moment(task_id="v2", kind="caption", style="formal", text="a cyclist rides at dusk"),
        ],
        embedder,
    )
    index.save(settings.oracle_index_path)

    app = create_app(settings)
    app.state.oracle_embedder = embedder
    app.state.oracle_chat = FakeChat()
    return TestClient(app)


def test_search_returns_ranked_hits(live_client: TestClient) -> None:
    resp = live_client.post("/api/search", json={"query": "chef whisks eggs", "top_k": 2})
    assert resp.status_code == 200
    hits = resp.json()["hits"]
    assert hits and hits[0]["task_id"] == "v1"
    assert hits[0]["score"] >= hits[-1]["score"]


def test_qa_returns_grounded_answer_with_citations(live_client: TestClient) -> None:
    resp = live_client.post("/api/qa", json={"question": "what is the chef doing?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert body["citations"] and body["citations"][0]["task_id"] == "v1"


def test_missing_key_without_injection_is_401(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    settings = Settings(data_dir=tmp_path, _env_file=None)
    embedder = FakeEmbedder()
    MomentIndex.build([Moment(task_id="v1", kind="caption", text="something")], embedder).save(
        settings.oracle_index_path
    )

    client = TestClient(create_app(settings))  # no injected embedder/chat
    resp = client.post("/api/search", json={"query": "anything"})
    assert resp.status_code == 401
