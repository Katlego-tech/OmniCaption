"""Shared FastAPI dependencies, resolved from ``app.state``."""

from __future__ import annotations

from fastapi import Request

from app.core.config import Settings
from app.core.runner import PipelineRunner


def get_settings(request: Request) -> Settings:
    """The settings instance the app was created with."""
    return request.app.state.settings


def get_runner(request: Request) -> PipelineRunner:
    """The process-wide pipeline runner."""
    return request.app.state.runner
