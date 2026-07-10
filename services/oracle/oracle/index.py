"""The moment index: build, persist, and cosine-search embedded moments."""

from __future__ import annotations

import json
import math
from pathlib import Path

from pydantic import BaseModel, Field

from oracle.embeddings import ClipEncoder, Embedder


class Moment(BaseModel):
    """One indexable unit of evidence: a caption, transcript segment, or keyframe."""

    task_id: str
    kind: str = Field(description="'caption', 'transcript', or 'keyframe'.")
    style: str | None = Field(default=None, description="Caption style, when kind='caption'.")
    text: str
    t_start: float | None = Field(default=None, description="Segment start (s), when known.")
    t_end: float | None = Field(default=None, description="Segment end (s), when known.")
    vector: list[float] = Field(default_factory=list)
    space: str = Field(
        default="text",
        description="Embedding space: 'text' (Fireworks) or 'clip' (visual encoder).",
    )
    media: str | None = Field(
        default=None, description="Source media path for visual moments (keyframe image)."
    )


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
    def build(
        cls,
        moments: list[Moment],
        embedder: Embedder,
        clip_encoder: ClipEncoder | None = None,
    ) -> MomentIndex:
        """Embed moments per space (batched) and return the index.

        Text-space moments use the text embedder; clip-space moments use the
        CLIP encoder over their media. Clip moments are left unembedded (and
        therefore unsearchable) when no encoder is supplied.
        """
        built = [m.model_copy() for m in moments]

        text_items = [m for m in built if m.space == "text"]
        if text_items:
            for moment, vector in zip(
                text_items, embedder.embed([m.text for m in text_items]), strict=True
            ):
                moment.vector = vector

        clip_items = [m for m in built if m.space == "clip" and m.media]
        if clip_items and clip_encoder is not None:
            for moment, vector in zip(
                clip_items,
                clip_encoder.embed_images([m.media or "" for m in clip_items]),
                strict=True,
            ):
                moment.vector = vector

        return cls(built)

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [m.model_dump() for m in self.moments]
        path.write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> MomentIndex:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls([Moment.model_validate(item) for item in data])

    def search(
        self,
        query: str,
        embedder: Embedder,
        top_k: int = 5,
        clip_encoder: ClipEncoder | None = None,
    ) -> list[SearchHit]:
        """Rank moments against the query, each within its own embedding space.

        Cross-space scores are merged as-is — cosine similarities from the two
        spaces are not calibrated against each other (MVP behavior). Clip-space
        moments are skipped entirely when no CLIP encoder is available.
        """
        if not self.moments:
            return []
        query_vecs: dict[str, list[float]] = {"text": embedder.embed([query])[0]}
        if clip_encoder is not None:
            query_vecs["clip"] = clip_encoder.embed_text(query)

        hits = [
            SearchHit(moment=m, score=_cosine(query_vecs[m.space], m.vector))
            for m in self.moments
            if m.vector and m.space in query_vecs
        ]
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]
