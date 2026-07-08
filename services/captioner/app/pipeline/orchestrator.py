"""Pipeline orchestration: run the six stages per task with sequential loading.

Model lifecycle across a run:
    1. Ingest + extract audio for the task.
    2. Load Whisper once, transcribe, then unload + reclaim VRAM.
    3. Extract + align keyframes (CPU/OpenCV).
    4. Load Gemma once, generate captions for all styles.
    5. Build/validate output.

The Gemma model is loaded lazily on the first task and reused for the rest of the
run; Whisper is loaded per task but always unloaded before synthesis so the two
large models never co-reside in VRAM.
"""

from __future__ import annotations

import time

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schema import ClipResult, Task
from app.pipeline import ingestion
from app.pipeline.audio import Transcript, WhisperTranscriber
from app.pipeline.memory import free_model, reclaim_vram
from app.pipeline.output import build_result
from app.pipeline.synthesis import CaptionSynthesizer
from app.pipeline.vision import align_to_transcript, extract_keyframes

logger = get_logger(__name__)


class CaptionPipeline:
    """Runs the OmniCaption six-stage pipeline over a batch of tasks."""

    def __init__(self, cfg: Settings) -> None:
        """Initialize the pipeline.

        Args:
            cfg: Application settings.
        """
        self._cfg = cfg
        # Synthesizer persists across tasks (loaded once, reused).
        self._synth = CaptionSynthesizer(cfg)
        self._run_started: float = 0.0

    def run(self, tasks: list[Task]) -> list[ClipResult]:
        """Run the pipeline over all tasks.

        Args:
            tasks: Parsed input tasks.

        Returns:
            One :class:`ClipResult` per task (order preserved). A task that fails
            still yields a result with empty captions for its requested styles.
        """
        self._run_started = time.monotonic()
        results: list[ClipResult] = []

        for task in tasks:
            elapsed = time.monotonic() - self._run_started
            if elapsed > self._cfg.total_runtime_budget_s:
                logger.error(
                    "Total runtime budget (%.0fs) exceeded; emitting empty results for rest.",
                    self._cfg.total_runtime_budget_s,
                )
                results.append(build_result(task.task_id, {}, task.styles))
                continue

            results.append(self._run_task(task))

        return results

    def _run_task(self, task: Task) -> ClipResult:
        """Execute all stages for a single task with per-task error isolation.

        Args:
            task: The task to process.

        Returns:
            The task's result (possibly with empty captions on failure).
        """
        started = time.monotonic()
        logger.info("=== Task %s: %s ===", task.task_id, task.video_url)

        try:
            # Stage 1: ingestion.
            video = ingestion.download_video(
                task.video_url,
                self._cfg.work_dir,
                timeout_s=self._cfg.download_timeout_s,
                task_id=task.task_id,
            )
            wav = ingestion.extract_audio(video, self._cfg.work_dir)

            # Stages 2 + 3: transcription then VRAM reclamation.
            transcript = self._transcribe(wav)

            # Stage 4: vision.
            keyframes = extract_keyframes(
                video,
                threshold=self._cfg.keyframe_threshold,
                max_keyframes=self._cfg.max_keyframes,
            )
            align_to_transcript(keyframes, transcript)

            # Stage 5: synthesis.
            self._synth.load()
            captions = self._synth.generate_for_styles(keyframes, transcript, task.styles)

            result = build_result(task.task_id, captions, task.styles)
        except Exception as exc:  # noqa: BLE001 - isolate task failures
            logger.exception("Task %s failed: %s", task.task_id, exc)
            result = build_result(task.task_id, {}, task.styles)

        latency = time.monotonic() - started
        if latency > self._cfg.per_request_budget_s:
            logger.warning(
                "Task %s took %.1fs (>%.0fs budget).",
                task.task_id,
                latency,
                self._cfg.per_request_budget_s,
            )
        else:
            logger.info("Task %s done in %.1fs.", task.task_id, latency)
        return result

    def _transcribe(self, wav) -> Transcript:  # noqa: ANN001 - Path, kept simple
        """Load Whisper, transcribe, then unload and reclaim VRAM.

        Args:
            wav: Path to the extracted WAV file.

        Returns:
            The transcript.
        """
        transcriber = WhisperTranscriber(self._cfg)
        transcriber.load()
        try:
            transcript = transcriber.transcribe(wav)
        finally:
            transcriber.unload()
            free_model(transcriber)
            reclaim_vram()  # Stage 3: free Whisper before loading Gemma.
        return transcript

    def close(self) -> None:
        """Release the synthesizer and reclaim VRAM at end of run."""
        self._synth.unload()
        free_model(self._synth)
        reclaim_vram()
