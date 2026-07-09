"""Keyframe extraction tests using synthetic frames and a mocked cv2."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pytest

from app.pipeline import vision
from app.pipeline.vision import _mean_abs_diff


class _FakeCapture:
    """Minimal stand-in for cv2.VideoCapture yielding preset frames."""

    def __init__(self, frames: list[np.ndarray], fps: float = 25.0) -> None:
        self._frames = frames
        self._i = 0
        self._fps = fps

    def isOpened(self) -> bool:  # noqa: N802 - mirror cv2 API
        return True

    def get(self, _prop: int) -> float:  # noqa: D102 - cv2 API
        return self._fps

    def read(self):  # noqa: D102 - cv2 API
        if self._i >= len(self._frames):
            return False, None
        frame = self._frames[self._i]
        self._i += 1
        return True, frame

    def release(self) -> None:  # noqa: D102 - cv2 API
        return None


def _install_fake_cv2(monkeypatch: pytest.MonkeyPatch, frames: list[np.ndarray]) -> None:
    """Register a fake ``cv2`` module exposing just what vision.py touches."""
    fake = types.ModuleType("cv2")
    fake.CAP_PROP_FPS = 5
    fake.COLOR_BGR2RGB = 4
    fake.VideoCapture = lambda _path: _FakeCapture(frames)
    monkeypatch.setitem(sys.modules, "cv2", fake)


def test_mean_abs_diff_zero_for_identical() -> None:
    """Identical frames have zero mean absolute difference."""
    frame = np.full((4, 4, 3), 100, dtype=np.uint8)
    assert _mean_abs_diff(frame, frame) == 0.0


def test_extract_keyframes_returns_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """A static video yields exactly the baseline first frame."""
    static = [np.full((8, 8, 3), 50, dtype=np.uint8) for _ in range(5)]
    _install_fake_cv2(monkeypatch, static)

    keyframes = vision.extract_keyframes(Path("fake.mp4"), threshold=30.0)
    assert len(keyframes) == 1
    assert keyframes[0].index == 0


def test_extract_keyframes_reacts_to_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """A large pixel jump produces a second keyframe; a high threshold suppresses it."""
    dark = np.zeros((8, 8, 3), dtype=np.uint8)
    bright = np.full((8, 8, 3), 255, dtype=np.uint8)
    frames = [dark, dark, bright, bright]

    _install_fake_cv2(monkeypatch, frames)
    low = vision.extract_keyframes(Path("fake.mp4"), threshold=30.0)
    assert len(low) == 2  # baseline + the dark->bright scene change

    _install_fake_cv2(monkeypatch, frames)
    high = vision.extract_keyframes(Path("fake.mp4"), threshold=300.0)
    assert len(high) == 1  # threshold above max possible diff -> baseline only


def test_align_to_transcript_windows_words() -> None:
    """Aligned text is bucketed into per-keyframe time windows."""
    from app.pipeline.audio import Segment, Transcript, Word

    transcript = Transcript(
        language="en",
        duration=4.0,
        segments=[
            Segment(
                start=0.0,
                end=4.0,
                text="hello brave new world",
                words=[
                    Word(0.0, 0.5, "hello"),
                    Word(1.6, 2.0, "brave"),
                    Word(2.1, 2.5, "new"),
                    Word(3.0, 3.4, "world"),
                ],
            )
        ],
    )
    dummy = np.zeros((2, 2, 3), dtype=np.uint8)
    keyframes = [
        vision.Keyframe(index=0, timestamp=0.0, image=dummy),
        vision.Keyframe(index=40, timestamp=1.5, image=dummy),
    ]
    vision.align_to_transcript(keyframes, transcript)

    assert keyframes[0].aligned_text == "hello"
    assert "brave" in keyframes[1].aligned_text
    assert "world" in keyframes[1].aligned_text


def test_encode_image_to_base64() -> None:
    """encode_image_to_base64 returns a non-empty string that decodes to the original dimensions."""
    import base64

    import cv2

    image = np.zeros((10, 10, 3), dtype=np.uint8)
    b64_str = vision.encode_image_to_base64(image)
    assert isinstance(b64_str, str)
    assert len(b64_str) > 0

    # Decode and check shape
    img_data = base64.b64decode(b64_str)
    decoded = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape == (10, 10, 3)
