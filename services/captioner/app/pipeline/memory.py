"""Stage 3: VRAM reclamation between the audio and vision/synthesis models.

The pipeline loads models sequentially to fit within a single GPU's memory. After
Whisper transcription we aggressively release its memory before loading Gemma.
Every torch/GPU call is guarded so this is a no-op on CPU/ROCm-less hosts.
"""

from __future__ import annotations

import gc
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def free_model(obj: Any | None) -> None:
    """Drop references to a model so it becomes garbage-collectable.

    This does not itself free VRAM — call :func:`reclaim_vram` afterwards. It
    clears common heavy attributes to break reference cycles.

    Args:
        obj: A model (or wrapper) to release. ``None`` is ignored.
    """
    if obj is None:
        return
    for attr in ("model", "processor", "tokenizer"):
        if hasattr(obj, attr):
            try:
                setattr(obj, attr, None)
            except (AttributeError, TypeError):
                pass
    del obj


def reclaim_vram() -> None:
    """Force a full Python GC pass and empty the CUDA/HIP caching allocator.

    Safe to call on any host: torch import failure or CPU-only execution makes
    the GPU steps no-ops.
    """
    gc.collect()

    try:
        import torch
    except ImportError:
        logger.debug("torch not installed; skipped VRAM reclamation.")
        return

    if not torch.cuda.is_available():
        logger.debug("No CUDA/HIP device; skipped empty_cache().")
        return

    try:
        before = torch.cuda.memory_allocated()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        # ipc_collect is CUDA-specific and may be absent/no-op under ROCm.
        collect = getattr(torch.cuda, "ipc_collect", None)
        if callable(collect):
            collect()
        after = torch.cuda.memory_allocated()
        freed = before - after
        logger.info(
            "Reclaimed VRAM (gc + empty_cache). Current allocated: %.2f MB (freed: %.2f MB).",
            after / (1024 * 1024),
            freed / (1024 * 1024),
        )
    except (RuntimeError, AssertionError) as exc:
        logger.warning("VRAM reclamation partial failure: %s", exc)
