"""End-to-end pipeline smoke test with all heavy stages mocked."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.core.config import Settings
from app.core.schema import ResultsOutput, Style, Task
from app.pipeline import orchestrator as orch
from app.pipeline.audio import Segment, Transcript, Word
from app.pipeline.vision import Keyframe


def _fake_transcript() -> Transcript:
    return Transcript(
        language="en",
        duration=2.0,
        segments=[
            Segment(0.0, 2.0, "a cat sits", words=[Word(0.0, 0.5, "a cat sits")]),
        ],
    )


@pytest.mark.integration
def test_pipeline_smoke(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    """Orchestrator produces a schema-valid result for a fake task."""
    # Stage 1: fake ingestion (no real download / ffmpeg).
    monkeypatch.setattr(
        orch.ingestion,
        "download_video",
        lambda *a, **k: Path("fake.mp4"),
    )
    monkeypatch.setattr(
        orch.ingestion,
        "extract_audio",
        lambda *a, **k: Path("fake.wav"),
    )

    # Stages 2/3: fake transcription (patched on the orchestrator instance).
    monkeypatch.setattr(orch.CaptionPipeline, "_transcribe", lambda self, wav: _fake_transcript())

    # Stage 4: fake keyframes.
    dummy = np.zeros((2, 2, 3), dtype=np.uint8)
    monkeypatch.setattr(
        orch,
        "extract_keyframes",
        lambda *a, **k: [Keyframe(0, 0.0, dummy)],
    )
    monkeypatch.setattr(orch, "align_to_transcript", lambda kfs, t: kfs)

    # Stage 5: fake synthesis.
    monkeypatch.setattr(orch.CaptionSynthesizer, "load", lambda self: None)
    monkeypatch.setattr(
        orch.CaptionSynthesizer,
        "generate_for_styles",
        lambda self, kfs, transcript, styles: {s: f"[{s.value}] caption" for s in styles},
    )

    task = Task(
        task_id="v1",
        video_url="https://example.com/clip.mp4",
        styles=[Style.FORMAL, Style.SARCASTIC],
    )

    pipeline = orch.CaptionPipeline(settings)
    results = pipeline.run([task])
    pipeline.close()

    # Must validate against the output schema and contain every requested style.
    doc = ResultsOutput(root=results)
    assert len(doc) == 1
    clip = doc.root[0]
    assert clip.task_id == "v1"
    assert clip.has_all([Style.FORMAL, Style.SARCASTIC])
    assert clip.captions[Style.FORMAL] == "[formal] caption"
