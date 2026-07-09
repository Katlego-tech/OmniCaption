"""Model loaders (Whisper STT; the VLM is a remote Fireworks API, no loader)."""

from app.models.loader import load_whisper

__all__ = ["load_whisper"]
