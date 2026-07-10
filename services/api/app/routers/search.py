"""/api/search — Track 3 Video-Oracle semantic search.

Serves the oracle index when it exists; otherwise answers the 501 stub the
frontend renders as an honest "not built yet" state.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings
from app.core.deps import get_settings
from app.routers.oracle_bridge import get_clip_encoder, get_embedder, hit_to_dict, load_index
from app.schemas import SearchRequest

router = APIRouter()


@router.post("")
def search(
    body: SearchRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Similarity-ranked moments for a natural-language query (AC7.2)."""
    index = load_index(settings)
    embedder = get_embedder(request)
    clip_encoder = get_clip_encoder(request)
    hits = index.search(body.query, embedder, top_k=body.top_k, clip_encoder=clip_encoder)
    return {"query": body.query, "hits": [hit_to_dict(hit) for hit in hits]}
