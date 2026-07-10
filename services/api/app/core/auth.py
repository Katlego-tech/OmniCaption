"""Authentication: a SQLite user store, PBKDF2 password hashing, and
HMAC-signed bearer tokens — all stdlib, no extra dependencies.

The token is a compact ``payload.signature`` pair (both base64url):
``payload`` is JSON ``{"uid", "email", "tv", "exp"}`` (``tv`` = token version,
for revocation); ``signature`` is HMAC-SHA256 over the payload, compared in
constant time. Deliberately small and well-understood for the hackathon — not
a full identity provider.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import time

from app.core.config import Settings

logger = logging.getLogger(__name__)

# OWASP 2023 floor for PBKDF2-HMAC-SHA256.
_PBKDF2_ITERATIONS = 600_000
_SALT_BYTES = 16
# A fixed salt used only to burn a comparable amount of time for unknown users,
# so login latency does not reveal whether an email is registered.
_DUMMY_SALT = b"\x00" * _SALT_BYTES


class AuthError(Exception):
    """A recoverable auth failure (bad credentials, bad token, unverified)."""


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)


class AuthService:
    """User accounts + token issuance/verification/revocation for one instance."""

    def __init__(self, settings: Settings) -> None:
        self._secret = _resolve_secret(settings)
        self._ttl_s = settings.token_ttl_hours * 3600
        self._require_verification = settings.require_verification
        self._db_path = settings.auth_db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    # Columns added after the original release, with the DDL to backfill them onto
    # a pre-existing table. Applied in order so an older auth.db upgrades in place
    # instead of failing at the first INSERT (CREATE TABLE IF NOT EXISTS never adds
    # columns to a table that already exists). Defaults keep legacy accounts usable:
    # they are treated as verified (predating verification) at token version 0.
    _COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
        ("verified", "ALTER TABLE users ADD COLUMN verified INTEGER NOT NULL DEFAULT 1"),
        ("verification_token", "ALTER TABLE users ADD COLUMN verification_token TEXT"),
        ("token_version", "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"),
    )

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    salt BLOB NOT NULL,
                    pw_hash BLOB NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 1,
                    verification_token TEXT,
                    token_version INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                )
                """
            )
            existing = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
            for column, ddl in self._COLUMN_MIGRATIONS:
                if column not in existing:
                    conn.execute(ddl)

    # --- accounts ----------------------------------------------------------
    def create_user(self, email: str, password: str) -> tuple[int | None, str | None]:
        """Create a user.

        Returns ``(user_id, verification_token)`` for a new account, or
        ``(None, None)`` if the email already exists — the caller returns an
        identical response either way so signup does not leak account existence.
        The verification token is non-None only when verification is required.
        """
        email = email.strip().lower()
        salt = _random_salt()
        pw_hash = _hash_password(password, salt)
        verified = 0 if self._require_verification else 1
        token = secrets.token_urlsafe(32) if self._require_verification else None
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "INSERT INTO users (email, salt, pw_hash, verified, verification_token, "
                    "created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (email, salt, pw_hash, verified, token, time.time()),
                )
                return int(cur.lastrowid), token
        except sqlite3.IntegrityError:
            return None, None

    def verify_email(self, token: str) -> tuple[int, str] | None:
        """Consume a verification token; return ``(user_id, email)`` or None."""
        if not token:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, email FROM users WHERE verification_token = ?", (token,)
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE users SET verified = 1, verification_token = NULL WHERE id = ?",
                (row[0],),
            )
            return int(row[0]), str(row[1])

    def verify_credentials(self, email: str, password: str) -> int:
        """Return the user id for valid, verified credentials; raise otherwise.

        Runs the KDF even for unknown emails so response time does not reveal
        which emails are registered.
        """
        email = email.strip().lower()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, salt, pw_hash, verified FROM users WHERE email = ?", (email,)
            ).fetchone()
        if row is None:
            _hash_password(password, _DUMMY_SALT)  # equalize timing, then fail
            raise AuthError("invalid credentials")
        user_id, salt, pw_hash, verified = row
        candidate = _hash_password(password, salt)
        if not hmac.compare_digest(candidate, pw_hash):
            raise AuthError("invalid credentials")
        if not verified:
            raise AuthError("email not verified")
        return int(user_id)

    def revoke_all(self, user_id: int) -> None:
        """Invalidate every outstanding token for a user (logout-everywhere)."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET token_version = token_version + 1 WHERE id = ?", (user_id,)
            )

    def _token_version(self, user_id: int) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT token_version FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return None if row is None else int(row[0])

    # --- tokens ------------------------------------------------------------
    def issue_token(self, user_id: int, email: str) -> str:
        """Mint a signed token carrying identity, token version, and expiry."""
        payload = {
            "uid": user_id,
            "email": email.strip().lower(),
            "tv": self._token_version(user_id) or 0,
            "exp": time.time() + self._ttl_s,
        }
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = _b64url_encode(self._sign(payload_b64))
        return f"{payload_b64}.{signature}"

    def verify_token(self, token: str) -> dict:
        """Return the token payload if signature, expiry, and version are valid.

        Raises:
            AuthError: On a malformed, tampered, expired, or revoked token.
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

        current_tv = self._token_version(int(payload.get("uid", -1)))
        if current_tv is None or int(payload.get("tv", -1)) != current_tv:
            raise AuthError("token revoked")
        return payload

    def _sign(self, payload_b64: str) -> bytes:
        return hmac.new(self._secret, payload_b64.encode("ascii"), hashlib.sha256).digest()


def _random_salt() -> bytes:
    # os.urandom is thread-safe and CSPRNG-backed.
    return os.urandom(_SALT_BYTES)


def _resolve_secret(settings: Settings) -> bytes:
    """The token-signing key.

    Priority: an explicit ``AUTH_SECRET`` (production / multi-instance), else a
    random 256-bit secret generated once and persisted under DATA_DIR. This
    guarantees the signing key is never the source's well-known default, so
    tokens cannot be forged from the public code.
    """
    explicit = settings.auth_secret.strip()
    if explicit:
        return explicit.encode("utf-8")

    key_path = settings.data_dir / "auth_secret.key"
    if key_path.is_file():
        return key_path.read_bytes()

    secret = os.urandom(32)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(secret)
    try:
        os.chmod(key_path, 0o600)
    except OSError:  # pragma: no cover - non-POSIX perms are best-effort
        pass
    logger.warning(
        "AUTH_SECRET not set; generated a random signing key at %s. "
        "Set AUTH_SECRET explicitly for multi-instance deployments.",
        key_path,
    )
    return secret
