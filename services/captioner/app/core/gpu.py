"""AMD GPU / ROCm detection and environment configuration.

Supports the hackathon target matrix::

    MI300X       gfx942
    RX 7900 XTX  gfx1100
    RX 6600      gfx1032
    Ryzen AI     gfx1103 / gfx1150

Honors ``PYTORCH_ROCM_ARCH`` and ``HSA_OVERRIDE_GFX_VERSION`` so a single image
runs across consumer RDNA and datacenter CDNA parts.
"""

from __future__ import annotations

import os
import subprocess

from app.core.logging import get_logger

logger = get_logger(__name__)

# Map gfx arch -> the HSA_OVERRIDE_GFX_VERSION string ROCm expects for it.
# Consumer parts frequently need an override to borrow a supported LLVM target.
_GFX_TO_HSA_OVERRIDE: dict[str, str] = {
    "gfx942": "9.4.2",  # MI300X (CDNA3)
    "gfx1100": "11.0.0",  # RX 7900 XTX (RDNA3)
    "gfx1032": "10.3.0",  # RX 6600 (RDNA2) — borrow gfx1030 target
    "gfx1103": "11.0.0",  # Ryzen AI (RDNA3 iGPU)
    "gfx1150": "11.5.0",  # Ryzen AI (RDNA3.5 iGPU)
}


def detect_gfx_arch() -> str | None:
    """Best-effort detection of the active AMD gfx architecture.

    Resolution order:
        1. ``PYTORCH_ROCM_ARCH`` environment variable (first arch if a list).
        2. ``rocminfo`` output parsing.
        3. ``None`` if neither is available (CPU / non-ROCm host).

    Returns:
        A gfx arch string such as ``"gfx942"``, or ``None``.
    """
    env_arch = os.environ.get("PYTORCH_ROCM_ARCH")
    if env_arch:
        arch = env_arch.split(";")[0].split(",")[0].strip()
        if arch:
            logger.info("gfx arch from PYTORCH_ROCM_ARCH: %s", arch)
            return arch

    try:
        proc = subprocess.run(
            ["rocminfo"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        logger.info("rocminfo unavailable (%s); assuming non-ROCm host.", exc)
        return None

    for line in proc.stdout.splitlines():
        token = line.strip()
        if "gfx" in token and "Name:" in token:
            # e.g. "  Name:                    gfx942"
            candidate = token.split()[-1]
            if candidate.startswith("gfx"):
                logger.info("gfx arch from rocminfo: %s", candidate)
                return candidate
    return None


def configure_rocm_env(
    gfx_arch: str | None = None,
    hsa_override: str | None = None,
) -> dict[str, str]:
    """Set ROCm-related environment variables for the current process.

    Must be called *before* importing torch so HIP picks up the overrides.

    Args:
        gfx_arch: Explicit gfx arch; auto-detected when ``None``.
        hsa_override: Explicit ``HSA_OVERRIDE_GFX_VERSION``; derived from the
            arch map when ``None``.

    Returns:
        A dict of the environment variables that were set.
    """
    applied: dict[str, str] = {}

    arch = gfx_arch or detect_gfx_arch()
    if arch:
        os.environ.setdefault("PYTORCH_ROCM_ARCH", arch)
        applied["PYTORCH_ROCM_ARCH"] = os.environ["PYTORCH_ROCM_ARCH"]

    override = hsa_override or (_GFX_TO_HSA_OVERRIDE.get(arch) if arch else None)
    if override:
        os.environ.setdefault("HSA_OVERRIDE_GFX_VERSION", override)
        applied["HSA_OVERRIDE_GFX_VERSION"] = os.environ["HSA_OVERRIDE_GFX_VERSION"]

    if applied:
        logger.info("Configured ROCm env: %s", applied)
    else:
        logger.info("No AMD GPU detected; running in CPU-fallback mode.")
    return applied


def select_device() -> str:
    """Return the torch device string to use.

    Returns:
        ``"cuda"`` when a ROCm/CUDA device is visible to torch (HIP presents as
        the ``cuda`` device in PyTorch-ROCm), otherwise ``"cpu"``.
    """
    try:
        import torch  # local import: torch may be a heavy/optional dependency
    except ImportError:
        return "cpu"

    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def query_vram_gb() -> float | None:
    """Query total VRAM of the active device in GiB, with fallbacks.

    Returns:
        Total device memory in GiB, or ``None`` if it cannot be determined.
    """
    try:
        import torch
    except ImportError:
        return None

    if not torch.cuda.is_available():
        return None

    try:
        props = torch.cuda.get_device_properties(0)
        return round(props.total_memory / (1024**3), 2)
    except (RuntimeError, AssertionError) as exc:
        logger.warning("VRAM query failed: %s", exc)
        return None


def assert_amd(enforced: bool = False) -> None:
    """Assert that an AMD device is active.

    Fails loudly if enforced is True and no HIP-enabled device is visible.

    Args:
        enforced: If True, raise RuntimeError if AMD device is missing.
    """
    device = select_device()
    logger.info("Active device: %s", device)

    arch = detect_gfx_arch()
    if arch:
        logger.info("ROCm gfx arch detected: %s", arch)

    vram = query_vram_gb()
    if vram:
        logger.info("ROCm HIP device total memory: %.2f GiB", vram)

    if enforced and device != "cuda":
        raise RuntimeError(
            "AMD GPU / ROCm compute is enforced, but no active HIP/CUDA device is visible!"
        )
