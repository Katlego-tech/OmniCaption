"""Grounded RAG question-answering over the moment index."""

from __future__ import annotations

from pydantic import BaseModel

from oracle.embeddings import ChatClient, Embedder
from oracle.index import MomentIndex, SearchHit

SYSTEM_PROMPT = (
    "You answer questions about a set of video clips. You may use ONLY the evidence "
    "moments provided — never invent people, places, dialogue, or events beyond them. "
    "Cite every claim with its moment reference in the form [task_id @ t]. If the "
    "evidence does not answer the question, say so plainly."
)


class Answer(BaseModel):
    """A grounded answer plus the moments it was allowed to draw from."""

    answer: str
    citations: list[SearchHit]


def _format_moment(hit: SearchHit) -> str:
    moment = hit.moment
    timestamp = f"{moment.t_start:.1f}s" if moment.t_start is not None else "0.0s"
    label = moment.style or moment.kind
    return f"[{moment.task_id} @ {timestamp}] ({label}) {moment.text}"


def answer(
    question: str,
    index: MomentIndex,
    embedder: Embedder,
    chat: ChatClient,
    top_k: int = 5,
) -> Answer:
    """Retrieve the most relevant moments and answer strictly from them.

    With an empty index the model is never called — there is nothing to ground
    an answer in, and an ungrounded answer would violate Non-negotiable I.
    """
    hits = index.search(question, embedder, top_k=top_k)
    if not hits:
        return Answer(
            answer="No indexed moments are available to answer from — build the index first.",
            citations=[],
        )

    evidence = "\n".join(_format_moment(hit) for hit in hits)
    user_prompt = f"Evidence moments:\n{evidence}\n\nQuestion: {question}"
    return Answer(answer=chat.complete(SYSTEM_PROMPT, user_prompt), citations=hits)
