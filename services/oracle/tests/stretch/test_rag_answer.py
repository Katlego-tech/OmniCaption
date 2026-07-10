"""T088 / AC7.3 — questions yield grounded RAG answers citing moments."""

from __future__ import annotations

from pathlib import Path

from oracle.corpus import moments_from_results
from oracle.index import MomentIndex
from oracle.qa import answer


def test_answer_cites_retrieved_moments(results_file: Path, embedder, chat) -> None:
    index = MomentIndex.build(moments_from_results(results_file), embedder)
    result = answer("What is the chef doing with the eggs?", index, embedder, chat)

    assert result.answer
    assert result.citations, "grounded answers must carry citations"
    assert result.citations[0].moment.task_id == "v1"


def test_prompt_contains_only_retrieved_evidence(results_file: Path, embedder, chat) -> None:
    index = MomentIndex.build(moments_from_results(results_file), embedder)
    answer("What is the chef doing with the eggs?", index, embedder, chat, top_k=2)

    assert chat.user is not None
    assert "chef whisks eggs" in chat.user.lower()
    # The system prompt must pin grounding: no invention beyond the moments.
    assert chat.system is not None
    assert "only" in chat.system.lower()


def test_empty_index_answers_honestly_without_calling_the_model(embedder, chat) -> None:
    index = MomentIndex.build([], embedder)
    result = answer("anything at all?", index, embedder, chat)

    assert result.citations == []
    assert "no indexed" in result.answer.lower()
    assert chat.user is None, "the VLM must not be called with zero evidence"
