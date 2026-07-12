"""Application settings via ``pydantic-settings``.

All values are overridable through ``OMNICAPTION_*`` environment variables (see
``.env.example``). Defaults target the hackathon eval harness, which mounts
``/input`` and ``/output``.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the captioning pipeline."""

    model_config = SettingsConfigDict(
        env_prefix="OMNICAPTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- I/O paths (mounted by the eval harness) ---
    input_dir: Path = Field(
        default=Path("/input"),
        description="Directory containing tasks.json.",
    )
    output_dir: Path = Field(
        default=Path("/output"),
        description="Directory to write results.json.",
    )
    work_dir: Path = Field(
        default=Path("/tmp/omnicaption"),
        description="Scratch directory for downloaded videos and extracted audio.",
    )

    @property
    def tasks_path(self) -> Path:
        """Path to the input tasks manifest."""
        return self.input_dir / "tasks.json"

    @property
    def results_path(self) -> Path:
        """Path to the output results file."""
        return self.output_dir / "results.json"

    @property
    def transcripts_path(self) -> Path:
        """Path to the optional transcript sidecar consumed by the Track 3 oracle."""
        return self.output_dir / "transcripts.json"

    # --- Sidecars (Track 3 oracle enrichment; never part of the scored contract) ---
    emit_transcripts: bool = Field(
        default=True,
        description="Write /output/transcripts.json (timed segments) after the run.",
    )
    emit_keyframes: bool = Field(
        default=False,
        description="Also persist keyframe JPEGs under /output/keyframes/ (off: larger output).",
    )

    # --- Model identifiers ---
    whisper_model_size: str = Field(
        default="large-v3",
        description="faster-whisper model size/name (e.g. tiny, base, large-v3).",
    )
    whisper_compute_type: str = Field(
        default="float16",
        description="CTranslate2 compute type (float16, int8_float16, int8).",
    )
    # --- Fireworks AI API config ---
    fireworks_api_key: str | None = Field(
        default_factory=lambda: os.getenv("FIREWORKS_API_KEY"),
        description="Fireworks AI API key for remote model inference.",
    )
    fireworks_api_url: str = Field(
        default="https://api.fireworks.ai/inference/v1",
        description="Fireworks AI API base URL.",
    )
    fireworks_whisper_model: str = Field(
        default="whisper-v3",
        description="Fireworks AI Whisper model identifier.",
    )
    fireworks_vlm_model: str = Field(
        default="accounts/fireworks/models/kimi-k2p6",
        description="Fireworks AI Vision-Language Model identifier.",
    )

    # --- Vision ---
    keyframe_threshold: float = Field(
        default=30.0,
        description="Mean absolute pixel-variance threshold for scene-change detection.",
    )
    max_keyframes: int = Field(
        default=8,
        description="Cap on keyframes fed to the VLM (controls prompt size/latency).",
    )

    # --- Synthesis / generation ---
    max_new_tokens: int = Field(
        default=4096,
        description="Maximum tokens generated per caption (reasoning VLMs spend "
        "tokens on thinking before the tagged caption).",
    )
    synthesis_max_attempts: int = Field(
        default=3,
        description="Attempts per style before falling back. Retries escalate "
        "max_tokens (recovers truncated/leaked reasoning) and add a little "
        "temperature (breaks the VLM out of a repeated degenerate caption).",
    )
    # Fusion weights for the hybrid audio/vision evidence blend used in prompting.
    alpha: float = Field(default=0.6, description="Weight for transcript (audio) evidence.")
    beta: float = Field(default=0.4, description="Weight for keyframe (vision) evidence.")

    # --- GPU / ROCm ---
    gfx_arch: str | None = Field(
        default=None,
        description="Override gfx arch (e.g. gfx942). Auto-detected when unset.",
    )
    hsa_override_gfx_version: str | None = Field(
        default=None,
        description="Value for HSA_OVERRIDE_GFX_VERSION (e.g. 11.0.0 for RDNA3).",
    )

    # --- Timeouts / latency guards (seconds) ---
    download_timeout_s: float = Field(default=60.0, description="Per-video download timeout.")
    fireworks_timeout_s: float = Field(
        default=120.0,
        description="Per-request read timeout for the Fireworks VLM call. Reasoning "
        "VLMs can exceed 60s on slow networks; raise further if you see read timeouts.",
    )
    per_request_budget_s: float = Field(
        default=30.0,
        description="Soft per-task latency budget; used to log/guard slow tasks.",
    )
    total_runtime_budget_s: float = Field(
        default=600.0,
        description="Hard total runtime budget for the whole run (10 min).",
    )


def get_settings() -> Settings:
    """Construct a :class:`Settings` instance from the environment.

    Returns:
        A fully populated settings object.
    """
    return Settings()
