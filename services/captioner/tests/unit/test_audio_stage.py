"""Unit tests for WhisperTranscriber using mocked local Whisper model (T035)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.pipeline.audio import WhisperTranscriber


class MockWord:
    def __init__(self, start: float, end: float, word: str, probability: float = 1.0) -> None:
        self.start = start
        self.end = end
        self.word = word
        self.probability = probability


class MockSegment:
    def __init__(self, start: float, end: float, text: str, words: list[MockWord]) -> None:
        self.start = start
        self.end = end
        self.text = text
        self.words = words


class MockInfo:
    language = "en"
    duration = 2.0


class MockModel:
    def transcribe(self, wav_path: str, **kwargs) -> tuple[list[MockSegment], MockInfo]:
        words = [
            MockWord(0.0, 0.9, "hello"),
            MockWord(1.0, 2.0, "world"),
        ]
        segments = [MockSegment(0.0, 2.0, "hello world", words)]
        return segments, MockInfo()


def test_transcribe_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """WhisperTranscriber transcribes a WAV file successfully using a mocked model."""
    monkeypatch.setattr("app.pipeline.audio.load_whisper", lambda cfg: MockModel())

    settings = Settings(whisper_model_size="tiny")
    transcriber = WhisperTranscriber(settings)
    transcriber.load()

    wav_file = tmp_path / "dummy.wav"
    wav_file.touch()

    t = transcriber.transcribe(wav_file)
    assert t.text == "hello world"
    assert len(t.segments) == 1
    assert len(t.segments[0].words) == 2
    assert t.segments[0].words[0].text == "hello"
    assert t.segments[0].words[1].text == "world"


def test_transcribe_empty_or_no_speech(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """If the model returns no segments, an empty Transcript is returned."""

    class MockEmptyModel:
        def transcribe(self, wav_path: str, **kwargs) -> tuple[list, MockInfo]:
            return [], MockInfo()

    monkeypatch.setattr("app.pipeline.audio.load_whisper", lambda cfg: MockEmptyModel())

    settings = Settings(whisper_model_size="tiny")
    transcriber = WhisperTranscriber(settings)
    transcriber.load()

    wav_file = tmp_path / "dummy.wav"
    wav_file.touch()

    t = transcriber.transcribe(wav_file)
    assert t.text == ""
    assert len(t.segments) == 0
