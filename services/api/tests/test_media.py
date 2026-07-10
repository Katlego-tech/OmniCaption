"""GET /api/media/{filename} — serve files from the media dir, traversal-safe."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_serves_existing_file(client: TestClient, settings) -> None:
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    (settings.media_dir / "clip.mp4").write_bytes(b"fake-video-bytes")

    resp = client.get("/api/media/clip.mp4")
    assert resp.status_code == 200
    assert resp.content == b"fake-video-bytes"


def test_missing_file_is_404(client: TestClient) -> None:
    assert client.get("/api/media/nope.mp4").status_code == 404


def test_path_traversal_is_blocked(client: TestClient, settings) -> None:
    # A secret outside the media dir must not be reachable via encoded traversal.
    (settings.data_dir / "secret.txt").write_text("s3cret", encoding="utf-8")
    resp = client.get("/api/media/..%2Fsecret.txt")
    assert resp.status_code in (400, 404)
    assert b"s3cret" not in resp.content
