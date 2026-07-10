"""Shared FastAPI dependencies, resolved from ``app.state``."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.auth import AuthError, AuthService
from app.core.config import Settings
from app.core.mailer import DevMailer
from app.core.ratelimit import RateLimiter
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


def get_limiter(request: Request) -> RateLimiter:
    """The process-wide auth rate limiter."""
    return request.app.state.limiter


def get_mailer(request: Request) -> DevMailer:
    """The process-wide verification mailer."""
    return request.app.state.mailer


def require_user(
    request: Request,
    authorization: str | None = Header(default=None),
    auth: AuthService = Depends(get_auth),
) -> dict:
    """Resolve the caller's identity from the bearer token or session cookie.

    Accepts an ``Authorization: Bearer`` header (cross-origin clients) or an
    httpOnly ``session`` cookie (XSS-safe). Raises 401 when neither is present
    or the token is invalid/revoked.
    """
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    else:
        token = request.cookies.get("session", "")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return auth.verify_token(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
