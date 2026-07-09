"""Tests for video downloader."""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from app.core.errors import IngestionError
from app.pipeline.ingestion import download_video


def test_download_video_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """download_video successfully downloads a file to dest_dir."""
    url = "https://example.com/clip.mp4"
    task_id = "v1"

    class MockResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield b"fake video content"

    def mock_get(url_arg, **kwargs):
        assert url_arg == url
        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    dest_file = download_video(url, tmp_path, task_id=task_id)
    assert dest_file == tmp_path / "v1_clip.mp4"
    assert dest_file.exists()
    assert dest_file.read_bytes() == b"fake video content"


def test_download_video_http_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """download_video raises IngestionError on HTTP errors."""
    url = "https://example.com/clip.mp4"

    def mock_get(url_arg, **kwargs):
        raise requests.HTTPError("404 Client Error")

    monkeypatch.setattr(requests, "get", mock_get)

    with pytest.raises(IngestionError) as exc_info:
        download_video(url, tmp_path, task_id="v1")

    assert "failed" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()


def test_download_video_connection_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """download_video raises IngestionError on connection failure."""
    url = "https://example.com/clip.mp4"

    def mock_get(url_arg, **kwargs):
        raise requests.ConnectionError("Connection refused")

    monkeypatch.setattr(requests, "get", mock_get)

    with pytest.raises(IngestionError) as exc_info:
        download_video(url, tmp_path, task_id="v1")

    assert "connection" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()
