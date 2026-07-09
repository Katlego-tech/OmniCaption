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

import requests

from app.core.config import Settings
from app.core.errors import TranscriptionError
from app.core.logging import get_logger

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
    """Lifecycle wrapper around the Fireworks Whisper API."""

    def __init__(self, cfg: Settings) -> None:
        """Store config; defer initialization to :meth:`load`.

        Args:
            cfg: Application settings.
        """
        self._cfg = cfg
        self.model: Any | None = None

    def load(self) -> None:
        """Initialize the transcriber (idempotent)."""
        if self.model is None:
            self.model = True

    def transcribe(self, wav: Path) -> Transcript:
        """Transcribe a WAV file into a :class:`Transcript` using Fireworks Whisper API.

        Args:
            wav: Path to a mono 16 kHz WAV file.

        Returns:
            The transcription with segment- and word-level timestamps.

        Raises:
            RuntimeError: If called before :meth:`load`.
            TranscriptionError: If the API call fails.
        """
        if self.model is None:
            raise RuntimeError("WhisperTranscriber.transcribe() called before load().")

        logger.info("Transcribing %s via Fireworks AI API", wav)

        if not self._cfg.fireworks_api_key:
            raise TranscriptionError("Fireworks API key is not configured. Cannot transcribe.")

        url = f"{self._cfg.fireworks_api_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self._cfg.fireworks_api_key}",
        }

        try:
            with open(wav, "rb") as f:
                files = {"file": (wav.name, f, "audio/wav")}
                data_list = [
                    ("model", self._cfg.fireworks_whisper_model),
                    ("response_format", "verbose_json"),
                    ("timestamp_granularities[]", "word"),
                    ("timestamp_granularities[]", "segment"),
                ]
                response = requests.post(
                    url, headers=headers, files=files, data=data_list, timeout=15.0
                )
        except Exception as exc:
            raise TranscriptionError(
                f"HTTP request to Fireworks Whisper API failed: {exc}"
            ) from exc

        if response.status_code != 200:
            raise TranscriptionError(
                f"Fireworks Whisper API failed with status {response.status_code}: {response.text}"
            )

        try:
            res_json = response.json()
        except Exception as exc:
            raise TranscriptionError(
                f"Failed to parse Fireworks Whisper API response JSON: {exc}"
            ) from exc

        raw_segments = res_json.get("segments", [])
        segments: list[Segment] = []
        for seg in raw_segments:
            words_list = seg.get("words", [])
            words = []
            if words_list:
                for w in words_list:
                    words.append(
                        Word(
                            start=float(w.get("start", 0.0)),
                            end=float(w.get("end", 0.0)),
                            text=str(w.get("word", "")),
                            probability=float(w.get("probability", 1.0)),
                        )
                    )
            else:
                # Interpolation fallback: split segment text and distribute duration
                seg_text = seg.get("text", "").strip()
                seg_words = seg_text.split()
                if seg_words:
                    start_val = float(seg.get("start", 0.0))
                    end_val = float(seg.get("end", 0.0))
                    duration = end_val - start_val
                    word_dur = duration / len(seg_words)
                    for i, w_text in enumerate(seg_words):
                        words.append(
                            Word(
                                start=start_val + i * word_dur,
                                end=start_val + (i + 1) * word_dur,
                                text=w_text,
                                probability=1.0,
                            )
                        )

            segments.append(
                Segment(
                    start=float(seg.get("start", 0.0)),
                    end=float(seg.get("end", 0.0)),
                    text=seg.get("text", ""),
                    words=words,
                )
            )

        transcript = Transcript(
            language=res_json.get("language", "en"),
            duration=float(res_json.get("duration", 0.0)),
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
        """Drop the transcriber reference."""
        self.model = None
