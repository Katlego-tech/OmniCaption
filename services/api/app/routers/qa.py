"""/api/qa — Track 3 Video-Oracle RAG question-answering (stub; contract pinned)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas import QARequest

router = APIRouter()


@router.post("")
def answer(body: QARequest) -> dict:
    """Grounded QA over indexed moments. 501 until Track 3 (T086-T094) is built."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Track 3 Video-Oracle QA is not implemented yet (see TASKS.md T093-T094).",
    )
