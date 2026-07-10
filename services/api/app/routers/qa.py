"""/api/qa — Track 3 Video-Oracle grounded RAG question-answering.

Serves the oracle index when it exists; otherwise answers the 501 stub the
frontend renders as an honest "not built yet" state.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings
from app.core.deps import get_settings
from app.routers.oracle_bridge import (
    get_chat,
    get_clip_encoder,
    get_embedder,
    hit_to_dict,
    load_index,
)
from app.schemas import QARequest

router = APIRouter()


@router.post("")
def qa(
    body: QARequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    """A grounded answer citing the moments it drew from (AC7.3)."""
    index = load_index(settings)  # raises the 501 stub before oracle imports are needed
    from oracle.qa import answer

    result = answer(
        body.question,
        index,
        get_embedder(request),
        get_chat(request),
        clip_encoder=get_clip_encoder(request),
    )
    return {
        "answer": result.answer,
        "citations": [hit_to_dict(hit) for hit in result.citations],
    }
