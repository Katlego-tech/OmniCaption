"""Shared pytest fixtures for the captioner package."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.schema import Style
from app.pipeline.orchestrator import CaptionState


@pytest.fixture
def temp_work_dir(tmp_path: Path) -> Path:
    """A temporary working directory."""
    d = tmp_path / "work"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """A temporary output directory."""
    d = tmp_path / "out"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def settings(temp_work_dir: Path, temp_output_dir: Path) -> Settings:
    """Settings pointed at temp directories."""
    return Settings(work_dir=temp_work_dir, output_dir=temp_output_dir)


@pytest.fixture
def sample_state() -> CaptionState:
    """A sample CaptionState with basic values."""
    return CaptionState(
        task_id="v1",
        styles=[Style.FORMAL, Style.SARCASTIC],
    )
