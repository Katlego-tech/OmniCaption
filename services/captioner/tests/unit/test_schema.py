"""Schema round-trip and validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.schema import (
    ClipResult,
    ResultsOutput,
    Style,
    Task,
    TaskInput,
)


def test_task_input_round_trip() -> None:
    """A well-formed tasks.json parses into Task objects and back."""
    raw = """
    [
      {
        "task_id": "v1",
        "video_url": "https://example.com/clip.mp4",
        "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
      }
    ]
    """
    parsed = TaskInput.model_validate_json(raw)
    assert len(parsed) == 1
    task = parsed.root[0]
    assert task.task_id == "v1"
    assert task.styles == list(Style)


def test_task_rejects_missing_styles() -> None:
    """A task with an empty styles list is rejected."""
    with pytest.raises(ValidationError):
        Task(task_id="v1", video_url="https://example.com/c.mp4", styles=[])


def test_task_rejects_unknown_style() -> None:
    """An unknown style value fails validation."""
    with pytest.raises(ValidationError):
        Task(
            task_id="v1",
            video_url="https://example.com/c.mp4",
            styles=["formal", "nonsense"],
        )


def test_task_dedupes_styles() -> None:
    """Duplicate styles collapse while preserving order."""
    task = Task(
        task_id="v1",
        video_url="https://example.com/c.mp4",
        styles=["formal", "formal", "sarcastic"],
    )
    assert task.styles == [Style.FORMAL, Style.SARCASTIC]


def test_results_output_round_trip() -> None:
    """ResultsOutput serializes to the expected contract shape."""
    clip = ClipResult(
        task_id="v1",
        captions={Style.FORMAL: "A person walks.", Style.SARCASTIC: "Riveting."},
    )
    doc = ResultsOutput(root=[clip])
    dumped = doc.model_dump(mode="json")
    assert dumped[0]["task_id"] == "v1"
    assert dumped[0]["captions"]["formal"] == "A person walks."


def test_clip_result_has_all() -> None:
    """has_all detects missing/empty captions for requested styles."""
    clip = ClipResult(task_id="v1", captions={Style.FORMAL: "x", Style.SARCASTIC: ""})
    assert clip.has_all([Style.FORMAL]) is True
    assert clip.has_all([Style.FORMAL, Style.SARCASTIC]) is False
