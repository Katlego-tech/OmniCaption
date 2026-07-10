"""Pydantic models mirroring the captioner I/O contract (docs/16-io-contract.md).

Kept as a standalone copy: this service deploys without the captioner package
installed, so it must not import from ``services/captioner``.
"""

from __future__ import annotations

import ipaddress
import re
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

# task_id ends up in scratch/output filesystem paths downstream, so keep it to a
# safe, non-traversal charset.
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_BLOCKED_HOSTS = {"localhost", "metadata", "metadata.google.internal"}


class Style(StrEnum):
    """The four supported caption styles."""

    FORMAL = "formal"
    SARCASTIC = "sarcastic"
    HUMOROUS_TECH = "humorous_tech"
    HUMOROUS_NON_TECH = "humorous_non_tech"


class TaskIn(BaseModel):
    """A captioning request as submitted by the frontend."""

    task_id: str = Field(..., min_length=1, description="Unique clip identifier, e.g. 'v1'.")
    video_url: str = Field(..., description="Publicly downloadable http(s) video URL.")
    styles: list[Style] = Field(..., min_length=1, description="Requested caption styles.")

    @field_validator("task_id")
    @classmethod
    def _safe_task_id(cls, value: str) -> str:
        """Restrict to `[A-Za-z0-9_-]` — it becomes a filesystem path downstream."""
        if not _TASK_ID_RE.match(value):
            raise ValueError("task_id may contain only letters, digits, '-' and '_' (max 64)")
        return value

    @field_validator("video_url")
    @classmethod
    def _safe_video_url(cls, value: str) -> str:
        """Require an http(s) URL to a non-internal host (SSRF guard).

        Blocks non-http(s) schemes and any literal private/loopback/link-local/
        reserved IP or known internal hostname. NB: this does not resolve DNS,
        so a hostname that resolves to an internal address (DNS rebinding)
        remains a residual risk — egress filtering is the backstop.
        """
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("video_url must be an http(s) URL")
        host = parsed.hostname
        if not host:
            raise ValueError("video_url must include a host")
        if host.lower() in _BLOCKED_HOSTS:
            raise ValueError("video_url host is not allowed")
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            ip = None
        if ip is not None and (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError("video_url may not point to a private/internal address")
        return value

    @field_validator("styles", mode="before")
    @classmethod
    def _drop_unknown_and_dedupe(cls, value: Any) -> Any:
        """Drop unknown styles and duplicates, matching the pipeline's ingestion behavior."""
        if isinstance(value, list):
            seen: set[Style] = set()
            ordered: list[Style] = []
            for item in value:
                try:
                    style = item if isinstance(item, Style) else Style(item)
                except ValueError:
                    continue
                if style not in seen:
                    seen.add(style)
                    ordered.append(style)
            return ordered
        return value


class ClipResult(BaseModel):
    """Captions produced for one task: a style -> text mapping."""

    task_id: str = Field(..., min_length=1)
    captions: dict[Style, str] = Field(default_factory=dict)


class KeyValidationRequest(BaseModel):
    """Body for /api/keys/validate."""

    api_key: str = Field(..., min_length=1, description="Fireworks AI API key to check.")


class SearchRequest(BaseModel):
    """Body for /api/search (Track 3 contract, pinned ahead of implementation)."""

    query: str = Field(..., min_length=1, description="Natural-language moment query.")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of moments to return.")


class QARequest(BaseModel):
    """Body for /api/qa (Track 3 contract, pinned ahead of implementation)."""

    question: str = Field(..., min_length=1, description="Question over the indexed corpus.")


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    """Body for /api/auth/signup and /api/auth/login."""

    email: str = Field(..., description="Account email address.")
    password: str = Field(..., min_length=8, max_length=200, description="Account password.")

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise ValueError("invalid email address")
        return value


class AuthResponse(BaseModel):
    """Response for a successful signup/login/verify."""

    email: str
    token: str


class VerifyRequest(BaseModel):
    """Body for /api/auth/verify."""

    token: str = Field(..., min_length=1, description="Email-verification token.")


def resolve_host_is_internal(host: str) -> bool:
    """True if ``host`` resolves to any private/loopback/link-local/reserved IP.

    Fail-open (returns False) on resolution errors — an unresolvable host is left
    for the pipeline's own fetch + egress policy to handle. This narrows, but does
    not fully close, DNS-rebinding: an address that flips between this check and
    the later fetch still slips through, so egress filtering remains the backstop.
    """
    import socket

    try:
        infos = socket.getaddrinfo(host, None)
    except (OSError, UnicodeError):
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False
