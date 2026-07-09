"""Central place for model ids and device placement.

The loader defers heavy imports (``faster_whisper``) to call time so the
package stays importable without the ML stack installed — required for
CI/style checks in the hackathon environment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import Settings
from app.core.gpu import select_device
from app.core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from faster_whisper import WhisperModel

logger = get_logger(__name__)


def load_whisper(cfg: Settings) -> WhisperModel:
    """Load a faster-whisper model on the best available device.

    Args:
        cfg: Application settings (model size, compute type).

    Returns:
        A ready-to-use ``faster_whisper.WhisperModel``.

    Raises:
        ImportError: If ``faster-whisper`` is not installed.
    """
    from faster_whisper import WhisperModel

    device = select_device()
    # CTranslate2 expects "cuda" (HIP presents as cuda under ROCm) or "cpu".
    ct2_device = "cuda" if device == "cuda" else "cpu"
    compute_type = cfg.whisper_compute_type if ct2_device == "cuda" else "int8"

    logger.info(
        "Loading Whisper '%s' on %s (compute=%s)",
        cfg.whisper_model_size,
        ct2_device,
        compute_type,
    )
    # Weights resolve from the HF cache baked into the image (HF_HOME layer in
    # the Dockerfile); with HF_HUB_OFFLINE=1 no network fetch happens at start.
    return WhisperModel(
        cfg.whisper_model_size,
        device=ct2_device,
        compute_type=compute_type,
    )
