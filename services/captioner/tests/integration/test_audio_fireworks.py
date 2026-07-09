"""Integration tests for Fireworks Whisper API transcription (T037)."""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from app.core.config import Settings
from app.pipeline.audio import WhisperTranscriber


def test_audio_fireworks_integration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verifies WhisperTranscriber calls the Fireworks API and parses segments/words."""
    settings = Settings(
        fireworks_api_key="integration_test_key",
        fireworks_api_url="https://api.fireworks.ai/inference/v1",
        fireworks_whisper_model="whisper-v3",
    )

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "text": "test audio transcription",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 1.5,
                        "text": "test audio",
                        "words": [
                            {"word": "test", "start": 0.0, "end": 0.5},
                            {"word": "audio", "start": 0.6, "end": 1.5},
                        ],
                    },
                    {
                        "start": 1.5,
                        "end": 3.0,
                        "text": "transcription",
                        "words": [
                            {"word": "transcription", "start": 1.5, "end": 3.0},
                        ],
                    },
                ],
            }

    calls = 0

    def mock_post(url, headers, files, data, **kwargs):
        nonlocal calls
        calls += 1
        assert url == f"{settings.fireworks_api_url}/audio/transcriptions"
        assert headers["Authorization"] == "Bearer integration_test_key"
        data_dict = dict(data)
        assert data_dict["model"] == "whisper-v3"
        return MockResponse()

    monkeypatch.setattr(requests, "post", mock_post)

    transcriber = WhisperTranscriber(settings)
    transcriber.load()

    wav_file = tmp_path / "audio.wav"
    wav_file.touch()

    transcript = transcriber.transcribe(wav_file)

    assert calls == 1
    assert transcript.text == "test audio transcription"
    assert len(transcript.segments) == 2
    assert len(transcript.words()) == 3
    assert transcript.words()[0].text == "test"
    assert transcript.words()[1].text == "audio"
    assert transcript.words()[2].text == "transcription"
