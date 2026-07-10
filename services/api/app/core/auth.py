"""Authentication: a SQLite user store, PBKDF2 password hashing, and
HMAC-signed bearer tokens — all stdlib, no extra dependencies.

The token is a compact ``payload.signature`` pair (both base64url):
``payload`` is JSON ``{"uid", "email", "exp"}``; ``signature`` is
HMAC-SHA256 over the payload with the configured secret, compared in
constant time. This is a deliberately small, well-understood scheme for the
hackathon demo — not a full identity provider.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import sqlite3
import time

from app.core.config import Settings

_PBKDF2_ITERATIONS = 120_000
_SALT_BYTES = 16


class AuthError(Exception):
    """A recoverable auth failure (bad credentials, duplicate email, bad token)."""


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)


class AuthService:
    """User accounts + token issuance/verification for one API instance."""

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.auth_secret.encode("utf-8")
        self._ttl_s = settings.token_ttl_hours * 3600
        self._db_path = settings.auth_db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    salt BLOB NOT NULL,
                    pw_hash BLOB NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    # --- accounts ----------------------------------------------------------
    def create_user(self, email: str, password: str) -> int:
        """Create a user and return its id; raises AuthError on duplicate email."""
        email = email.strip().lower()
        salt = _random_salt()
        pw_hash = _hash_password(password, salt)
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "INSERT INTO users (email, salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
                    (email, salt, pw_hash, time.time()),
                )
                return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise AuthError("email already registered") from exc

    def verify_credentials(self, email: str, password: str) -> int:
        """Return the user id for valid credentials; raise AuthError otherwise."""
        email = email.strip().lower()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, salt, pw_hash FROM users WHERE email = ?", (email,)
            ).fetchone()
        if row is None:
            raise AuthError("invalid credentials")
        user_id, salt, pw_hash = row
        candidate = _hash_password(password, salt)
        if not hmac.compare_digest(candidate, pw_hash):
            raise AuthError("invalid credentials")
        return int(user_id)

    # --- tokens ------------------------------------------------------------
    def issue_token(self, user_id: int, email: str) -> str:
        """Mint a signed token carrying the user's identity and an expiry."""
        payload = {"uid": user_id, "email": email.strip().lower(), "exp": time.time() + self._ttl_s}
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = _b64url_encode(self._sign(payload_b64))
        return f"{payload_b64}.{signature}"

    def verify_token(self, token: str) -> dict:
        """Return the token payload if the signature and expiry are valid.

        Raises:
            AuthError: On a malformed, tampered, or expired token.
        """
        try:
            payload_b64, signature_b64 = token.split(".", 1)
        except ValueError as exc:
            raise AuthError("malformed token") from exc

        expected = self._sign(payload_b64)
        try:
            provided = _b64url_decode(signature_b64)
        except (binascii.Error, ValueError) as exc:
            raise AuthError("malformed token") from exc
        if not hmac.compare_digest(expected, provided):
            raise AuthError("bad signature")

        try:
            payload = json.loads(_b64url_decode(payload_b64))
        except (binascii.Error, ValueError, json.JSONDecodeError) as exc:
            raise AuthError("malformed token") from exc
        if float(payload.get("exp", 0)) < time.time():
            raise AuthError("token expired")
        return payload

    def _sign(self, payload_b64: str) -> bytes:
        return hmac.new(self._secret, payload_b64.encode("ascii"), hashlib.sha256).digest()


def _random_salt() -> bytes:
    # os.urandom is thread-safe and CSPRNG-backed.
    return os.urandom(_SALT_BYTES)
