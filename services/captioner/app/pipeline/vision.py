"""Stage 4: vision — pixel-variance scene-change keyframe extraction (OpenCV).

We walk the video frame by frame, comparing each frame to the last retained
keyframe. When the mean absolute pixel difference exceeds ``threshold`` we treat
it as a scene change and keep the frame. The first frame is always retained as a
baseline. Keyframes are then aligned to transcript segments by timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np

    from app.pipeline.audio import Transcript

logger = get_logger(__name__)


@dataclass(slots=True)
class Keyframe:
    """A retained keyframe with its timestamp and (optional) aligned text."""

    index: int
    timestamp: float
    image: np.ndarray
    score: float = 0.0
    aligned_text: str = field(default="")


def _mean_abs_diff(frame_a: np.ndarray, frame_b: np.ndarray) -> float:
    """Mean absolute per-pixel difference between two frames.

    Args:
        frame_a: First frame (H, W[, C]).
        frame_b: Second frame with the same shape.

    Returns:
        Mean absolute difference across all pixels/channels.
    """
    import numpy as np

    return float(np.mean(np.abs(frame_a.astype(np.int16) - frame_b.astype(np.int16))))


def extract_keyframes(
    video: Path,
    threshold: float = 30.0,
    max_keyframes: int = 8,
    sample_stride: int = 1,
) -> list[Keyframe]:
    """Extract scene-change keyframes via pixel-variance detection.

    Args:
        video: Path to the source video file.
        threshold: Mean-abs-diff above which a frame is a new scene.
        max_keyframes: Hard cap on returned keyframes (controls prompt size).
        sample_stride: Only inspect every Nth frame for speed.

    Returns:
        A list of :class:`Keyframe`, always including a baseline first frame,
        ordered by timestamp.
    """
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        logger.error("Could not open video: %s", video)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    keyframes: list[Keyframe] = []
    last_kept: np.ndarray | None = None
    frame_idx = -1

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            if frame_idx % sample_stride != 0:
                continue

            timestamp = frame_idx / fps

            if last_kept is None:
                # Baseline: always keep the first inspected frame.
                keyframes.append(Keyframe(frame_idx, timestamp, frame, score=0.0))
                last_kept = frame
                continue

            score = _mean_abs_diff(frame, last_kept)
            if score >= threshold:
                keyframes.append(Keyframe(frame_idx, timestamp, frame, score=score))
                last_kept = frame
                if len(keyframes) >= max_keyframes:
                    logger.info("Hit max_keyframes=%d; stopping scan.", max_keyframes)
                    break
    finally:
        cap.release()

    logger.info("Extracted %d keyframes (threshold=%.1f)", len(keyframes), threshold)
    return keyframes


def align_to_transcript(
    keyframes: list[Keyframe],
    transcript: Transcript,
) -> list[Keyframe]:
    """Attach the transcript text overlapping each keyframe's timestamp.

    For each keyframe we collect words whose span brackets the keyframe time (and
    the trailing gap until the next keyframe), giving the VLM local audio context
    per image.

    Args:
        keyframes: Keyframes ordered by timestamp.
        transcript: The audio transcript with word timestamps.

    Returns:
        The same keyframes with ``aligned_text`` populated (mutated in place).
    """
    if not keyframes:
        return keyframes

    words = transcript.words()
    for i, kf in enumerate(keyframes):
        window_end = keyframes[i + 1].timestamp if i + 1 < len(keyframes) else float("inf")
        chunk = [w.text for w in words if kf.timestamp <= w.start < window_end]
        kf.aligned_text = " ".join(chunk).strip()

    return keyframes


def stitch_keyframe_grid(
    keyframes: list[Keyframe],
    cell_width: int = 480,
    cols: int = 4,
) -> np.ndarray | None:
    """Stitch keyframes into a single timestamp-labeled grid image.

    One grid replaces N separate base64 payloads in the VLM call: ~80% less
    upload and a single visual projection pass instead of N, while the
    printed ``t=Xs`` labels give the model explicit chronology (curbs
    hallucinated transitions between non-sequential frames).

    Args:
        keyframes: Keyframes in temporal order.
        cell_width: Width each frame is resized to before placement.
        cols: Grid columns; rows grow as needed, last row padded with black.

    Returns:
        The grid as a BGR image, or ``None`` for an empty keyframe list.
    """
    import cv2
    import numpy as np

    if not keyframes:
        return None

    cells: list[np.ndarray] = []
    for kf in keyframes:
        h, w = kf.image.shape[:2]
        scale = cell_width / float(w)
        cell = cv2.resize(kf.image, (cell_width, max(1, round(h * scale))))
        label = f"t={kf.timestamp:.1f}s"
        # Black outline under white text keeps the label readable on any frame.
        cv2.putText(cell, label, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(
            cell, label, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA
        )
        cells.append(cell)

    cell_h = max(c.shape[0] for c in cells)
    blank = np.zeros((cell_h, cell_width, 3), dtype=cells[0].dtype)
    padded = [
        c if c.shape[0] == cell_h else np.vstack([c, blank[: cell_h - c.shape[0]]]) for c in cells
    ]

    ncols = min(cols, len(padded))
    rows: list[np.ndarray] = []
    for start in range(0, len(padded), ncols):
        row = padded[start : start + ncols]
        row.extend([blank] * (ncols - len(row)))
        rows.append(np.hstack(row))
    return np.vstack(rows)


def encode_image_to_base64(image: np.ndarray, format_ext: str = ".jpg") -> str:
    """Encode an OpenCV image (numpy array) to a base64 string.

    Args:
        image: OpenCV image array (BGR format).
        format_ext: File format extension (e.g. '.jpg', '.png').

    Returns:
        Base64-encoded string representation of the image.
    """
    import base64

    import cv2

    # Downsample image to a maximum dimension of 1024px to prevent VLM server issues
    max_dim = 1024
    h, w = image.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    ok, buffer = cv2.imencode(format_ext, image)
    if not ok:
        raise ValueError("Failed to encode image to base64.")
    return base64.b64encode(buffer).decode("utf-8")
