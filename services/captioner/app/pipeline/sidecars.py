"""Best-effort sidecar outputs for the Track 3 oracle (services/oracle).

Sidecars are written *after* results.json and must never fail the run: the
callers wrap them in try/except and a broken sidecar only costs oracle
enrichment, never the Track 2 contract.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.logging import get_logger
from app.pipeline.audio import Transcript
from app.pipeline.vision import Keyframe

logger = get_logger(__name__)


def write_transcript_sidecar(transcripts: dict[str, Transcript], path: Path) -> None:
    """Write transcripts in the oracle corpus contract.

    Shape: ``{task_id: [{"text", "t_start", "t_end"}, …]}`` — mirrors
    ``oracle.corpus.moments_from_transcripts``. Tasks with no speech are omitted.

    Args:
        transcripts: Per-task transcripts collected during the run.
        path: Destination file (typically ``/output/transcripts.json``).
    """
    payload: dict[str, list[dict]] = {}
    for task_id, transcript in transcripts.items():
        segments = [
            {"text": seg.text.strip(), "t_start": seg.start, "t_end": seg.end}
            for seg in transcript.segments
            if seg.text.strip()
        ]
        if segments:
            payload[task_id] = segments

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
    logger.info("Wrote transcript sidecar (%d task(s)) -> %s", len(payload), path)


def write_keyframe_sidecar(task_id: str, keyframes: list[Keyframe], root: Path) -> list[Path]:
    """Encode a task's keyframes as JPEGs under ``root/<task_id>/``.

    Filenames carry the timestamp (``kf000_t1.5.jpg``) so the oracle can attach
    a moment time without re-reading the video.

    Args:
        task_id: The originating task id (becomes the subdirectory name).
        keyframes: Keyframes with in-memory images.
        root: The sidecar root (typically ``/output/keyframes``).

    Returns:
        Paths of the files actually written.
    """
    import cv2

    target = root / task_id
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for position, frame in enumerate(keyframes):
        path = target / f"kf{position:03d}_t{frame.timestamp:.1f}.jpg"
        if cv2.imwrite(str(path), frame.image):
            written.append(path)
        else:
            logger.warning("Could not encode keyframe %s for task %s", position, task_id)
    logger.info("Wrote %d keyframe(s) -> %s", len(written), target)
    return written
