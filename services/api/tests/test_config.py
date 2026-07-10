"""Settings.run_command — the default docker invocation and env forwarding."""

from __future__ import annotations

import pytest

from app.core.config import Settings


def test_override_command_is_returned_verbatim(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path, captioner_cmd="echo hi", _env_file=None)
    assert settings.run_command() == "echo hi"


def test_default_is_a_docker_run_with_mounts(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path, captioner_image="omnicaption:test", _env_file=None)
    cmd = settings.run_command()
    assert isinstance(cmd, list)
    assert cmd[:3] == ["docker", "run", "--rm"]
    assert cmd[-1] == "omnicaption:test"
    assert cmd.count("-v") == 2  # input + output mounts


def test_fireworks_and_omnicaption_env_are_forwarded(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-secret")
    monkeypatch.setenv("OMNICAPTION_MAX_KEYFRAMES", "4")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("UNRELATED_VAR", "nope")

    cmd = Settings(data_dir=tmp_path, _env_file=None).run_command()
    joined = " ".join(cmd)

    assert "-e" in cmd
    assert "FIREWORKS_API_KEY=fw-secret" in joined
    assert "OMNICAPTION_MAX_KEYFRAMES=4" in joined
    assert "HF_HUB_OFFLINE=1" in joined
    assert "UNRELATED_VAR" not in joined
