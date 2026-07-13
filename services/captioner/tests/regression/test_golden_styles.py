"""Golden-clip regression tests (T096): pin the tone-bearing surfaces.

Tone and fidelity live in exactly three deterministic places: the per-style
system prompts (persona + output-tag rules), the prompt-assembly shape
(images -> transcript), and the deterministic fallback caption text. These
tests pin all three, byte-for-byte, against golden fixtures over frozen
v1/v2/v3 evidence — an accidental edit anywhere fails loudly, and a deliberate
tone change requires regenerating the goldens in the same PR.

Regenerate after an intentional change:

    python tests/regression/regen_goldens.py

An opt-in live test (real Fireworks call) checks structural invariants of the
actual model output; it is skipped unless both ``FIREWORKS_API_KEY`` and
``OMNICAPTION_LIVE_TESTS=1`` are set, so CI and local runs never spend tokens
by accident.
"""

from __future__ import annotations

import json
import os
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

from app.core.config import Settings
from app.core.errors import fallback_caption, is_fallback_caption
from app.core.schema import Style
from app.pipeline.audio import Segment, Transcript
from app.pipeline.synthesis import CaptionSynthesizer
from app.pipeline.vision import Keyframe

GOLDEN_DIR = Path(__file__).parents[1] / "fixtures" / "golden"

ALL_STYLES = [Style.FORMAL, Style.SARCASTIC, Style.HUMOROUS_TECH, Style.HUMOROUS_NON_TECH]


def _load_golden(name: str) -> dict:
    path = GOLDEN_DIR / name
    assert path.exists(), (
        f"Golden file missing: {path}. Run tests/regression/regen_goldens.py to create it."
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _clips() -> dict[str, dict]:
    clips = _load_golden("clips.json")
    return {k: v for k, v in clips.items() if not k.startswith("_")}


def _keyframes(count: int) -> list[Keyframe]:
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    return [Keyframe(index=i, timestamp=float(i), image=img) for i in range(count)]


@pytest.fixture
def synth() -> CaptionSynthesizer:
    cfg = Settings(fireworks_api_key="golden_test_key")
    s = CaptionSynthesizer(cfg)
    s.load()
    return s


# --- 1. System prompts: byte-for-byte persona + tag rules ------------------------


@pytest.mark.regression
def test_system_prompts_match_golden(synth: CaptionSynthesizer) -> None:
    """The assembled system prompt for each style equals the golden exactly."""
    golden = _load_golden("style_prompts.json")
    for style in ALL_STYLES:
        messages = synth._build_messages(_keyframes(1), "irrelevant", style)
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == golden[style.value], (
            f"System prompt for style '{style.value}' drifted from the golden. If the change "
            "is intentional, regenerate via tests/regression/regen_goldens.py in the same PR."
        )


@pytest.mark.regression
def test_style_personas_are_distinct() -> None:
    """No two style prompts collapse into each other (tone separation holds)."""
    golden = _load_golden("style_prompts.json")
    assert set(golden) == {s.value for s in ALL_STYLES}
    for a, b in combinations(ALL_STYLES, 2):
        assert golden[a.value] != golden[b.value], f"{a.value} and {b.value} share a prompt"


# --- 2. Prompt assembly shape over the frozen v1/v2/v3 evidence ------------------


@pytest.mark.regression
def test_prompt_assembly_shape_per_clip(synth: CaptionSynthesizer) -> None:
    """One stitched grid image + its layout note first, then the transcript block."""
    for clip_id, clip in _clips().items():
        messages = synth._build_messages(
            _keyframes(clip["keyframes"]), clip["transcript"], Style.FORMAL
        )
        user_parts = messages[1]["content"]
        image_parts = [p for p in user_parts if p["type"] == "image_url"]
        text_parts = [p for p in user_parts if p["type"] == "text"]

        n_images = 1 if clip["keyframes"] else 0
        assert len(image_parts) == n_images, clip_id
        if n_images:
            grid_note = text_parts[0]["text"]
            assert f"grid of {clip['keyframes']} keyframes" in grid_note, clip_id
        assert user_parts[-1]["type"] == "text", f"{clip_id}: transcript must come last"

        expected_block = clip["transcript"].strip() or "(no speech detected)"
        assert text_parts[-1]["text"] == f"Transcript:\n{expected_block}", clip_id


# --- 3. Deterministic fallback captions over the frozen evidence -----------------


@pytest.mark.regression
def test_fallback_captions_match_golden() -> None:
    """The deterministic fallback for each frozen clip equals the golden exactly."""
    golden = _load_golden("fallback_captions.json")
    for clip_id, clip in _clips().items():
        produced = fallback_caption(clip["transcript"], clip["keyframes"])
        assert produced == golden[clip_id], (
            f"Fallback caption for '{clip_id}' drifted from the golden. If intentional, "
            "regenerate via tests/regression/regen_goldens.py in the same PR."
        )
    # No-evidence case: the last-resort string is part of the contract too.
    assert fallback_caption(None, 0) == golden["no_evidence"]


@pytest.mark.regression
def test_fallback_is_deterministic() -> None:
    """Same evidence in, same caption out — every time."""
    for clip in _clips().values():
        first = fallback_caption(clip["transcript"], clip["keyframes"])
        second = fallback_caption(clip["transcript"], clip["keyframes"])
        assert first == second


# --- 4. Opt-in live golden run (real Fireworks call; costs tokens) ---------------


@pytest.mark.golden_live
@pytest.mark.skipif(
    not (os.getenv("FIREWORKS_API_KEY") and os.getenv("OMNICAPTION_LIVE_TESTS") == "1"),
    reason="live golden run needs FIREWORKS_API_KEY and OMNICAPTION_LIVE_TESTS=1",
)
def test_live_styles_structural_invariants() -> None:
    """All four live captions are present, distinct, and free of scaffolding leaks."""
    cfg = Settings()
    synth = CaptionSynthesizer(cfg)
    synth.load()

    # A non-trivial synthetic frame (gradient) so the VLM has real pixels to describe.
    gradient = np.tile(np.arange(256, dtype=np.uint8), (256, 1))
    image = np.stack([gradient, gradient.T, np.flipud(gradient)], axis=-1)
    keyframes = [Keyframe(index=0, timestamp=0.0, image=image)]

    clip = _clips()["v1"]
    transcript = Transcript(
        language="en",
        duration=8.0,
        segments=[Segment(start=0.0, end=8.0, text=clip["transcript"])],
    )
    captions = synth.generate_for_styles(keyframes, transcript, ALL_STYLES)
    # generate_for_styles never raises; a fallback caption here means the API call failed.

    assert set(captions) == set(ALL_STYLES)
    for style, caption in captions.items():
        assert caption.strip(), f"{style.value}: empty caption"
        assert "<captionStyle>" not in caption, f"{style.value}: tag leaked into caption"
        assert not is_fallback_caption(caption), f"{style.value}: API call failed"
    for a, b in combinations(ALL_STYLES, 2):
        assert captions[a] != captions[b], f"{a.value} and {b.value} produced identical captions"
