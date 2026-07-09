"""Regenerate the golden fixtures for the T096 regression tests.

Run from ``services/captioner/`` after an INTENTIONAL change to the style
prompts, the tag instruction, or the fallback caption format:

    python tests/regression/regen_goldens.py

Commit the regenerated goldens in the same PR as the change so the diff shows
reviewers exactly how the tone-bearing text moved.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

import numpy as np  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.core.errors import fallback_caption  # noqa: E402
from app.core.schema import Style  # noqa: E402
from app.pipeline.synthesis import CaptionSynthesizer  # noqa: E402
from app.pipeline.vision import Keyframe  # noqa: E402

GOLDEN_DIR = Path(__file__).parents[1] / "fixtures" / "golden"


def main() -> None:
    """Write style_prompts.json and fallback_captions.json from the current code."""
    synth = CaptionSynthesizer(Settings(fireworks_api_key="golden_test_key"))
    synth.load()
    keyframes = [Keyframe(index=0, timestamp=0.0, image=np.zeros((8, 8, 3), dtype=np.uint8))]

    prompts = {
        style.value: synth._build_messages(keyframes, "irrelevant", style)[0]["content"]
        for style in Style
    }
    (GOLDEN_DIR / "style_prompts.json").write_text(
        json.dumps(prompts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    clips = json.loads((GOLDEN_DIR / "clips.json").read_text(encoding="utf-8"))
    fallbacks = {
        clip_id: fallback_caption(clip["transcript"], clip["keyframes"])
        for clip_id, clip in clips.items()
        if not clip_id.startswith("_")
    }
    fallbacks["no_evidence"] = fallback_caption(None, 0)
    (GOLDEN_DIR / "fallback_captions.json").write_text(
        json.dumps(fallbacks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"Wrote {GOLDEN_DIR / 'style_prompts.json'}")
    print(f"Wrote {GOLDEN_DIR / 'fallback_captions.json'}")


if __name__ == "__main__":
    main()
