"""/api/tasks — manage the captioner input manifest and trigger runs."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.config import Settings
from app.core.deps import get_runner, get_settings, require_user
from app.core.runner import PipelineRunner
from app.schemas import TaskIn, resolve_host_is_internal

router = APIRouter()


def _read_manifest(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_manifest_atomically(path: Path, tasks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
        os.replace(tmp_name, path)
    except BaseException:
        os.unlink(tmp_name)
        raise


@router.get("")
def list_tasks(settings: Settings = Depends(get_settings)) -> list[dict]:
    """All tasks currently in the manifest (empty until something is submitted)."""
    return _read_manifest(settings.tasks_path)


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_tasks(
    body: list[TaskIn] | TaskIn,
    settings: Settings = Depends(get_settings),
    _user: dict = Depends(require_user),
) -> list[dict]:
    """Validate task(s) and merge them into the manifest (same task_id replaces)."""
    submitted = [body] if isinstance(body, TaskIn) else body

    if settings.ssrf_resolve_dns:
        for task in submitted:
            host = urlparse(task.video_url).hostname
            if host and resolve_host_is_internal(host):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="video_url host resolves to an internal address.",
                )

    incoming = [task.model_dump(mode="json") for task in submitted]

    manifest = _read_manifest(settings.tasks_path)
    by_id = {task["task_id"]: task for task in incoming}
    merged = [by_id.pop(task["task_id"], task) for task in manifest]
    merged.extend(by_id.values())

    _write_manifest_atomically(settings.tasks_path, merged)
    return incoming


@router.delete("")
def clear_tasks(
    settings: Settings = Depends(get_settings),
    _user: dict = Depends(require_user),
) -> Response:
    """Remove every task from the manifest."""
    _write_manifest_atomically(settings.tasks_path, [])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    settings: Settings = Depends(get_settings),
    _user: dict = Depends(require_user),
) -> Response:
    """Remove one task by id; 404 if it is not in the manifest."""
    manifest = _read_manifest(settings.tasks_path)
    remaining = [task for task in manifest if task.get("task_id") != task_id]
    if len(remaining) == len(manifest):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No task with id {task_id!r}.",
        )
    _write_manifest_atomically(settings.tasks_path, remaining)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_run(
    settings: Settings = Depends(get_settings),
    runner: PipelineRunner = Depends(get_runner),
    _user: dict = Depends(require_user),
) -> dict:
    """Launch the pipeline; 409 while a run is already in flight."""
    settings.input_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    if not runner.start(settings.run_command()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pipeline run is already in progress.",
        )
    return runner.status()


@router.get("/run")
def run_status(runner: PipelineRunner = Depends(get_runner)) -> dict:
    """Current pipeline run state: idle, running, succeeded, or failed."""
    return runner.status()
