"""Keyframe grid stitching (tests FIRST).

One labeled grid image replaces N separate base64 payloads in the VLM call:
~80% smaller upload, a single visual projection pass, and explicit `t=Xs`
tile labels giving the model chronology (curbs hallucinated transitions
between non-sequential frames).
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core.config import Settings
from app.core.schema import Style
from app.pipeline.audio import Transcript
from app.pipeline.synthesis import CaptionSynthesizer
from app.pipeline.vision import Keyframe, stitch_keyframe_grid


def _kf(i: int, h: int = 90, w: int = 160) -> Keyframe:
    return Keyframe(index=i, timestamp=float(i * 3), image=np.full((h, w, 3), i, np.uint8))


def _transcript() -> Transcript:
    return Transcript(segments=[], language="en", duration=1.0)


def test_grid_shape_full_two_rows() -> None:
    """8 frames stitch to a 2x4 grid (temporal order, uniform cells)."""
    grid = stitch_keyframe_grid([_kf(i) for i in range(8)], cell_width=160, cols=4)
    assert grid is not None
    assert grid.shape == (180, 640, 3)  # 2 rows x 90px, 4 cols x 160px


def test_grid_pads_partial_last_row() -> None:
    """5 frames -> 2 rows, second row padded to full width."""
    grid = stitch_keyframe_grid([_kf(i) for i in range(5)], cell_width=160, cols=4)
    assert grid is not None
    assert grid.shape == (180, 640, 3)


def test_grid_empty_returns_none() -> None:
    assert stitch_keyframe_grid([]) is None


def test_messages_use_single_grid_image_by_default() -> None:
    """keyframe_grid=True (default): ONE image plus a grid-layout note."""
    cfg = Settings(_env_file=None, fireworks_api_key="k")
    synth = CaptionSynthesizer(cfg)
    messages = synth._build_messages([_kf(i) for i in range(8)], "hello", Style.FORMAL)

    user = next(m for m in messages if m["role"] == "user")["content"]
    images = [c for c in user if c["type"] == "image_url"]
    texts = [c["text"] for c in user if c["type"] == "text"]
    assert len(images) == 1, f"expected 1 stitched grid image, got {len(images)}"
    assert any("grid" in t.lower() and "timestamp" in t.lower() for t in texts), (
        "missing the grid-layout note"
    )


def test_messages_per_frame_when_grid_disabled() -> None:
    """keyframe_grid=False keeps the legacy one-image-per-keyframe payload."""
    cfg = Settings(_env_file=None, fireworks_api_key="k", keyframe_grid=False)
    synth = CaptionSynthesizer(cfg)
    messages = synth._build_messages([_kf(i) for i in range(8)], "hello", Style.FORMAL)

    user = next(m for m in messages if m["role"] == "user")["content"]
    images = [c for c in user if c["type"] == "image_url"]
    assert len(images) == 8


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
