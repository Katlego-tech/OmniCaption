"""Integration tests for the video/audio ingestion pipeline stage."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.errors import IngestionError
from app.core.schema import Style, Task
from app.pipeline.orchestrator import CaptionPipeline, CaptionState


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointed at a temp working directory."""
    return Settings(work_dir=tmp_path / "work", output_dir=tmp_path / "out")


def test_ingestion_success(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    """A successful task downloads the video and extracts WAV, populating CaptionState."""
    expected_video = settings.work_dir / "v1_clip.mp4"
    expected_wav = settings.work_dir / "v1_clip.wav"

    # Mock ingestion functions
    monkeypatch.setattr(
        "app.pipeline.ingestion.download_video",
        lambda url, dest_dir, timeout_s, task_id: expected_video,
    )
    monkeypatch.setattr(
        "app.pipeline.ingestion.extract_audio",
        lambda video_path, dest_dir: expected_wav,
    )

    # We mock transcription, vision, and synthesis to do nothing
    monkeypatch.setattr("app.pipeline.orchestrator.free_model", lambda model: None)
    monkeypatch.setattr("app.pipeline.orchestrator.reclaim_vram", lambda: None)
    monkeypatch.setattr("app.pipeline.audio.WhisperTranscriber.load", lambda self: None)
    monkeypatch.setattr(
        "app.pipeline.audio.WhisperTranscriber.transcribe",
        lambda self, wav: None,
    )
    monkeypatch.setattr("app.pipeline.audio.WhisperTranscriber.unload", lambda self: None)
    monkeypatch.setattr("app.pipeline.vision.extract_keyframes", lambda *a, **k: [])
    monkeypatch.setattr("app.pipeline.vision.align_to_transcript", lambda kfs, t: kfs)
    monkeypatch.setattr("app.pipeline.synthesis.CaptionSynthesizer.load", lambda self: None)
    monkeypatch.setattr(
        "app.pipeline.synthesis.CaptionSynthesizer.generate_for_styles",
        lambda self, kfs, transcript, styles: dict.fromkeys(styles, "dummy"),
    )

    task = Task(
        task_id="v1",
        video_url="https://example.com/clip.mp4",
        styles=[Style.FORMAL],
    )

    # Let's inspect CaptionState during run_task
    captured_state: CaptionState | None = None
    original_run_task = CaptionPipeline._run_task

    def mock_run_task(self, task_obj):
        nonlocal captured_state
        # Call original run_task to execute the flow
        res = original_run_task(self, task_obj)
        # Note: We'll modify orchestrator to store state or we can capture it here if we expose it
        # Actually, let's just make sure CaptionPipeline._run_task creates the state.
        # We can mock a stage (like vision or transcribe) to capture the state argument!
        return res

    monkeypatch.setattr(CaptionPipeline, "_run_task", mock_run_task)

    # Let's capture the state via mocking transcribe
    def mock_transcribe(self, wav):
        # We can find the active state or pass it. If transcribe takes wav,
        # we can't easily capture state unless we mock the orchestrator's transcription.
        # Wait, if we mock extract_keyframes, it gets called with video, which is in state.
        # Let's capture state by inspecting the orchestrator instance if it stores it,
        # or we can mock _transcribe to capture the state if we pass it or store it on self.
        pass

    # Current state is stored in self.current_state for testing/inspection.
    pipeline = CaptionPipeline(settings)
    pipeline.run([task])

    state = getattr(pipeline, "current_state", None)
    assert state is not None
    assert state.task_id == "v1"
    assert state.video_path == expected_video
    assert state.wav_path == expected_wav
    assert len(state.errors) == 0


def test_one_bad_task_does_not_abort_batch(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    """If one task fails during download, other tasks in the batch still run."""

    # Task 1 fails ingestion, Task 2 succeeds
    def mock_download_video(url, dest_dir, timeout_s, task_id):
        if task_id == "failed_task":
            raise IngestionError("Simulated download failure")
        return settings.work_dir / f"{task_id}_clip.mp4"

    monkeypatch.setattr("app.pipeline.ingestion.download_video", mock_download_video)
    monkeypatch.setattr(
        "app.pipeline.ingestion.extract_audio",
        lambda video_path, dest_dir: settings.work_dir / f"{video_path.stem}.wav",
    )

    # Mock downstream stages
    monkeypatch.setattr("app.pipeline.audio.WhisperTranscriber.load", lambda self: None)
    monkeypatch.setattr(
        "app.pipeline.audio.WhisperTranscriber.transcribe",
        lambda self, wav: None,
    )
    monkeypatch.setattr("app.pipeline.audio.WhisperTranscriber.unload", lambda self: None)
    monkeypatch.setattr("app.pipeline.vision.extract_keyframes", lambda *a, **k: [])
    monkeypatch.setattr("app.pipeline.vision.align_to_transcript", lambda kfs, t: kfs)
    monkeypatch.setattr("app.pipeline.synthesis.CaptionSynthesizer.load", lambda self: None)
    monkeypatch.setattr(
        "app.pipeline.synthesis.CaptionSynthesizer.generate_for_styles",
        lambda self, kfs, transcript, styles: dict.fromkeys(styles, "success_caption"),
    )

    tasks = [
        Task(task_id="failed_task", video_url="https://example.com/bad.mp4", styles=[Style.FORMAL]),
        Task(task_id="good_task", video_url="https://example.com/good.mp4", styles=[Style.FORMAL]),
    ]

    pipeline = CaptionPipeline(settings)
    results = pipeline.run(tasks)

    assert len(results) == 2

    # Task 1 result should have empty captions (due to failure)
    assert results[0].task_id == "failed_task"
    assert results[0].captions[Style.FORMAL] == ""

    # Task 2 result should have success caption
    assert results[1].task_id == "good_task"
    assert results[1].captions[Style.FORMAL] == "success_caption"
