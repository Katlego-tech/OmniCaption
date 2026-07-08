"""Tests for audio extraction using ffmpeg."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.core.errors import AudioExtractionError
from app.pipeline.ingestion import extract_audio


def test_extract_audio_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """extract_audio runs ffmpeg successfully and returns the wav path."""
    video_path = tmp_path / "video.mp4"
    video_path.touch()

    # Mock subprocess.run to do nothing (success)
    def mock_run(cmd, *args, **kwargs):
        assert cmd[0] == "ffmpeg"
        # Create dummy wav file
        out_wav = Path(cmd[-1])
        out_wav.touch()
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", mock_run)

    wav_path = extract_audio(video_path, tmp_path)
    assert wav_path == tmp_path / "video.wav"
    assert wav_path.exists()


def test_extract_audio_failure_raises_extraction_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """If ffmpeg exits non-zero, extract_audio raises AudioExtractionError."""
    video_path = tmp_path / "video.mp4"
    video_path.touch()

    def mock_run(cmd, *args, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, stderr="ffmpeg error output")

    monkeypatch.setattr(subprocess, "run", mock_run)

    with pytest.raises(AudioExtractionError) as exc_info:
        extract_audio(video_path, tmp_path)

    assert "ffmpeg" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()


def test_extract_audio_ffmpeg_not_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """If ffmpeg is missing from PATH, extract_audio raises AudioExtractionError."""
    video_path = tmp_path / "video.mp4"
    video_path.touch()

    def mock_run(cmd, *args, **kwargs):
        raise FileNotFoundError("[Errno 2] No such file or directory: 'ffmpeg'")

    monkeypatch.setattr(subprocess, "run", mock_run)

    with pytest.raises(AudioExtractionError) as exc_info:
        extract_audio(video_path, tmp_path)

    assert "missing" in str(exc_info.value).lower() or "ffmpeg" in str(exc_info.value).lower()
