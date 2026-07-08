"""Stage 2: audio transcription with faster-whisper (word-level timestamps).

Defines lightweight dataclasses for the transcript so downstream stages don't
depend on faster-whisper's internal types, and a :class:`WhisperTranscriber`
wrapper with explicit ``load``/``transcribe``/``unload`` lifecycle for the
sequential memory model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.loader import load_whisper

logger = get_logger(__name__)


@dataclass(slots=True)
class Word:
    """A single transcribed word with its time span."""

    start: float
    end: float
    text: str
    probability: float = 1.0


@dataclass(slots=True)
class Segment:
    """A transcript segment (sentence/utterance) with contained words."""

    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)


@dataclass(slots=True)
class Transcript:
    """Full transcription result for one clip."""

    language: str
    duration: float
    segments: list[Segment] = field(default_factory=list)

    @property
    def text(self) -> str:
        """The full transcript as a single whitespace-joined string."""
        return " ".join(seg.text.strip() for seg in self.segments).strip()

    def words(self) -> list[Word]:
        """Flatten all words across segments in temporal order."""
        return [word for seg in self.segments for word in seg.words]


class WhisperTranscriber:
    """Lifecycle wrapper around a faster-whisper model."""

    def __init__(self, cfg: Settings) -> None:
        """Store config; defer heavy model loading to :meth:`load`.

        Args:
            cfg: Application settings.
        """
        self._cfg = cfg
        self.model: Any | None = None

    def load(self) -> None:
        """Load the underlying Whisper model (idempotent)."""
        if self.model is None:
            self.model = load_whisper(self._cfg)

    def transcribe(self, wav: Path) -> Transcript:
        """Transcribe a WAV file into a :class:`Transcript`.

        Args:
            wav: Path to a mono 16 kHz WAV file.

        Returns:
            The transcription with segment- and word-level timestamps.

        Raises:
            RuntimeError: If called before :meth:`load`.
        """
        if self.model is None:
            raise RuntimeError("WhisperTranscriber.transcribe() called before load().")

        logger.info("Transcribing %s", wav)
        # faster-whisper returns a generator of segments plus an info object.
        raw_segments, info = self.model.transcribe(
            str(wav),
            word_timestamps=True,
            vad_filter=True,
        )

        segments: list[Segment] = []
        for seg in raw_segments:
            words = [
                Word(
                    start=float(w.start),
                    end=float(w.end),
                    text=w.word,
                    probability=float(getattr(w, "probability", 1.0)),
                )
                for w in (seg.words or [])
            ]
            segments.append(
                Segment(
                    start=float(seg.start),
                    end=float(seg.end),
                    text=seg.text,
                    words=words,
                )
            )

        transcript = Transcript(
            language=getattr(info, "language", "en"),
            duration=float(getattr(info, "duration", 0.0)),
            segments=segments,
        )
        logger.info(
            "Transcribed %d segments (%.1fs, lang=%s)",
            len(segments),
            transcript.duration,
            transcript.language,
        )
        return transcript

    def unload(self) -> None:
        """Drop the model reference so its VRAM can be reclaimed.

        The caller is responsible for invoking
        :func:`app.pipeline.memory.reclaim_vram` afterwards.
        """
        self.model = None
