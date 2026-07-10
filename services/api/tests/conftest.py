"""Shared fixtures: isolated data dir + a TestClient wired to it."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    """Settings pointing every path at a throwaway temp directory."""
    return Settings(
        data_dir=tmp_path,
        # A no-op command so /api/tasks/run never touches Docker in tests.
        captioner_cmd=f'"{sys.executable}" -c "print(42)"',
        _env_file=None,
    )


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    """TestClient against an app built from the isolated settings."""
    return TestClient(create_app(settings))
