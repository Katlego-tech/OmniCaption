"""Pydantic I/O models mirroring the eval harness JSON contract.

Input (``/input/tasks.json``)::

    [
      {
        "task_id": "v1",
        "video_url": "https://.../clip.mp4",
        "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
      }
    ]

Output (``/output/results.json``)::

    [
      {
        "task_id": "v1",
        "captions": {"formal": "...", "sarcastic": "...", ...}
      }
    ]
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, RootModel, field_validator


class Style(str, Enum):
    """The four supported caption styles."""

    FORMAL = "formal"
    SARCASTIC = "sarcastic"
    HUMOROUS_TECH = "humorous_tech"
    HUMOROUS_NON_TECH = "humorous_non_tech"


ALL_STYLES: tuple[str, ...] = tuple(s.value for s in Style)


class Task(BaseModel):
    """A single captioning request from the input manifest."""

    task_id: str = Field(..., min_length=1, description="Unique clip identifier, e.g. 'v1'.")
    video_url: str = Field(..., description="Publicly downloadable video URL.")
    styles: list[Style] = Field(..., min_length=1, description="Requested caption styles.")

    @field_validator("styles")
    @classmethod
    def _dedupe_styles(cls, value: list[Style]) -> list[Style]:
        """Drop duplicate styles while preserving request order."""
        seen: set[Style] = set()
        ordered: list[Style] = []
        for style in value:
            if style not in seen:
                seen.add(style)
                ordered.append(style)
        return ordered


class TaskInput(RootModel[list[Task]]):
    """Top-level input document: a list of tasks."""

    root: list[Task]

    def __iter__(self):  # type: ignore[override]
        """Iterate over the contained tasks."""
        return iter(self.root)

    def __len__(self) -> int:
        """Number of tasks."""
        return len(self.root)


class StyleCaption(BaseModel):
    """A caption for one style (used internally before flattening to dict)."""

    style: Style
    text: str


class ClipResult(BaseModel):
    """Result for a single task: task_id plus a style->caption mapping."""

    task_id: str = Field(..., min_length=1)
    captions: dict[Style, str] = Field(
        default_factory=dict,
        description="Caption text keyed by style; must include every requested style.",
    )

    def has_all(self, requested: list[Style]) -> bool:
        """Return True if every requested style has a non-empty caption.

        Args:
            requested: The styles asked for by the originating task.
        """
        return all(self.captions.get(style) for style in requested)


class ResultsOutput(RootModel[list[ClipResult]]):
    """Top-level output document: a list of per-clip results."""

    root: list[ClipResult]

    def __len__(self) -> int:
        """Number of results."""
        return len(self.root)
