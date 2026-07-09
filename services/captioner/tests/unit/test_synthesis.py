"""Unit tests for CaptionSynthesizer (T052-T054, T062-T065)."""

from __future__ import annotations

import numpy as np
import pytest
import requests

from app.core.config import Settings
from app.core.schema import Style
from app.pipeline.audio import Transcript
from app.pipeline.synthesis import CaptionSynthesizer
from app.pipeline.vision import Keyframe
from app.prompts.pmp import PMP_INSTRUCTION


@pytest.fixture
def settings_with_key() -> Settings:
    return Settings(
        fireworks_api_key="fake_key",
        fireworks_api_url="https://api.fireworks.ai/inference/v1",
        fireworks_vlm_model="qwen2-vl-72b-instruct",
    )


def test_modality_order_and_pmp(settings_with_key: Settings) -> None:
    """_build_messages puts images first, then transcript, then optional PMP, then style."""
    synth = CaptionSynthesizer(settings_with_key)
    dummy_img = np.zeros((10, 10, 3), dtype=np.uint8)
    keyframes = [Keyframe(index=0, timestamp=0.0, image=dummy_img)]

    # Test formal style (no PMP)
    messages = synth._build_messages(keyframes, "Test transcript", Style.FORMAL)
    content = messages[0]["content"]

    assert len(content) == 3
    assert content[0]["type"] == "image_url"
    assert "data:image/jpeg;base64" in content[0]["image_url"]["url"]
    assert content[1]["type"] == "text"
    assert "Transcript:\nTest transcript" in content[1]["text"]
    assert content[2]["type"] == "text"
    assert len(content[2]["text"]) > 10

    # Test sarcastic style (includes PMP)
    messages_sarcastic = synth._build_messages(
        keyframes, "Test transcript", Style.SARCASTIC
    )
    content_sarc = messages_sarcastic[0]["content"]

    assert len(content_sarc) == 4
    assert content_sarc[0]["type"] == "image_url"
    assert content_sarc[1]["type"] == "text"
    assert content_sarc[2]["type"] == "text"
    assert content_sarc[2]["text"] == PMP_INSTRUCTION
    assert content_sarc[3]["type"] == "text"


def test_synthesis_success(monkeypatch: pytest.MonkeyPatch, settings_with_key: Settings) -> None:
    """generate_caption calls Fireworks API and returns the generated content."""
    synth = CaptionSynthesizer(settings_with_key)
    synth.load()

    dummy_img = np.zeros((2, 2, 3), dtype=np.uint8)
    keyframes = [Keyframe(index=0, timestamp=0.0, image=dummy_img)]
    transcript = Transcript(language="en", duration=1.0)

    class MockResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "A formal caption."}}]}

    def mock_post(url, headers, json, **kwargs):
        assert url == f"{settings_with_key.fireworks_api_url}/chat/completions"
        assert headers["Authorization"] == f"Bearer {settings_with_key.fireworks_api_key}"
        assert json["model"] == settings_with_key.fireworks_vlm_model
        assert json["temperature"] == 0.0
        return MockResponse()

    monkeypatch.setattr(requests, "post", mock_post)

    caption = synth.generate_caption(keyframes, transcript, Style.FORMAL)
    assert caption == "A formal caption."


def test_synthesis_fallback_on_api_error(
    monkeypatch: pytest.MonkeyPatch,
    settings_with_key: Settings,
) -> None:
    """VLM API failure returns empty captions which triggers the fallback in orchestrator."""
    synth = CaptionSynthesizer(settings_with_key)
    synth.load()

    dummy_img = np.zeros((2, 2, 3), dtype=np.uint8)
    keyframes = [Keyframe(index=0, timestamp=0.0, image=dummy_img)]
    transcript = Transcript(language="en", duration=1.0)

    class MockResponse:
        status_code = 500
        text = "Internal Server Error"

    monkeypatch.setattr(requests, "post", lambda *a, **k: MockResponse())

    # generate_for_styles handles exceptions and returns fallback caption
    captions = synth.generate_for_styles(keyframes, transcript, [Style.FORMAL])
    assert "[Fallback]" in captions[Style.FORMAL]
