"""CLIP visual space: keyframe moments index and cross-modal search.

Uses a fake CLIP encoder (filename-token based) — plumbing is tested for real,
pixels are not. The real encoder (oracle.clip_embed.OpenClipEncoder) is an
optional dependency exercised only in live runs.
"""

from __future__ import annotations

import math
import zlib
from pathlib import Path

import pytest

from oracle.corpus import moments_from_keyframes
from oracle.index import Moment, MomentIndex

DIMS = 32


def _token_vec(tokens: list[str]) -> list[float]:
    vec = [0.0] * DIMS
    for token in tokens:
        vec[zlib.crc32(token.encode()) % DIMS] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class FakeClipEncoder:
    """Embeds images by their filename tokens and text by its words — same space."""

    def embed_images(self, paths: list[str]) -> list[list[float]]:
        return [
            _token_vec(Path(p).stem.replace("_", " ").replace("-", " ").lower().split())
            for p in paths
        ]

    def embed_text(self, text: str) -> list[float]:
        return _token_vec(text.lower().split())


@pytest.fixture()
def keyframes_dir(tmp_path: Path) -> Path:
    root = tmp_path / "keyframes"
    (root / "v1").mkdir(parents=True)
    (root / "v2").mkdir(parents=True)
    (root / "v1" / "kf000_t0.0_chef_eggs.jpg").write_bytes(b"fake")
    (root / "v2" / "kf000_t3.5_bike_night.jpg").write_bytes(b"fake")
    return root


def test_keyframe_corpus_extracts_task_and_timestamp(keyframes_dir: Path) -> None:
    moments = moments_from_keyframes(keyframes_dir)
    assert len(moments) == 2
    by_task = {m.task_id: m for m in moments}
    assert by_task["v2"].space == "clip"
    assert by_task["v2"].kind == "keyframe"
    assert by_task["v2"].t_start == 3.5
    assert by_task["v2"].media and by_task["v2"].media.endswith(".jpg")


def test_index_embeds_clip_moments_with_the_clip_encoder(keyframes_dir: Path, embedder) -> None:
    clip = FakeClipEncoder()
    moments = moments_from_keyframes(keyframes_dir)
    index = MomentIndex.build(moments, embedder, clip_encoder=clip)
    assert all(m.vector for m in index.moments)
    assert embedder.calls == []  # text embedder untouched: all moments are clip-space


def test_cross_modal_search_ranks_the_matching_keyframe(keyframes_dir: Path, embedder) -> None:
    clip = FakeClipEncoder()
    text_moments = [
        Moment(task_id="v1", kind="caption", style="formal", text="a chef whisks eggs"),
    ]
    index = MomentIndex.build(
        text_moments + moments_from_keyframes(keyframes_dir), embedder, clip_encoder=clip
    )

    hits = index.search("bike night", embedder, clip_encoder=clip, top_k=3)
    assert hits[0].moment.task_id == "v2"
    assert hits[0].moment.space == "clip"


def test_clip_moments_are_skipped_without_a_clip_encoder(keyframes_dir: Path, embedder) -> None:
    # Build WITH clip (vectors exist), search WITHOUT it: clip moments must not
    # be scored against the text-space query vector.
    clip = FakeClipEncoder()
    index = MomentIndex.build(moments_from_keyframes(keyframes_dir), embedder, clip_encoder=clip)
    hits = index.search("bike night", embedder, top_k=5)
    assert hits == []


def test_old_text_only_index_files_still_load(results_file: Path, embedder, tmp_path) -> None:
    # Pre-CLIP index payloads had no space/media keys; loading must default them.
    from oracle.corpus import moments_from_results

    index = MomentIndex.build(moments_from_results(results_file), embedder)
    path = tmp_path / "index.json"
    index.save(path)

    import json

    stripped = [
        {k: v for k, v in item.items() if k not in ("space", "media")}
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]
    path.write_text(json.dumps(stripped), encoding="utf-8")

    reloaded = MomentIndex.load(path)
    assert all(m.space == "text" for m in reloaded.moments)
