"""/api/auth — signup, login, and the bearer-token identity check."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.auth import AuthError, AuthService
from app.core.deps import get_auth
from app.schemas import AuthResponse, Credentials

router = APIRouter()


def require_user(
    authorization: str | None = Header(default=None),
    auth: AuthService = Depends(get_auth),
) -> dict:
    """Resolve the caller's identity from the Authorization bearer token.

    Raises 401 when the header is missing, malformed, or the token is invalid.
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


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
def signup(body: Credentials, auth: AuthService = Depends(get_auth)) -> AuthResponse:
    """Register a new account and return a session token."""
    try:
        user_id = auth.create_user(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AuthResponse(email=body.email, token=auth.issue_token(user_id, body.email))


@router.post("/login", response_model=AuthResponse)
def login(body: Credentials, auth: AuthService = Depends(get_auth)) -> AuthResponse:
    """Authenticate and return a session token."""
    try:
        user_id = auth.verify_credentials(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from exc
    return AuthResponse(email=body.email, token=auth.issue_token(user_id, body.email))


@router.get("/me")
def me(user: dict = Depends(require_user)) -> dict:
    """Return the identity carried by the caller's token."""
    return {"email": user["email"]}
