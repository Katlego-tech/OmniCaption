"""/api/results — read-only view over the captioner's results.json."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings
from app.core.deps import get_settings

router = APIRouter()


def _read_results(settings: Settings) -> list[dict]:
    if not settings.results_path.is_file():
        return []
    with settings.results_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@router.get("")
def list_results(settings: Settings = Depends(get_settings)) -> list[dict]:
    """All clip results (empty until the pipeline has produced output)."""
    return _read_results(settings)


@router.get("/{task_id}")
def result_for_task(task_id: str, settings: Settings = Depends(get_settings)) -> dict:
    """Captions for one task_id; 404 if the pipeline has no result for it."""
    for clip in _read_results(settings):
        if clip.get("task_id") == task_id:
            return clip
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No result for task_id {task_id!r}.",
    )
