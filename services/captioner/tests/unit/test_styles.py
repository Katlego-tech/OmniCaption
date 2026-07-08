"""Style prompt coverage tests."""

from __future__ import annotations

import pytest

from app.core.schema import ALL_STYLES, Style
from app.prompts.styles import STYLE_SYSTEM_PROMPTS, get_style_prompt


def test_all_styles_have_prompts() -> None:
    """Every declared style has a non-trivial system prompt."""
    assert set(STYLE_SYSTEM_PROMPTS) == set(Style)
    for style in Style:
        prompt = STYLE_SYSTEM_PROMPTS[style]
        assert isinstance(prompt, str)
        assert len(prompt.strip()) > 40


def test_get_style_prompt_accepts_str_and_enum() -> None:
    """get_style_prompt resolves both enum and string inputs identically."""
    for value in ALL_STYLES:
        assert get_style_prompt(value) == get_style_prompt(Style(value))


def test_get_style_prompt_rejects_unknown() -> None:
    """An unknown style raises KeyError."""
    with pytest.raises(KeyError):
        get_style_prompt("interpretive_dance")
