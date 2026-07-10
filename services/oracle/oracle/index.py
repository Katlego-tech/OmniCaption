"""The moment index: build, persist, and cosine-search embedded moments."""

from __future__ import annotations

import json
import math
from pathlib import Path

from pydantic import BaseModel, Field

from oracle.embeddings import Embedder


class Moment(BaseModel):
    """One indexable unit of evidence: a caption or a transcript segment."""

    task_id: str
    kind: str = Field(description="'caption' or 'transcript'.")
    style: str | None = Field(default=None, description="Caption style, when kind='caption'.")
    text: str
    t_start: float | None = Field(default=None, description="Segment start (s), when known.")
    t_end: float | None = Field(default=None, description="Segment end (s), when known.")
    vector: list[float] = Field(default_factory=list)


class SearchHit(BaseModel):
    """A ranked retrieval result."""

    moment: Moment
    score: float


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class MomentIndex:
    """In-memory vector index with JSON persistence (small corpora by design)."""

    def __init__(self, moments: list[Moment]) -> None:
        self.moments = moments

    def __len__(self) -> int:
        return len(self.moments)

    @classmethod
    def build(cls, moments: list[Moment], embedder: Embedder) -> MomentIndex:
        """Embed every moment's text in one batched call and return the index."""
        if moments:
            vectors = embedder.embed([m.text for m in moments])
            moments = [
                m.model_copy(update={"vector": v}) for m, v in zip(moments, vectors, strict=True)
            ]
        return cls(list(moments))

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [m.model_dump() for m in self.moments]
        path.write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> MomentIndex:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls([Moment.model_validate(item) for item in data])

    def search(self, query: str, embedder: Embedder, top_k: int = 5) -> list[SearchHit]:
        """Rank all moments against the query by cosine similarity."""
        if not self.moments:
            return []
        query_vec = embedder.embed([query])[0]
        hits = [
            SearchHit(moment=m, score=_cosine(query_vec, m.vector))
            for m in self.moments
            if m.vector
        ]
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]
