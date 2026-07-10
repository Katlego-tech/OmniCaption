"""/api/keys — Fireworks API key validation."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings
from app.core.deps import get_settings
from app.schemas import KeyValidationRequest

router = APIRouter()


class UpstreamError(RuntimeError):
    """Fireworks could not be reached or answered unexpectedly."""


def probe_fireworks_key(api_key: str, base_url: str) -> bool:
    """Check a key against the Fireworks models endpoint.

    Returns:
        True for an accepted key, False for a rejected (401/403) one.

    Raises:
        UpstreamError: On network failure or an unexpected upstream status.
    """
    try:
        resp = httpx.get(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise UpstreamError(str(exc)) from exc
    if resp.status_code == 200:
        return True
    if resp.status_code in (401, 403):
        return False
    raise UpstreamError(f"unexpected upstream status {resp.status_code}")


@router.post("/validate")
def validate_key(
    body: KeyValidationRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    """Report whether the supplied Fireworks key is accepted upstream."""
    try:
        valid = probe_fireworks_key(body.api_key, settings.fireworks_api_url)
    except UpstreamError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach Fireworks to validate the key: {exc}",
        ) from exc
    return {"valid": valid}
