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

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, RootModel, field_validator


class Style(StrEnum):
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

    @field_validator("styles", mode="before")
    @classmethod
    def _parse_and_dedupe_styles(cls, value: Any) -> Any:
        """Filter out unknown styles with a warning, and deduplicate them."""
        from app.core.logging import get_logger

        logger = get_logger("app.core.schema")

        if isinstance(value, list):
            seen: set[Style] = set()
            ordered: list[Style] = []
            for item in value:
                style = None
                if isinstance(item, Style):
                    style = item
                elif isinstance(item, str):
                    try:
                        style = Style(item)
                    except ValueError:
                        logger.warning("Dropping unknown style: %s", item)
                        continue
                if style is not None and style not in seen:
                    seen.add(style)
                    ordered.append(style)
            return ordered
        return value


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


def load_tasks(path: Path | str) -> list[Task]:
    """Parse and validate tasks from a JSON file.

    Args:
        path: Path to the tasks.json file.

    Returns:
        List of parsed Task objects.

    Raises:
        ValidationError: If structurally malformed.
        json.JSONDecodeError: If not valid JSON.
    """
    import json
    from pathlib import Path

    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return TaskInput.model_validate(data).root
