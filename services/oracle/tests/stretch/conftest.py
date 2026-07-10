"""Fixtures: deterministic fake embedder/chat so no test touches Fireworks."""

from __future__ import annotations

import json
import math
import sys
import zlib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

DIMS = 32


class FakeEmbedder:
    """Deterministic bag-of-words hash embedding — similar texts get similar vectors.

    Uses crc32, not ``hash()``: Python string hashing is salted per process and
    would make rankings flaky.
    """

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * DIMS
            for word in text.lower().split():
                vec[zlib.crc32(word.encode()) % DIMS] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class FakeChat:
    """Records the prompt it was given and returns a canned grounded answer."""

    def __init__(self) -> None:
        self.system: str | None = None
        self.user: str | None = None

    def complete(self, system: str, user: str) -> str:
        self.system = system
        self.user = user
        return "At [v1 @ 0.0s] a chef whisks eggs in a steel bowl."


@pytest.fixture()
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture()
def chat() -> FakeChat:
    return FakeChat()


@pytest.fixture()
def results_file(tmp_path: Path) -> Path:
    """A results.json in the captioner output contract."""
    results = [
        {
            "task_id": "v1",
            "captions": {
                "formal": "A chef whisks eggs in a steel bowl on a kitchen counter.",
                "sarcastic": "Yes, whisking eggs. Culinary revolution in progress.",
            },
        },
        {
            "task_id": "v2",
            "captions": {
                "formal": "A cyclist rides along a coastal road at sunset.",
            },
        },
    ]
    path = tmp_path / "results.json"
    path.write_text(json.dumps(results), encoding="utf-8")
    return path
