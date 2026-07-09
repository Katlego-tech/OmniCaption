"""Integration tests for Fireworks VLM API caption synthesis (T055)."""

from __future__ import annotations

import numpy as np
import pytest
import requests

from app.core.config import Settings
from app.core.schema import Style
from app.pipeline.audio import Transcript
from app.pipeline.synthesis import CaptionSynthesizer
from app.pipeline.vision import Keyframe


def test_synthesis_fireworks_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies CaptionSynthesizer calls the Fireworks VLM API and formats the output."""
    settings = Settings(
        fireworks_api_key="integration_test_key",
        fireworks_api_url="https://api.fireworks.ai/inference/v1",
        fireworks_vlm_model="qwen2-vl-72b-instruct",
    )

    class MockResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Integrated VLM Caption"}}]}

    calls = 0

    def mock_post(url, headers, json, **kwargs):
        nonlocal calls
        calls += 1
        assert url == f"{settings.fireworks_api_url}/chat/completions"
        assert headers["Authorization"] == "Bearer integration_test_key"
        assert json["model"] == "qwen2-vl-72b-instruct"
        assert json["temperature"] == 0.0
        return MockResponse()

    monkeypatch.setattr(requests, "post", mock_post)

    synth = CaptionSynthesizer(settings)
    synth.load()

    dummy_img = np.zeros((10, 10, 3), dtype=np.uint8)
    keyframes = [Keyframe(index=0, timestamp=1.2, image=dummy_img)]
    transcript = Transcript(language="en", duration=2.5)

    caption = synth.generate_caption(keyframes, transcript, Style.FORMAL)

    assert calls == 1
    assert caption == "Integrated VLM Caption"
