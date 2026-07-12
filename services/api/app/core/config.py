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
    auto_build_index: bool = Field(
        default=True,
        description="After a successful run, auto-build the Track 3 oracle index from "
        "results.json so search/QA work without a manual `oracle.cli build` step.",
    )
    fireworks_api_url: str = Field(
        default="https://api.fireworks.ai/inference/v1",
        description="Fireworks AI base URL probed by /api/keys/validate.",
    )
    auth_secret: str = Field(
        default="",
        description="HMAC signing secret for auth tokens. When empty, a random secret is "
        "generated and persisted under DATA_DIR — set this explicitly for multi-instance "
        "deployments so every instance signs with the same key.",
    )
    token_ttl_hours: int = Field(
        default=24 * 7,
        description="Lifetime of an issued auth token, in hours.",
    )
    rate_limit_max: int = Field(
        default=20,
        description="Max auth attempts (signup/login/verify) per window, per client IP.",
    )
    rate_limit_window_s: int = Field(
        default=60, description="Window for auth rate limiting, in seconds."
    )
    redis_url: str = Field(
        default="",
        description="Optional Redis URL for a rate-limit store shared across API instances. "
        "When empty (or unreachable), rate limiting falls back to per-process in-memory.",
    )
    require_verification: bool = Field(
        default=False,
        description="Require email verification before login. When true, signup returns a "
        "generic 202 (no token, no account-existence oracle) and login blocks unverified users.",
    )
    cookie_secure: bool = Field(
        default=False, description="Set the Secure flag on the session cookie (enable over HTTPS)."
    )
    cookie_samesite: str = Field(
        default="lax", description="SameSite policy for the session cookie (lax/strict/none)."
    )
    ssrf_resolve_dns: bool = Field(
        default=True,
        description="Resolve video_url hostnames at submit and reject internal IPs "
        "(mitigates DNS-based SSRF; disable in offline tests).",
    )

    @property
    def auth_db_path(self) -> Path:
        """SQLite file holding user accounts."""
        return self.data_dir / "auth.db"

    @property
    def auth_outbox_dir(self) -> Path:
        """Dev mailer outbox for verification links."""
        return self.data_dir / "outbox"

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

    def run_command(self, fireworks_api_key: str | None = None) -> list[str] | str:
        """The pipeline command: CAPTIONER_CMD verbatim, or the default docker run.

        A string is returned for overrides (the OS command-line parser splits it,
        which is backslash-safe on Windows); the docker default is a ready list.
        """
        if self.captioner_cmd:
            return self.captioner_cmd

        import os

        env_flags: list[str] = []
        fw_key = fireworks_api_key or os.environ.get("FIREWORKS_API_KEY", "")
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
