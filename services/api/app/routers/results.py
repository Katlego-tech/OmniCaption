"""/api/results — read-only view over the captioner's results.json."""

from __future__ import annotations

import json
import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.config import Settings
from app.core.deps import get_settings

router = APIRouter()


def _read_results(settings: Settings) -> list[dict]:
    if not settings.results_path.is_file():
        return []
    with settings.results_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_results(settings: Settings, results: list[dict]) -> None:
    path = settings.results_path
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        os.replace(tmp_name, path)
    except BaseException:
        os.unlink(tmp_name)
        raise


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


@router.delete("")
def clear_results(settings: Settings = Depends(get_settings)) -> Response:
    """Delete all generated captions (no-op if none exist)."""
    if settings.results_path.is_file():
        _write_results(settings, [])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{task_id}")
def delete_result(task_id: str, settings: Settings = Depends(get_settings)) -> Response:
    """Delete one clip's captions by task_id; 404 if absent."""
    results = _read_results(settings)
    remaining = [clip for clip in results if clip.get("task_id") != task_id]
    if len(remaining) == len(results):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No result for task_id {task_id!r}.",
        )
    _write_results(settings, remaining)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
