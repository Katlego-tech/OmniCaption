"""Stage 1: ingestion — download videos and extract mono 16 kHz WAV audio.

Audio extraction shells out to ``ffmpeg`` (present in the ROCm image) rather
than binding a Python decoder, matching the hackathon reference approach.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from app.core.errors import AudioExtractionError, IngestionError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Whisper expects 16 kHz mono PCM.
_TARGET_SAMPLE_RATE = 16_000
_TARGET_CHANNELS = 1
_DOWNLOAD_CHUNK = 1 << 20  # 1 MiB
# ffmpeg on a judged UHD clip finishes in seconds; a hang must not eat the
# whole runtime budget (the hard-exit guard is the backstop, not the plan).
_FFMPEG_TIMEOUT_S = 120.0
_FFMPEG_SILENT_TIMEOUT_S = 30.0


def _safe_stem(url: str, fallback: str) -> str:
    """Derive a filesystem-safe stem from a URL path."""
    name = Path(urlparse(url).path).stem
    return name or fallback


def download_video(
    url: str,
    dest_dir: Path,
    timeout_s: float = 60.0,
    task_id: str = "clip",
) -> Path:
    """Download a video to ``dest_dir``.

    Args:
        url: Publicly downloadable video URL.
        dest_dir: Directory to write the file into (created if missing).
        timeout_s: Bounds BOTH the socket operations and the total elapsed
            download time. requests' ``timeout`` alone only limits gaps
            between bytes, so a slow-but-steady stream was otherwise unbounded.
        task_id: Used to build a stable, unique filename.

    Returns:
        Path to the downloaded video file.

    Raises:
        requests.RequestException: On network/HTTP failure.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(urlparse(url).path).suffix or ".mp4"
    out_path = dest_dir / f"{task_id}_{_safe_stem(url, task_id)}{suffix}"

    if out_path.exists() and out_path.stat().st_size > 0:
        logger.info("Video already cached at %s, skipping download.", out_path)
        return out_path

    logger.info("Downloading %s -> %s", url, out_path)
    started = time.monotonic()
    try:
        with requests.get(url, stream=True, timeout=timeout_s) as resp:
            resp.raise_for_status()
            with out_path.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=_DOWNLOAD_CHUNK):
                    if time.monotonic() - started > timeout_s:
                        raise IngestionError(
                            f"Download exceeded the {timeout_s:.0f}s total cap: {url}"
                        )
                    if chunk:
                        fh.write(chunk)
    except IngestionError:
        out_path.unlink(missing_ok=True)  # never leave a partial file "cached"
        raise
    except requests.RequestException as exc:
        logger.error("Download failed for URL %s: %s", url, exc)
        raise IngestionError(f"Download failed: {exc}") from exc

    logger.info("Downloaded %.2f MiB", out_path.stat().st_size / (1024**2))
    return out_path


def extract_audio(video: Path, dest_dir: Path | None = None) -> Path:
    """Extract mono 16 kHz PCM WAV audio from a video via ffmpeg.

    Args:
        video: Path to the source video.
        dest_dir: Output directory; defaults to the video's directory.

    Returns:
        Path to the extracted ``.wav`` file.

    Raises:
        FileNotFoundError: If ``ffmpeg`` is not on PATH.
        subprocess.CalledProcessError: If ffmpeg exits non-zero.
    """
    out_dir = dest_dir or video.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / f"{video.stem}.wav"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-vn",  # drop video
        "-ac",
        str(_TARGET_CHANNELS),
        "-ar",
        str(_TARGET_SAMPLE_RATE),
        "-acodec",
        "pcm_s16le",
        str(wav_path),
    ]
    logger.info("Extracting audio: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=_FFMPEG_TIMEOUT_S)
    except subprocess.TimeoutExpired as exc:
        logger.error("ffmpeg timed out after %.0fs on %s", _FFMPEG_TIMEOUT_S, video)
        raise AudioExtractionError(f"ffmpeg timed out after {_FFMPEG_TIMEOUT_S:.0f}s.") from exc
    except FileNotFoundError as exc:
        logger.error("ffmpeg command not found on PATH: %s", exc)
        raise AudioExtractionError("ffmpeg is not installed or not on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        if "does not contain any stream" in exc.stderr:
            logger.warning("Video has no audio stream. Generating 1-second silent wav.")
            silent_cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=16000:cl=mono",
                "-t",
                "1",
                "-acodec",
                "pcm_s16le",
                str(wav_path),
            ]
            try:
                subprocess.run(
                    silent_cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=_FFMPEG_SILENT_TIMEOUT_S,
                )
                return wav_path
            except Exception as silent_exc:
                logger.error("Failed to generate silent wav: %s", silent_exc)
        logger.error("ffmpeg failed with exit code %d: %s", exc.returncode, exc.stderr)
        raise AudioExtractionError(f"ffmpeg failed: {exc.stderr.strip()}") from exc
    return wav_path
