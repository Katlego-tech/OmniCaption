"""Stage 6: output — build, validate, and atomically write results.json.

Guarantees a schema-valid file even when some captions are missing: absent
styles are backfilled with an empty string so the harness always receives every
requested key.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.logging import get_logger
from app.core.schema import ClipResult, ResultsOutput, Style

logger = get_logger(__name__)


def build_result(
    task_id: str,
    captions: dict[Style, str],
    requested: list[Style],
) -> ClipResult:
    """Build a :class:`ClipResult`, backfilling any missing requested styles.

    Args:
        task_id: The originating task id.
        captions: Generated captions keyed by style.
        requested: Styles the task asked for (defines the required keys).

    Returns:
        A ClipResult whose ``captions`` include every requested style.
    """
    filled: dict[Style, str] = {}
    for style in requested:
        text = captions.get(style, "")
        if not text:
            logger.warning("Missing caption for task=%s style=%s; using empty.", task_id, style)
        filled[style] = text
    return ClipResult(task_id=task_id, captions=filled)


def validate_and_write(results: list[ClipResult], path: Path) -> None:
    """Validate results against the schema and write JSON atomically.

    Args:
        results: Per-clip results.
        path: Destination file (typically ``/output/results.json``).

    Raises:
        pydantic.ValidationError: If ``results`` do not satisfy the schema.
    """
    document = ResultsOutput(root=results)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Serialize enum keys to their string values for the JSON contract.
    payload = [
        {
            "task_id": clip.task_id,
            "captions": {style.value: text for style, text in clip.captions.items()},
        }
        for clip in document.root
    ]

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, path)

    logger.info("Wrote %d results -> %s", len(payload), path)
