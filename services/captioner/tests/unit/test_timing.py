"""Unit tests for timing utilities."""

from __future__ import annotations

import time

from app.core.timing import stage_timer


def test_stage_timer_records_duration() -> None:
    """stage_timer records the correct stage name and non-trivial duration."""
    timings = {}
    with stage_timer("test_stage", timings):
        time.sleep(0.01)

    assert "test_stage" in timings
    assert timings["test_stage"] >= 0.01
