"""Pipeline orchestration: run the six stages per task, tasks in parallel.

Tasks are processed by a small worker pool (``task_concurrency``): downloads,
keyframe extraction, and the remote Fireworks synthesis calls all overlap
across clips — sequential processing of ~12 hidden clips at 1.5–3 min each can
never fit the 600 s budget, and every clip that misses the cutoff scores zero.

Model lifecycle across a run:
    - Whisper (the only LOCAL model) loads once per run and transcribes behind
      a lock, serializing the GPU work.
    - Synthesis is a remote API (Fireworks VLM), so nothing co-resides with
      Whisper in VRAM — the historical per-task load/unload handoff existed
      for the retired local-Gemma design.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schema import ClipResult, Style, Task
from app.core.timing import stage_timer
from app.pipeline import ingestion
from app.pipeline.audio import Transcript, WhisperTranscriber
from app.pipeline.memory import free_model, reclaim_vram
from app.pipeline.output import build_result
from app.pipeline.synthesis import CaptionSynthesizer
from app.pipeline.vision import align_to_transcript, extract_keyframes

if TYPE_CHECKING:
    from app.pipeline.vision import Keyframe

logger = get_logger(__name__)


@dataclass
class CaptionState:
    """Mutable state threaded through the 6 pipeline stages for a single task."""

    task_id: str
    styles: list[Style]
    video_path: Path | None = None
    wav_path: Path | None = None
    transcript: Transcript | None = None
    keyframes: list[Keyframe] = field(default_factory=list)
    captions: dict[Style, str] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


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
        self.current_state: CaptionState | None = None
        # Collected for the transcript sidecar (Track 3 oracle enrichment).
        self.transcripts: dict[str, Transcript] = {}
        # Whisper is shared across tasks: loaded once, transcription serialized.
        self._whisper: WhisperTranscriber | None = None
        self._whisper_lock = threading.Lock()

    def run(
        self,
        tasks: list[Task],
        on_result: Callable[[list[ClipResult]], None] | None = None,
    ) -> list[ClipResult]:
        """Run the pipeline over all tasks.

        Args:
            tasks: Parsed input tasks.
            on_result: Optional callback fired after EVERY task completion with
                a COMPLETE, input-ordered document — finished tasks carry their
                real captions, unfinished ones placeholder empties — so the
                entrypoint can atomically refresh ``results.json`` and a
                mid-batch kill still leaves a valid document covering every
                task. Called under a lock (writes never interleave); callback
                errors are logged and never abort the batch.

        Returns:
            One :class:`ClipResult` per task (input order preserved). A task
            that fails still yields a result with empty captions for its
            requested styles.
        """
        self._run_started = time.monotonic()
        # Stop STARTING tasks early enough that in-flight ones can finish and
        # the process still exits 0 before any harness-side kill at the budget.
        start_cutoff = max(0.0, self._cfg.total_runtime_budget_s - self._cfg.budget_reserve_s)
        # Same moment gates synthesis retry escalation: near the deadline, one
        # attempt per style for every clip beats three attempts for a few.
        self._synth.retry_deadline = self._run_started + start_cutoff

        results: list[ClipResult | None] = [None] * len(tasks)
        results_lock = threading.Lock()

        def _snapshot() -> list[ClipResult]:
            return [
                r if r is not None else build_result(t.task_id, {}, t.styles)
                for r, t in zip(results, tasks, strict=True)
            ]

        def _process(idx: int, task: Task) -> None:
            elapsed = time.monotonic() - self._run_started
            if elapsed > start_cutoff:
                logger.error(
                    "Runtime cutoff reached (%.0fs elapsed > %.0fs budget - %.0fs reserve); "
                    "emitting an empty result for task %s.",
                    elapsed,
                    self._cfg.total_runtime_budget_s,
                    self._cfg.budget_reserve_s,
                    task.task_id,
                )
                result = build_result(task.task_id, {}, task.styles)
            else:
                result = self._run_task(task)
            with results_lock:
                results[idx] = result
                if on_result is not None:
                    try:
                        on_result(_snapshot())
                    except Exception as exc:  # noqa: BLE001 - reporting never sinks the batch
                        logger.warning("on_result callback failed: %s", exc)

        workers = max(1, self._cfg.task_concurrency)
        if workers == 1 or len(tasks) <= 1:
            for idx, task in enumerate(tasks):
                _process(idx, task)
        else:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="task") as pool:
                futures = [pool.submit(_process, i, t) for i, t in enumerate(tasks)]
                for future in futures:
                    future.result()  # surface unexpected worker crashes

        return _snapshot()

    def _run_task(self, task: Task) -> ClipResult:
        """Execute all stages for a single task with per-task error isolation.

        Args:
            task: The task to process.

        Returns:
            The task's result (possibly with empty captions on failure).
        """
        started = time.monotonic()
        logger.info("=== Task %s: %s ===", task.task_id, task.video_url)

        # Create the state object and make it inspectable
        state = CaptionState(task_id=task.task_id, styles=task.styles)
        self.current_state = state

        try:
            # Stage 1: ingestion.
            with stage_timer("ingestion", state.timings):
                state.video_path = ingestion.download_video(
                    task.video_url,
                    self._cfg.work_dir,
                    timeout_s=self._cfg.download_timeout_s,
                    task_id=task.task_id,
                )
                state.wav_path = ingestion.extract_audio(state.video_path, self._cfg.work_dir)

            # Stages 2 + 3: transcription then VRAM reclamation.
            with stage_timer("audio", state.timings):
                state.transcript = self._transcribe(state.wav_path)
                self.transcripts[task.task_id] = state.transcript

            # Stage 4: vision.
            with stage_timer("vision", state.timings):
                state.keyframes = extract_keyframes(
                    state.video_path,
                    threshold=self._cfg.keyframe_threshold,
                    max_keyframes=self._cfg.max_keyframes,
                )
                align_to_transcript(state.keyframes, state.transcript)

            if self._cfg.emit_keyframes and state.keyframes:
                try:
                    from app.pipeline.sidecars import write_keyframe_sidecar

                    write_keyframe_sidecar(
                        task.task_id, state.keyframes, self._cfg.output_dir / "keyframes"
                    )
                except Exception as exc:  # noqa: BLE001 - sidecars never fail the task
                    logger.warning("Keyframe sidecar failed for %s: %s", task.task_id, exc)

            # Stage 5: synthesis.
            with stage_timer("synthesis", state.timings):
                self._synth.load()
                state.captions = self._synth.generate_for_styles(
                    state.keyframes, state.transcript, task.styles
                )

            result = build_result(task.task_id, state.captions, task.styles)
        except Exception as exc:  # noqa: BLE001 - isolate task failures
            logger.exception("Task %s failed: %s", task.task_id, exc)
            state.errors.append(str(exc))
            result = build_result(task.task_id, state.captions, task.styles)

        latency = time.monotonic() - started
        state.timings["total"] = latency
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
        """Transcribe on the shared Whisper model (loaded once, serialized).

        The lock serializes GPU work across task workers; synthesis is remote,
        so Whisper stays resident for the whole run with nothing to co-reside.

        Args:
            wav: Path to the extracted WAV file.

        Returns:
            The transcript.
        """
        with self._whisper_lock:
            if self._whisper is None:
                transcriber = WhisperTranscriber(self._cfg)
                transcriber.load()
                self._whisper = transcriber
            return self._whisper.transcribe(wav)

    def close(self) -> None:
        """Release Whisper and the synthesizer, reclaim VRAM at end of run."""
        if self._whisper is not None:
            self._whisper.unload()
            free_model(self._whisper)
            self._whisper = None
        self._synth.unload()
        free_model(self._synth)
        reclaim_vram()
