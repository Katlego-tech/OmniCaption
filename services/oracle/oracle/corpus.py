"""Build the moment corpus from captioner artifacts.

The Track 2 pipeline ships captions in results.json; word-timed transcripts are
an optional sidecar (transcripts.json) when a run persists them. Both feed the
same Moment shape.
"""

from __future__ import annotations

import json
from pathlib import Path

from oracle.index import Moment


def moments_from_results(path: Path | str) -> list[Moment]:
    """One moment per (task, style) caption in a results.json document."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    moments: list[Moment] = []
    for clip in data:
        for style, text in clip.get("captions", {}).items():
            if text:
                moments.append(
                    Moment(task_id=clip["task_id"], kind="caption", style=style, text=text)
                )
    return moments


def moments_from_keyframes(root: Path | str) -> list[Moment]:
    """Clip-space moments from a keyframe sidecar tree (``root/<task_id>/*.jpg``).

    Timestamps are parsed from the captioner's sidecar filenames
    (``kf000_t1.5.jpg`` → 1.5 s) when present.
    """
    root = Path(root)
    moments: list[Moment] = []
    for image in sorted(root.glob("*/*.jpg")):
        t_start = _timestamp_from_name(image.stem)
        moments.append(
            Moment(
                task_id=image.parent.name,
                kind="keyframe",
                text=f"keyframe {image.stem}",
                t_start=t_start,
                space="clip",
                media=str(image),
            )
        )
    return moments


def _timestamp_from_name(stem: str) -> float | None:
    for part in stem.split("_"):
        if part.startswith("t"):
            try:
                return float(part[1:])
            except ValueError:
                continue
    return None


def moments_from_transcripts(path: Path | str) -> list[Moment]:
    """Moments from an optional transcripts sidecar.

    Expected shape: ``{task_id: [{"text": str, "t_start": float, "t_end": float}, …]}``.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    moments: list[Moment] = []
    for task_id, segments in data.items():
        for segment in segments:
            if segment.get("text"):
                moments.append(
                    Moment(
                        task_id=task_id,
                        kind="transcript",
                        text=segment["text"],
                        t_start=segment.get("t_start"),
                        t_end=segment.get("t_end"),
                    )
                )
    return moments
