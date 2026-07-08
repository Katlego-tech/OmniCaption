"""Tests for the tasks.json loader and schema validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.schema import Style, load_tasks


def test_load_tasks_valid(tmp_path: Path) -> None:
    """A valid tasks.json loads correctly."""
    content = """
    [
      {
        "task_id": "v1",
        "video_url": "https://example.com/clip.mp4",
        "styles": ["formal", "sarcastic"]
      }
    ]
    """
    path = tmp_path / "tasks.json"
    path.write_text(content, encoding="utf-8")

    tasks = load_tasks(path)
    assert len(tasks) == 1
    assert tasks[0].task_id == "v1"
    assert tasks[0].video_url == "https://example.com/clip.mp4"
    assert tasks[0].styles == [Style.FORMAL, Style.SARCASTIC]


def test_load_tasks_drops_unknown_style_but_keeps_valid(tmp_path: Path) -> None:
    """Unknown styles are dropped, but valid styles in the same task are kept."""
    content = """
    [
      {
        "task_id": "v1",
        "video_url": "https://example.com/clip.mp4",
        "styles": ["formal", "nonsense", "sarcastic"]
      }
    ]
    """
    path = tmp_path / "tasks.json"
    path.write_text(content, encoding="utf-8")

    tasks = load_tasks(path)
    assert len(tasks) == 1
    assert tasks[0].styles == [Style.FORMAL, Style.SARCASTIC]


def test_load_tasks_rejects_empty_styles_after_dropping(tmp_path: Path) -> None:
    """If all styles are unknown/empty, the task is rejected."""
    content = """
    [
      {
        "task_id": "v1",
        "video_url": "https://example.com/clip.mp4",
        "styles": ["nonsense", "garbage"]
      }
    ]
    """
    path = tmp_path / "tasks.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValidationError):
        load_tasks(path)


def test_load_tasks_malformed_json(tmp_path: Path) -> None:
    """Malformed JSON fails fast with JSONDecodeError."""
    path = tmp_path / "tasks.json"
    path.write_text("invalid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_tasks(path)


def test_load_tasks_malformed_schema(tmp_path: Path) -> None:
    """Malformed structural schema (e.g. not an array) fails fast with ValidationError."""
    content = """
    {
      "task_id": "v1",
      "video_url": "https://example.com/clip.mp4",
      "styles": ["formal"]
    }
    """
    path = tmp_path / "tasks.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValidationError):
        load_tasks(path)


def test_load_tasks_missing_required_fields(tmp_path: Path) -> None:
    """Missing required fields raises ValidationError."""
    content = """
    [
      {
        "task_id": "v1",
        "styles": ["formal"]
      }
    ]
    """
    path = tmp_path / "tasks.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValidationError):
        load_tasks(path)
