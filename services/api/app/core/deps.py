"""Shared FastAPI dependencies, resolved from ``app.state``."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.auth import AuthError, AuthService
from app.core.config import Settings
from app.core.runner import PipelineRunner


def get_settings(request: Request) -> Settings:
    """The settings instance the app was created with."""
    return request.app.state.settings


def get_runner(request: Request) -> PipelineRunner:
    """The process-wide pipeline runner."""
    return request.app.state.runner


def get_auth(request: Request) -> AuthService:
    """The process-wide auth service."""
    return request.app.state.auth


def require_user(
    authorization: str | None = Header(default=None),
    auth: AuthService = Depends(get_auth),
) -> dict:
    """Resolve the caller's identity from the Authorization bearer token.

    Raises 401 when the header is missing/malformed or the token is invalid.
    Use as a dependency to gate any state-changing endpoint.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        return auth.verify_token(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
