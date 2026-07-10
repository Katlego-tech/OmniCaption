"""Shared glue between the API and the optional Track 3 oracle package.

The oracle is a separate service (services/oracle) and may not be installed in
every deployment; everything here degrades to the 501 stub behavior when it is
absent or its index has not been built.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.config import Settings

STUB_DETAIL = (
    "Track 3 Video-Oracle is not available: {reason}. Build the index with "
    "`python -m oracle.cli build` into <DATA_DIR>/oracle/index.json (see services/oracle)."
)


def load_index(settings: Settings) -> Any:
    """Load the moment index, or raise the 501 the frontend knows how to render."""
    try:
        from oracle.index import MomentIndex
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=STUB_DETAIL.format(reason="the oracle package is not installed"),
        ) from exc
    if not settings.oracle_index_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=STUB_DETAIL.format(reason="no index has been built yet"),
        )
    return MomentIndex.load(settings.oracle_index_path)


def get_embedder(request: Request) -> Any:
    """The injected embedder (tests), or a Fireworks one from the request/env key."""
    injected = getattr(request.app.state, "oracle_embedder", None)
    if injected is not None:
        return injected
    from oracle.embeddings import FireworksEmbeddings

    return FireworksEmbeddings(_require_key(request))


def get_chat(request: Request) -> Any:
    """The injected chat client (tests), or a Fireworks one from the request/env key."""
    injected = getattr(request.app.state, "oracle_chat", None)
    if injected is not None:
        return injected
    from oracle.embeddings import FireworksChat

    return FireworksChat(_require_key(request))


def _require_key(request: Request) -> str:
    api_key = request.headers.get("X-Fireworks-Key") or os.environ.get("FIREWORKS_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A Fireworks key is required: send X-Fireworks-Key or set FIREWORKS_API_KEY.",
        )
    return api_key


def hit_to_dict(hit: Any) -> dict:
    """Flatten a SearchHit for the wire."""
    moment = hit.moment
    return {
        "task_id": moment.task_id,
        "kind": moment.kind,
        "style": moment.style,
        "text": moment.text,
        "t_start": moment.t_start,
        "t_end": moment.t_end,
        "score": round(hit.score, 4),
    }
