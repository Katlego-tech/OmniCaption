"""API settings via ``pydantic-settings``.

Environment names follow the deployment contract in
``docs/18-frontend-architecture.md`` §6 (``CORS_ORIGINS``, ``DATA_DIR``,
``CAPTIONER_IMAGE``) — unprefixed, unlike the captioner's ``OMNICAPTION_*``
namespace, because this service is deployed standalone with its own env.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the backend API service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed frontend origins.",
    )
    data_dir: Path = Field(
        default=Path("./data"),
        description="Root data dir; holds input/, output/ and media/ subdirectories.",
    )
    captioner_image: str = Field(
        default="omnicaption-captioner:latest",
        description="Captioner container image used by the default run command.",
    )
    captioner_cmd: str | None = Field(
        default=None,
        description="Full override of the pipeline run command; bypasses Docker when set.",
    )
    fireworks_api_url: str = Field(
        default="https://api.fireworks.ai/inference/v1",
        description="Fireworks AI base URL probed by /api/keys/validate.",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """The configured origins, split and trimmed."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def input_dir(self) -> Path:
        """Directory holding the captioner input manifest."""
        return self.data_dir / "input"

    @property
    def output_dir(self) -> Path:
        """Directory the captioner writes results into."""
        return self.data_dir / "output"

    @property
    def media_dir(self) -> Path:
        """Directory served by /api/media."""
        return self.data_dir / "media"

    @property
    def oracle_index_path(self) -> Path:
        """Where the Track 3 Video-Oracle index lives when built."""
        return self.data_dir / "oracle" / "index.json"

    @property
    def tasks_path(self) -> Path:
        """Path to the input tasks manifest."""
        return self.input_dir / "tasks.json"

    @property
    def results_path(self) -> Path:
        """Path to the pipeline output file."""
        return self.output_dir / "results.json"

    def run_command(self) -> list[str] | str:
        """The pipeline command: CAPTIONER_CMD verbatim, or the default docker run.

        A string is returned for overrides (the OS command-line parser splits it,
        which is backslash-safe on Windows); the docker default is a ready list.
        """
        if self.captioner_cmd:
            return self.captioner_cmd

        import os
        env_flags: list[str] = []
        fw_key = os.environ.get("FIREWORKS_API_KEY", "")
        if fw_key:
            env_flags += ["-e", f"FIREWORKS_API_KEY={fw_key}"]
        for key, val in os.environ.items():
            if key.startswith("OMNICAPTION_") or key.startswith("HF_"):
                env_flags += ["-e", f"{key}={val}"]

        return [
            "docker",
            "run",
            "--rm",
            *env_flags,
            "-v",
            f"{self.input_dir.resolve()}:/input",
            "-v",
            f"{self.output_dir.resolve()}:/output",
            self.captioner_image,
        ]
