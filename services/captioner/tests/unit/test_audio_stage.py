"""Unit tests for WhisperTranscriber using Fireworks AI API (T035)."""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from app.core.config import Settings
from app.core.errors import TranscriptionError
from app.pipeline.audio import WhisperTranscriber


@pytest.fixture
def settings_with_key() -> Settings:
    return Settings(
        fireworks_api_key="fake_key",
        fireworks_api_url="https://api.fireworks.ai/inference/v1",
        fireworks_whisper_model="whisper-v3",
    )


def test_transcribe_success(
    monkeypatch: pytest.MonkeyPatch,
    settings_with_key: Settings,
    tmp_path: Path,
) -> None:
    """WhisperTranscriber calls Fireworks API and returns a valid Transcript."""
    transcriber = WhisperTranscriber(settings_with_key)
    transcriber.load()

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "text": "hello world",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 2.0,
                        "text": "hello world",
                        "words": [
                            {"word": "hello", "start": 0.0, "end": 0.9},
                            {"word": "world", "start": 1.0, "end": 2.0},
                        ],
                    }
                ],
            }

    def mock_post(url, headers, files, data, **kwargs):
        assert url == f"{settings_with_key.fireworks_api_url}/audio/transcriptions"
        assert headers["Authorization"] == f"Bearer {settings_with_key.fireworks_api_key}"
        data_dict = dict(data)
        assert data_dict["model"] == settings_with_key.fireworks_whisper_model
        assert data_dict["response_format"] == "verbose_json"
        return MockResponse()

    monkeypatch.setattr(requests, "post", mock_post)

    wav_file = tmp_path / "dummy.wav"
    wav_file.touch()
    t = transcriber.transcribe(wav_file)
    assert t.text == "hello world"
    assert len(t.segments) == 1
    assert len(t.segments[0].words) == 2
    assert t.segments[0].words[0].text == "hello"
    assert t.segments[0].words[1].text == "world"


def test_transcribe_empty_or_no_speech(
    monkeypatch: pytest.MonkeyPatch,
    settings_with_key: Settings,
    tmp_path: Path,
) -> None:
    """If the API returns no speech segments, an empty Transcript is returned."""
    transcriber = WhisperTranscriber(settings_with_key)
    transcriber.load()

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "text": "",
                "segments": [],
            }

    monkeypatch.setattr(requests, "post", lambda *a, **k: MockResponse())

    wav_file = tmp_path / "dummy.wav"
    wav_file.touch()
    t = transcriber.transcribe(wav_file)
    assert t.text == ""
    assert len(t.segments) == 0


def test_transcribe_api_error_raises_transcription_error(
    monkeypatch: pytest.MonkeyPatch,
    settings_with_key: Settings,
    tmp_path: Path,
) -> None:
    """If Fireworks API returns an HTTP error, raise TranscriptionError."""
    transcriber = WhisperTranscriber(settings_with_key)
    transcriber.load()

    class MockResponse:
        status_code = 400
        text = "Bad Request: invalid file format"

    monkeypatch.setattr(requests, "post", lambda *a, **k: MockResponse())

    wav_file = tmp_path / "dummy.wav"
    wav_file.touch()
    with pytest.raises(TranscriptionError) as exc_info:
        transcriber.transcribe(wav_file)

    assert "api failed" in str(exc_info.value).lower()
