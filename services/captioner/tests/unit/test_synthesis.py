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


@pytest.fixture
def settings_with_key() -> Settings:
    return Settings(
        fireworks_api_key="fake_key",
        fireworks_api_url="https://api.fireworks.ai/inference/v1",
        fireworks_vlm_model="accounts/fireworks/models/kimi-k2p6",
    )


def test_modality_order_and_pmp(settings_with_key: Settings) -> None:
    """_build_messages puts instructions in system and user message split."""
    synth = CaptionSynthesizer(settings_with_key)
    dummy_img = np.zeros((10, 10, 3), dtype=np.uint8)
    keyframes = [Keyframe(index=0, timestamp=0.0, image=dummy_img)]

    # Test formal style (no PMP in system message)
    messages = synth._build_messages(keyframes, "Test transcript", Style.FORMAL)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    system_content = messages[0]["content"]
    assert "meticulous archival captioner" in system_content
    assert "<captionStyle>" in system_content

    user_content = messages[1]["content"]
    assert len(user_content) == 2
    assert user_content[0]["type"] == "image_url"
    assert "data:image/jpeg;base64" in user_content[0]["image_url"]["url"]
    assert user_content[1]["type"] == "text"
    assert "Transcript:\nTest transcript" in user_content[1]["text"]

    # Test sarcastic style (no PMP in system message)
    messages_sarcastic = synth._build_messages(keyframes, "Test transcript", Style.SARCASTIC)
    assert len(messages_sarcastic) == 2
    assert messages_sarcastic[0]["role"] == "system"
    assert messages_sarcastic[1]["role"] == "user"

    system_content_sarc = messages_sarcastic[0]["content"]
    assert "dry, unimpressed critic" in system_content_sarc

    user_content_sarc = messages_sarcastic[1]["content"]
    assert len(user_content_sarc) == 2
    assert user_content_sarc[0]["type"] == "image_url"
    assert user_content_sarc[1]["type"] == "text"


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


def _mock_content(monkeypatch: pytest.MonkeyPatch, content: str, finish_reason: str = "stop"):
    """Patch requests.post so the VLM returns ``content`` with a 200."""

    class MockResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": content}, "finish_reason": finish_reason}]}

    monkeypatch.setattr(requests, "post", lambda *a, **k: MockResponse())


@pytest.mark.parametrize(
    "content",
    [
        "<captionStyle>...</captionStyle>",  # the observed deadpan ellipsis
        "<captionStyle>…</captionStyle>",  # unicode ellipsis
        "<captionStyle>   </captionStyle>",  # whitespace only
        "<captionStyle>--</captionStyle>",  # punctuation only
        "",  # empty response
        "...",  # untagged punctuation-only
    ],
)
def test_degenerate_caption_raises_synthesis_error(
    monkeypatch: pytest.MonkeyPatch, settings_with_key: Settings, content: str
) -> None:
    """A punctuation-only / empty caption must be rejected, not returned."""
    from app.core.errors import SynthesisError

    synth = CaptionSynthesizer(settings_with_key)
    synth.load()
    keyframes = [Keyframe(index=0, timestamp=0.0, image=np.zeros((2, 2, 3), dtype=np.uint8))]
    transcript = Transcript(language="en", duration=1.0)
    _mock_content(monkeypatch, content)

    with pytest.raises(SynthesisError):
        synth.generate_caption(keyframes, transcript, Style.SARCASTIC)


def test_degenerate_caption_falls_back_grounded(
    monkeypatch: pytest.MonkeyPatch, settings_with_key: Settings
) -> None:
    """The batch path turns a degenerate caption into a grounded fallback, never '...'."""
    synth = CaptionSynthesizer(settings_with_key)
    synth.load()
    keyframes = [Keyframe(index=0, timestamp=0.0, image=np.zeros((2, 2, 3), dtype=np.uint8))]
    transcript = Transcript(language="en", duration=1.0)
    _mock_content(monkeypatch, "<captionStyle>...</captionStyle>")

    captions = synth.generate_for_styles(keyframes, transcript, [Style.SARCASTIC])

    assert captions[Style.SARCASTIC] != "..."
    assert "[Fallback]" in captions[Style.SARCASTIC]


def test_short_but_real_caption_is_kept(
    monkeypatch: pytest.MonkeyPatch, settings_with_key: Settings
) -> None:
    """Guard against over-rejection: a short real caption with words is returned."""
    synth = CaptionSynthesizer(settings_with_key)
    synth.load()
    keyframes = [Keyframe(index=0, timestamp=0.0, image=np.zeros((2, 2, 3), dtype=np.uint8))]
    transcript = Transcript(language="en", duration=1.0)
    _mock_content(monkeypatch, "<captionStyle>Rush hour.</captionStyle>")

    assert synth.generate_caption(keyframes, transcript, Style.SARCASTIC) == "Rush hour."


def test_untagged_reasoning_leak_falls_back(
    monkeypatch: pytest.MonkeyPatch, settings_with_key: Settings
) -> None:
    """A long tag-less chain-of-thought blob must never become the caption."""
    synth = CaptionSynthesizer(settings_with_key)
    synth.load()
    keyframes = [Keyframe(index=0, timestamp=0.0, image=np.zeros((2, 2, 3), dtype=np.uint8))]
    transcript = Transcript(language="en", duration=1.0)
    leak = "Let me think about what would be funny here. Maybe something like... " * 30
    _mock_content(monkeypatch, leak, finish_reason="length")

    captions = synth.generate_for_styles(keyframes, transcript, [Style.HUMOROUS_NON_TECH])

    assert "[Fallback]" in captions[Style.HUMOROUS_NON_TECH]
    assert "Let me think" not in captions[Style.HUMOROUS_NON_TECH]


def test_truncated_untagged_response_raises(
    monkeypatch: pytest.MonkeyPatch, settings_with_key: Settings
) -> None:
    """finish_reason='length' with no closing tag is a truncation, not a caption."""
    from app.core.errors import SynthesisError

    synth = CaptionSynthesizer(settings_with_key)
    synth.load()
    keyframes = [Keyframe(index=0, timestamp=0.0, image=np.zeros((2, 2, 3), dtype=np.uint8))]
    transcript = Transcript(language="en", duration=1.0)
    # One attempt so it doesn't retry into success here; assert the raw truncation is rejected.
    synth._cfg = settings_with_key.model_copy(update={"synthesis_max_attempts": 1})
    _mock_content(monkeypatch, "The scene shows a figure walking through", finish_reason="length")

    with pytest.raises(SynthesisError):
        synth.generate_caption(keyframes, transcript, Style.FORMAL)


def test_retry_recovers_after_degenerate(
    monkeypatch: pytest.MonkeyPatch, settings_with_key: Settings
) -> None:
    """A degenerate first attempt is retried; a good second attempt is returned."""
    synth = CaptionSynthesizer(settings_with_key)
    synth.load()
    keyframes = [Keyframe(index=0, timestamp=0.0, image=np.zeros((2, 2, 3), dtype=np.uint8))]
    transcript = Transcript(language="en", duration=1.0)

    replies = iter(
        [
            ("<captionStyle>...</captionStyle>", "stop"),  # attempt 1: ellipsis
            ("<captionStyle>The leaves change.</captionStyle>", "stop"),  # attempt 2: good
        ]
    )
    seen_max_tokens: list[int] = []

    class MockResponse:
        status_code = 200

        def __init__(self, content: str, finish: str) -> None:
            self._content, self._finish = content, finish

        def json(self):
            return {
                "choices": [{"message": {"content": self._content}, "finish_reason": self._finish}]
            }

    def mock_post(url, headers, json, **kwargs):
        seen_max_tokens.append(json["max_tokens"])
        content, finish = next(replies)
        return MockResponse(content, finish)

    monkeypatch.setattr(requests, "post", mock_post)

    caption = synth.generate_caption(keyframes, transcript, Style.SARCASTIC)

    assert caption == "The leaves change."
    # The retry escalated the token budget rather than repeating the same request.
    assert seen_max_tokens == [
        settings_with_key.max_new_tokens,
        settings_with_key.max_new_tokens * 2,
    ]
