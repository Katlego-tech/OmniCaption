"""Timer utilities for pipeline stages and budget verification."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager

from app.core.logging import get_logger

logger = get_logger(__name__)


@contextmanager
def stage_timer(stage_name: str, timings: dict[str, float]) -> Generator[None, None, None]:
    """Context manager to time a pipeline stage and record it.

    Args:
        stage_name: Name of the stage (e.g. 'ingestion').
        timings: Dictionary where timings are recorded.
    """
    start_time = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - start_time
        timings[stage_name] = elapsed
        logger.info("Stage '%s' completed in %.2fs", stage_name, elapsed)
