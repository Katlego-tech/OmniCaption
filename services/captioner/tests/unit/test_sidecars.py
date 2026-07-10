"""Sidecar outputs: transcripts.json (oracle contract) + optional keyframe JPEGs.

Sidecars enrich the Track 3 oracle index; they must never jeopardize the main
results.json contract, so writers are best-effort and independently gated.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.core.config import Settings
from app.pipeline.audio import Segment, Transcript, Word
from app.pipeline.sidecars import write_keyframe_sidecar, write_transcript_sidecar
from app.pipeline.vision import Keyframe


def _transcript() -> Transcript:
    return Transcript(
        language="en",
        duration=4.2,
        segments=[
            Segment(start=0.0, end=2.0, text="hello there", words=[Word(0.0, 0.5, "hello")]),
            Segment(start=2.0, end=4.2, text="general kenobi", words=[]),
        ],
    )


def test_transcript_sidecar_matches_oracle_contract(tmp_path: Path) -> None:
    path = tmp_path / "transcripts.json"
    write_transcript_sidecar({"v1": _transcript()}, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {
        "v1": [
            {"text": "hello there", "t_start": 0.0, "t_end": 2.0},
            {"text": "general kenobi", "t_start": 2.0, "t_end": 4.2},
        ]
    }


def test_transcript_sidecar_skips_empty_segments(tmp_path: Path) -> None:
    path = tmp_path / "transcripts.json"
    empty = Transcript(language="en", duration=0.0, segments=[])
    write_transcript_sidecar({"v1": empty, "v2": _transcript()}, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "v1" not in data
    assert len(data["v2"]) == 2


def test_keyframe_sidecar_writes_timestamped_jpegs(tmp_path: Path) -> None:
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    keyframes = [
        Keyframe(index=0, timestamp=0.0, image=frame),
        Keyframe(index=12, timestamp=1.5, image=frame),
    ]
    written = write_keyframe_sidecar("v1", keyframes, tmp_path / "keyframes")

    assert len(written) == 2
    assert all(p.is_file() and p.suffix == ".jpg" for p in written)
    assert written[1].parent.name == "v1"
    assert "t1.5" in written[1].name


def test_settings_defaults_transcripts_on_keyframes_off() -> None:
    cfg = Settings(_env_file=None)
    assert cfg.emit_transcripts is True
    assert cfg.emit_keyframes is False
    assert cfg.transcripts_path.name == "transcripts.json"
