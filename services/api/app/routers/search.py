"""/api/search — Track 3 Video-Oracle semantic search (stub; contract pinned)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas import SearchRequest

router = APIRouter()


@router.post("")
def search(body: SearchRequest) -> dict:
    """Semantic moment search. 501 until the Track 3 index (T086-T094) is built."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Track 3 Video-Oracle search is not implemented yet (see TASKS.md T086-T092).",
    )
