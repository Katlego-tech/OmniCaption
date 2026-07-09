"""Unit tests for memory reclamation (T036)."""

from __future__ import annotations

import gc

import pytest

from app.pipeline.memory import free_model, reclaim_vram


class DummyModelWrapper:
    def __init__(self) -> None:
        self.model = "heavy_model"
        self.processor = "heavy_processor"
        self.tokenizer = "heavy_tokenizer"


def test_free_model_nulls_attributes() -> None:
    """free_model nulls out model, processor, and tokenizer attributes."""
    wrapper = DummyModelWrapper()
    assert wrapper.model == "heavy_model"

    free_model(wrapper)

    assert wrapper.model is None
    assert wrapper.processor is None
    assert wrapper.tokenizer is None


def test_reclaim_vram_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """reclaim_vram executes gc.collect and does not throw even if torch is mocked or absent."""
    collected = False

    def mock_collect():
        nonlocal collected
        collected = True
        return 0

    monkeypatch.setattr(gc, "collect", mock_collect)

    # Calling reclaim_vram should run successfully
    reclaim_vram()
    assert collected is True
