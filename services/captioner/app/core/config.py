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
    keyframe_grid: bool = Field(
        default=True,
        description="Send keyframes as ONE timestamp-labeled grid image instead "
        "of N separate payloads: ~80% smaller upload, one visual pass, and "
        "explicit chronology for the VLM. Set 0 for the legacy per-frame "
        "payload.",
    )

    # --- Synthesis / generation ---
    max_new_tokens: int = Field(
        default=8192,
        description="Maximum tokens generated per caption (reasoning VLMs spend "
        "tokens on thinking before the tagged caption). 4096 truncated real "
        "reasoning output mid-thought (finish_reason='length'), costing a full "
        "retry; 8192 clears the common case on the first attempt.",
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

    # --- Throughput ---
    task_concurrency: int = Field(
        default=4,
        description="Tasks processed concurrently. Synthesis is a remote API "
        "call and downloads are I/O-bound, so tasks overlap almost fully; "
        "Whisper (the only local model) is serialized behind a lock. "
        "Sequential processing of ~12 hidden clips at 1.5-3 min each cannot "
        "fit the 600 s budget — every clip past the cutoff scores zero.",
    )

    # --- Timeouts / latency guards (seconds) ---
    download_timeout_s: float = Field(
        default=180.0,
        description="Per-video download timeout. The judged clips are 1440p-4K "
        "MP4s; a real run lost every caption when a 4K download hit the old 60 s "
        "default, so keep generous headroom (the total-runtime guard still bounds "
        "the batch).",
    )
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
    budget_reserve_s: float = Field(
        default=120.0,
        description="Stop STARTING new tasks once elapsed exceeds "
        "total_runtime_budget_s minus this reserve, so the in-flight task can "
        "finish and the process exits 0 before the harness kills the container "
        "(a killed container exits non-zero and writes nothing further).",
    )
    hard_exit_reserve_s: float = Field(
        default=30.0,
        description="Absolute wall-clock guard: force-exit 0 at "
        "total_runtime_budget_s minus this reserve even mid-task. The "
        "between-task budget_reserve_s guard cannot bound a task already in "
        "flight (download + ffmpeg + Whisper + UHD decode + synthesis retries "
        "can together exceed the whole budget), and a judge-side kill is "
        "scored TIMEOUT regardless of the valid results.json on disk — the "
        "process must exit first.",
    )


def get_settings() -> Settings:
    """Construct a :class:`Settings` instance from the environment.

    Returns:
        A fully populated settings object.
    """
    return Settings()
