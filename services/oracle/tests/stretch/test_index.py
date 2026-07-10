"""T086 / AC7.1 — the multimodal vector index builds over captioner evidence."""

from __future__ import annotations

from pathlib import Path

from oracle.corpus import moments_from_results
from oracle.index import MomentIndex


def test_corpus_extracts_one_moment_per_caption(results_file: Path) -> None:
    moments = moments_from_results(results_file)
    assert len(moments) == 3  # v1 formal + v1 sarcastic + v2 formal
    assert {m.task_id for m in moments} == {"v1", "v2"}
    assert all(m.kind == "caption" and m.text for m in moments)


def test_index_builds_and_embeds_every_moment(results_file: Path, embedder) -> None:
    moments = moments_from_results(results_file)
    index = MomentIndex.build(moments, embedder)
    assert len(index) == 3
    assert all(m.vector for m in index.moments)
    # All texts embedded in a single batched call.
    assert len(embedder.calls) == 1


def test_index_persists_and_reloads(results_file: Path, embedder, tmp_path: Path) -> None:
    index = MomentIndex.build(moments_from_results(results_file), embedder)
    path = tmp_path / "index.json"
    index.save(path)

    reloaded = MomentIndex.load(path)
    assert len(reloaded) == len(index)
    assert reloaded.moments[0].text == index.moments[0].text
    assert reloaded.moments[0].vector == index.moments[0].vector
