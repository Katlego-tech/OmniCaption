"""Central place for model ids, quantization config, and device placement.

Both loaders defer heavy imports (``faster_whisper``, ``torch``,
``transformers``) to call time so the package stays importable without the ML
stack installed — required for CI/style checks in the hackathon environment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
    # TODO(hackathon): point download_root at the baked-in model cache to keep
    # cold start under the 60s budget (see Dockerfile model-cache layer).
    return WhisperModel(
        cfg.whisper_model_size,
        device=ct2_device,
        compute_type=compute_type,
    )


def _build_quantization_config(cfg: Settings) -> Any | None:
    """Build a bitsandbytes 4-bit config, or ``None`` if unavailable/disabled.

    Args:
        cfg: Application settings.

    Returns:
        A ``transformers.BitsAndBytesConfig`` or ``None`` for full-precision.
    """
    if not cfg.load_in_4bit:
        return None
    try:
        import torch
        from transformers import BitsAndBytesConfig
    except ImportError:
        logger.warning("Quantization backend unavailable; falling back to fp16/bf16.")
        return None

    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )


def load_gemma_vlm(cfg: Settings) -> tuple[Any, Any]:
    """Load the Gemma 4 E4B-it vision-language model and its processor.

    Args:
        cfg: Application settings (model id, quantization).

    Returns:
        A ``(model, processor)`` tuple.

    Raises:
        ImportError: If ``transformers`` is not installed.
    """
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    quant_config = _build_quantization_config(cfg)
    device = select_device()
    dtype = torch.bfloat16 if device == "cuda" else torch.float32

    logger.info(
        "Loading Gemma VLM '%s' (4bit=%s, device=%s)",
        cfg.gemma_model_id,
        quant_config is not None,
        device,
    )
    # TODO(hackathon): ensure weights are baked into the image layer / HF cache
    # so no network fetch happens at container start (startup <60s constraint).
    processor = AutoProcessor.from_pretrained(cfg.gemma_model_id)
    model = AutoModelForImageTextToText.from_pretrained(
        cfg.gemma_model_id,
        quantization_config=quant_config,
        torch_dtype=dtype,
        device_map="auto" if device == "cuda" else None,
    )
    model.eval()
    return model, processor
