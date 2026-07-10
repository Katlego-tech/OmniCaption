"""/api/auth — signup, login, email verification, logout, and identity.

Auth attempts are rate-limited per client IP. On success a token is returned in
the body (for cross-origin header clients) *and* set as an httpOnly ``session``
cookie (XSS-safe for same-site/HTTPS clients).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.auth import AuthError, AuthService
from app.core.config import Settings
from app.core.deps import get_auth, get_limiter, get_mailer, get_settings, require_user
from app.core.mailer import DevMailer
from app.core.ratelimit import RateLimiter
from app.schemas import AuthResponse, Credentials, VerifyRequest

router = APIRouter()


def _rate_limit(request: Request, limiter: RateLimiter) -> None:
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(f"auth:{client}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts; slow down and try again shortly.",
        )


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        "session",
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.token_ttl_hours * 3600,
        path="/",
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(
    body: Credentials,
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
    mailer: DevMailer = Depends(get_mailer),
) -> dict:
    """Register an account.

    Verification-required mode returns an identical generic 202 whether or not
    the email already exists (no account-existence oracle). Otherwise a new
    account is logged in immediately and a duplicate returns 409.
    """
    _rate_limit(request, limiter)
    user_id, verification_token = auth.create_user(body.email, body.password)

    if settings.require_verification:
        if user_id is not None and verification_token is not None:
            mailer.send_verification(body.email, verification_token)
        response.status_code = status.HTTP_202_ACCEPTED
        return {"status": "verification_required", "email": body.email}

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")
    token = auth.issue_token(user_id, body.email)
    _set_session_cookie(response, token, settings)
    return AuthResponse(email=body.email, token=token).model_dump()


@router.post("/login", response_model=AuthResponse)
def login(
    body: Credentials,
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> AuthResponse:
    """Authenticate and return a session token (+ httpOnly cookie)."""
    _rate_limit(request, limiter)
    try:
        user_id = auth.verify_credentials(body.email, body.password)
    except AuthError as exc:
        # "email not verified" only surfaces after the password matches, so it
        # is not an enumeration oracle; everything else is a generic 401.
        if str(exc) == "email not verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified."
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
        ) from exc
    token = auth.issue_token(user_id, body.email)
    _set_session_cookie(response, token, settings)
    return AuthResponse(email=body.email, token=token)


@router.post("/verify", response_model=AuthResponse)
def verify(
    body: VerifyRequest,
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> AuthResponse:
    """Consume an email-verification token and start a session."""
    _rate_limit(request, limiter)
    verified = auth.verify_email(body.token)
    if verified is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token."
        )
    user_id, email = verified
    token = auth.issue_token(user_id, email)
    _set_session_cookie(response, token, settings)
    return AuthResponse(email=email, token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    user: dict = Depends(require_user),
    auth: AuthService = Depends(get_auth),
) -> Response:
    """Revoke every outstanding token for the caller and clear the cookie."""
    auth.revoke_all(int(user["uid"]))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie("session", path="/")
    return response


@router.get("/me")
def me(user: dict = Depends(require_user)) -> dict:
    """Return the identity carried by the caller's token/cookie."""
    return {"email": user["email"]}
