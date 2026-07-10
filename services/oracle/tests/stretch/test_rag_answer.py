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


class _ReasoningChat:
    """A reasoning VLM: emits chain-of-thought, then a tagged final answer."""

    def __init__(self, reply: str) -> None:
        self._reply = reply
        self.system: str | None = None
        self.user: str | None = None

    def complete(self, system: str, user: str) -> str:
        self.system, self.user = system, user
        return self._reply


def test_answer_strips_reasoning_and_keeps_tagged_final(results_file: Path, embedder) -> None:
    """The model's chain-of-thought must never surface as the answer."""
    reply = (
        "Let me look at the evidence. The user asks about the chef. I should cite moments.\n"
        "I need to be careful not to invent anything.\n"
        "<answer>At [v1 @ 0.0s] a chef whisks eggs in a steel bowl.</answer>"
    )
    index = MomentIndex.build(moments_from_results(results_file), embedder)

    result = answer("What is the chef doing?", index, embedder, _ReasoningChat(reply))

    assert result.answer == "At [v1 @ 0.0s] a chef whisks eggs in a steel bowl."
    assert "Let me look at the evidence" not in result.answer


def test_answer_without_tags_falls_back_to_whole_content(results_file: Path, embedder) -> None:
    """A tag-less answer (e.g. a non-reasoning model) is passed through, trimmed."""
    index = MomentIndex.build(moments_from_results(results_file), embedder)

    result = answer(
        "What is the chef doing?",
        index,
        embedder,
        _ReasoningChat("  At [v1 @ 0.0s] a chef whisks eggs.  "),
    )

    assert result.answer == "At [v1 @ 0.0s] a chef whisks eggs."


def test_system_prompt_requests_answer_tag(results_file: Path, embedder, chat) -> None:
    index = MomentIndex.build(moments_from_results(results_file), embedder)
    answer("q?", index, embedder, chat)
    assert "<answer>" in chat.system


def test_chat_default_max_tokens_has_reasoning_headroom() -> None:
    """Truncation after chain-of-thought is what leaked reasoning; keep headroom."""
    from oracle.embeddings import FireworksChat

    assert FireworksChat(api_key="x")._max_tokens >= 4096
