"""AuthService schema migration: an auth.db created by an older build (before the
email-verification columns existed) must be upgraded in place, not left broken.

Regression for the ``sqlite3.OperationalError: table users has no column named
verified`` seen on signup against a pre-verification database.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.auth import AuthService
from app.core.config import Settings
from app.main import create_app

# The original shipped schema — before verified / verification_token / token_version.
_LEGACY_SCHEMA = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        salt BLOB NOT NULL,
        pw_hash BLOB NOT NULL,
        created_at REAL NOT NULL
    )
"""

_NEW_COLUMNS = {"verified", "verification_token", "token_version"}


def _seed_legacy_db(data_dir: Path, *, with_row: bool = False) -> Path:
    """Write an old-schema auth.db under ``data_dir`` and return its path."""
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "auth.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(_LEGACY_SCHEMA)
        if with_row:
            conn.execute(
                "INSERT INTO users (email, salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
                ("legacy@example.com", b"\x01" * 16, b"\x02" * 32, time.time()),
            )
    return db_path


def _columns(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        return {row[1] for row in conn.execute("PRAGMA table_info(users)")}


def test_init_adds_missing_columns_to_legacy_db(tmp_path: Path) -> None:
    db_path = _seed_legacy_db(tmp_path)
    assert not _NEW_COLUMNS & _columns(db_path)  # precondition: legacy schema

    AuthService(Settings(data_dir=tmp_path, _env_file=None))

    assert _NEW_COLUMNS <= _columns(db_path)


def test_legacy_rows_default_to_verified(tmp_path: Path) -> None:
    """Accounts that predate verification must not be locked out by the migration."""
    db_path = _seed_legacy_db(tmp_path, with_row=True)

    AuthService(Settings(data_dir=tmp_path, _env_file=None))

    with sqlite3.connect(db_path) as conn:
        verified, tv = conn.execute(
            "SELECT verified, token_version FROM users WHERE email = ?",
            ("legacy@example.com",),
        ).fetchone()
    assert verified == 1
    assert tv == 0


def test_signup_succeeds_against_migrated_legacy_db(tmp_path: Path) -> None:
    _seed_legacy_db(tmp_path)
    client = TestClient(
        create_app(Settings(data_dir=tmp_path, ssrf_resolve_dns=False, _env_file=None))
    )

    resp = client.post(
        "/api/auth/signup", json={"email": "new@example.com", "password": "password-123"}
    )

    assert resp.status_code == 201
    assert resp.json()["token"]
