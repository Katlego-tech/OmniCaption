"""Typed pipeline errors and deterministic fallback helpers."""

from __future__ import annotations


class PipelineError(Exception):
    """Base exception for all OmniCaption pipeline failures."""


class IngestionError(PipelineError):
    """Raised when video ingestion or download fails."""


class AudioExtractionError(PipelineError):
    """Raised when audio extraction (ffmpeg) fails."""


class TranscriptionError(PipelineError):
    """Raised when audio transcription (Whisper) fails."""


class SynthesisError(PipelineError):
    """Raised when VLM caption synthesis fails."""


def fallback_caption(transcript_text: str | None = None, keyframes_count: int = 0) -> str:
    """Generate a deterministic fallback caption based on available evidence.

    Args:
        transcript_text: Text from the audio transcript, if available.
        keyframes_count: Number of extracted keyframes, if available.

    Returns:
        A grounded, deterministic fallback caption string.
    """
    evidence: list[str] = []
    if transcript_text and transcript_text.strip():
        tx = transcript_text.strip()
        # Simple deterministic truncation
        if len(tx) > 100:
            tx = tx[:97] + "..."
        evidence.append(f"Audio mentions '{tx}'")
    if keyframes_count > 0:
        evidence.append(f"Visual event showing {keyframes_count} keyframe(s)")

    if not evidence:
        return "Video content processed with no speech or visual variance."

    return "[Fallback] " + " and ".join(evidence) + "."
