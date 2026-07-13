"""Defaults that keep a bare judge `docker run` from silently degrading.

The judging harness pulls the public image and runs it with NO extra flags
(FAQ: "Run the container without local files or manual setup", "No private
secrets are required"). These tests pin the two defaults that protect that run:

1. The per-video download timeout must have headroom for the UHD judging clips
   (a real 2026-07-10 run lost all captions when a 4K download hit the old 60 s
   default — see STATUS.md).
2. An EMPTY-string ``FIREWORKS_API_KEY`` (what the image ENV contains when the
   bake build-arg is not supplied) must behave exactly like an unset key: the
   synthesizer raises ``SynthesisError`` so the style falls back, rather than
   sending a garbage ``Authorization: Bearer`` header upstream.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.errors import SynthesisError
from app.core.schema import Style
from app.pipeline.audio import Transcript
from app.pipeline.synthesis import CaptionSynthesizer


def _default_settings() -> Settings:
    """Settings with env-file loading disabled so only class defaults apply."""
    return Settings(_env_file=None)


def test_download_timeout_covers_uhd_judging_clips() -> None:
    """The judged clips are 1440p-4K MP4s; 60 s was measured too tight."""
    assert _default_settings().download_timeout_s >= 180.0


def test_first_attempt_token_headroom_avoids_length_retry() -> None:
    """4096 max_tokens truncated real reasoning output (finish_reason='length'
    at 18k chars on v1/sarcastic, costing a ~60 s retry); first attempts need
    more headroom."""
    assert _default_settings().max_new_tokens >= 8192


def test_budget_reserve_default_leaves_exit_margin() -> None:
    """The guard must stop STARTING tasks early enough that the in-flight task
    finishes and the process exits 0 before the harness kill."""
    reserve = _default_settings().budget_reserve_s
    assert 60.0 <= reserve <= 240.0


def test_empty_api_key_falls_back_instead_of_calling_fireworks() -> None:
    """ENV FIREWORKS_API_KEY="" (unsupplied build-arg) must act like no key."""
    cfg = Settings(_env_file=None, fireworks_api_key="")
    synth = CaptionSynthesizer(cfg)
    synth.load()

    transcript = Transcript(segments=[], language="en", duration=0.0)
    with pytest.raises(SynthesisError, match="not configured"):
        synth.generate_caption([], transcript, Style.FORMAL)
