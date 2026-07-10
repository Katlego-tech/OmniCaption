"""T087 / AC7.2 — natural-language queries return similarity-ranked moments."""

from __future__ import annotations

from pathlib import Path

from oracle.corpus import moments_from_results
from oracle.index import MomentIndex


def _index(results_file: Path, embedder) -> MomentIndex:
    return MomentIndex.build(moments_from_results(results_file), embedder)


def test_query_ranks_the_matching_moment_first(results_file: Path, embedder) -> None:
    index = _index(results_file, embedder)
    hits = index.search("cyclist on a coastal road", embedder, top_k=3)
    assert hits[0].moment.task_id == "v2"
    assert hits[0].score > 0


def test_scores_are_descending_and_top_k_respected(results_file: Path, embedder) -> None:
    index = _index(results_file, embedder)
    hits = index.search("eggs in a bowl", embedder, top_k=2)
    assert len(hits) == 2
    assert hits[0].score >= hits[1].score
    assert hits[0].moment.task_id == "v1"


def test_empty_index_returns_no_hits(embedder) -> None:
    index = MomentIndex.build([], embedder)
    assert index.search("anything", embedder, top_k=5) == []
