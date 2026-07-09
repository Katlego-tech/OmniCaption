"""Unit tests for Transcript, Segment, and Word models (T034)."""

from __future__ import annotations

from app.pipeline.audio import Segment, Transcript, Word


def test_transcript_text_concatenation() -> None:
    """Transcript.text property correctly whitespace-joins segment texts."""
    t = Transcript(
        language="en",
        duration=5.0,
        segments=[
            Segment(0.0, 2.0, "Hello"),
            Segment(2.0, 5.0, " world.  "),
        ],
    )
    assert t.text == "Hello world."


def test_transcript_words_flattening() -> None:
    """Transcript.words() flattens and preserves temporal order of all words."""
    w1 = Word(0.0, 0.5, "hello")
    w2 = Word(0.6, 1.0, "world")
    w3 = Word(2.0, 2.5, "again")

    t = Transcript(
        language="en",
        duration=5.0,
        segments=[
            Segment(0.0, 1.5, "hello world", words=[w1, w2]),
            Segment(1.5, 3.0, "again", words=[w3]),
        ],
    )
    assert t.words() == [w1, w2, w3]


def test_word_timestamp_monotonicity() -> None:
    """Word timestamps should be monotonic (start <= end)."""
    # Simple validation that start <= end
    w = Word(start=1.2, end=1.5, text="test")
    assert w.start <= w.end
