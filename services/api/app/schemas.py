"""Pydantic models mirroring the captioner I/O contract (docs/16-io-contract.md).

Kept as a standalone copy: this service deploys without the captioner package
installed, so it must not import from ``services/captioner``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Style(StrEnum):
    """The four supported caption styles."""

    FORMAL = "formal"
    SARCASTIC = "sarcastic"
    HUMOROUS_TECH = "humorous_tech"
    HUMOROUS_NON_TECH = "humorous_non_tech"


class TaskIn(BaseModel):
    """A captioning request as submitted by the frontend."""

    task_id: str = Field(..., min_length=1, description="Unique clip identifier, e.g. 'v1'.")
    video_url: str = Field(..., description="Publicly downloadable video URL.")
    styles: list[Style] = Field(..., min_length=1, description="Requested caption styles.")

    @field_validator("styles", mode="before")
    @classmethod
    def _drop_unknown_and_dedupe(cls, value: Any) -> Any:
        """Drop unknown styles and duplicates, matching the pipeline's ingestion behavior."""
        if isinstance(value, list):
            seen: set[Style] = set()
            ordered: list[Style] = []
            for item in value:
                try:
                    style = item if isinstance(item, Style) else Style(item)
                except ValueError:
                    continue
                if style not in seen:
                    seen.add(style)
                    ordered.append(style)
            return ordered
        return value


class ClipResult(BaseModel):
    """Captions produced for one task: a style -> text mapping."""

    task_id: str = Field(..., min_length=1)
    captions: dict[Style, str] = Field(default_factory=dict)


class KeyValidationRequest(BaseModel):
    """Body for /api/keys/validate."""

    api_key: str = Field(..., min_length=1, description="Fireworks AI API key to check.")


class SearchRequest(BaseModel):
    """Body for /api/search (Track 3 contract, pinned ahead of implementation)."""

    query: str = Field(..., min_length=1, description="Natural-language moment query.")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of moments to return.")


class QARequest(BaseModel):
    """Body for /api/qa (Track 3 contract, pinned ahead of implementation)."""

    question: str = Field(..., min_length=1, description="Question over the indexed corpus.")
