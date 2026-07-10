"""/api/media — serve video/keyframe files from the media directory."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import Settings
from app.core.deps import get_settings

router = APIRouter()


@router.get("/{filename:path}")
def get_media(filename: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    """Stream a file from the media dir; anything resolving outside it is a 404."""
    media_root = settings.media_dir.resolve()
    target = (media_root / filename).resolve()
    if not target.is_relative_to(media_root) or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return FileResponse(target)
