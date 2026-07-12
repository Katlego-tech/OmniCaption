"""Runtime resilience for the judged run (tests FIRST).

Measured on the 8-clip public validation batch (2026-07-12): synthesis is the
dominant stage at ~136 s/clip because the four Fireworks calls run
sequentially — and that latency is identical on the judge's MI300 (remote
API). Against a 600 s total budget and ~12 hidden clips, the old behavior
empties most of the batch. These tests pin the fixes:

1. The four style calls run CONCURRENTLY (per-style fallback isolation kept).
2. ``results.json`` is pre-written (all tasks, empty captions) BEFORE the
   pipeline starts and refreshed after every task — a judge-side kill can
   never yield OUTPUT_MISSING or MISSING_TASKS.
3. The batch guard stops STARTING tasks at ``budget - reserve`` so the
   in-flight task can finish and the process exits 0 before an external kill.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.schema import Style, Task
from app.pipeline import orchestrator as orch
from app.pipeline.audio import Transcript
from app.pipeline.output import build_result
from app.pipeline.synthesis import CaptionSynthesizer

ALL_STYLES = [Style.FORMAL, Style.SARCASTIC, Style.HUMOROUS_TECH, Style.HUMOROUS_NON_TECH]


def _transcript() -> Transcript:
    return Transcript(segments=[], language="en", duration=1.0)


def _task(task_id: str) -> Task:
    return Task(
        task_id=task_id,
        video_url=f"https://example.com/{task_id}.mp4",
        styles=[Style.FORMAL, Style.SARCASTIC],
    )


# --- 1. concurrent style synthesis ---------------------------------------------


def test_styles_generated_concurrently(monkeypatch: pytest.MonkeyPatch) -> None:
    """All four remote style calls overlap instead of running back-to-back."""
    cfg = Settings(_env_file=None, fireworks_api_key="fake_key")
    active = 0
    peak = 0
    lock = threading.Lock()

    def fake_request(
        self: CaptionSynthesizer, messages: list, style: Style, temperature: float, max_tokens: int
    ) -> str:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.15)
        with lock:
            active -= 1
        return f"[{style.value}] ok"

    monkeypatch.setattr(CaptionSynthesizer, "_request_caption", fake_request)
    synth = CaptionSynthesizer(cfg)
    synth.load()

    captions = synth.generate_for_styles([], _transcript(), ALL_STYLES)

    assert peak >= 2, f"style calls ran sequentially (peak concurrency {peak})"
    assert captions[Style.FORMAL] == "[formal] ok"
    assert set(captions) == set(ALL_STYLES)


def test_concurrent_failure_still_isolated_per_style(monkeypatch: pytest.MonkeyPatch) -> None:
    """One style blowing up concurrently still yields a fallback only for it."""
    cfg = Settings(_env_file=None, fireworks_api_key="fake_key", synthesis_max_attempts=1)

    def fake_request(
        self: CaptionSynthesizer, messages: list, style: Style, temperature: float, max_tokens: int
    ) -> str:
        if style is Style.SARCASTIC:
            raise RuntimeError("boom")
        return f"[{style.value}] ok"

    monkeypatch.setattr(CaptionSynthesizer, "_request_caption", fake_request)
    synth = CaptionSynthesizer(cfg)
    synth.load()

    captions = synth.generate_for_styles([], _transcript(), ALL_STYLES)

    assert captions[Style.FORMAL] == "[formal] ok"
    assert captions[Style.SARCASTIC]  # deterministic fallback, never empty
    assert "[sarcastic] ok" != captions[Style.SARCASTIC]


# --- 2. kill-safe incremental output --------------------------------------------


def test_results_prewritten_before_pipeline_starts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A schema-valid results.json with EVERY task exists before stage 1 runs."""
    from app import main as app_main

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    tasks = [
        {"task_id": "a", "video_url": "https://example.com/a.mp4", "styles": ["formal"]},
        {"task_id": "b", "video_url": "https://example.com/b.mp4", "styles": ["formal"]},
    ]
    (input_dir / "tasks.json").write_text(json.dumps(tasks), encoding="utf-8")

    cfg = Settings(_env_file=None, input_dir=input_dir, output_dir=output_dir)
    monkeypatch.setattr(app_main, "get_settings", lambda: cfg)

    seen_at_run: dict[str, object] = {}

    class SpyPipeline:
        def __init__(self, _cfg: Settings) -> None:
            self.transcripts: dict = {}

        def run(self, run_tasks: list[Task], on_result=None) -> list:  # noqa: ANN001
            results_file = cfg.results_path
            seen_at_run["existed"] = results_file.exists()
            if results_file.exists():
                seen_at_run["doc"] = json.loads(results_file.read_text(encoding="utf-8"))
            return [build_result(t.task_id, {}, t.styles) for t in run_tasks]

        def close(self) -> None:
            pass

    monkeypatch.setattr(app_main, "CaptionPipeline", SpyPipeline)

    assert app_main.run() == 0
    assert seen_at_run["existed"] is True, "results.json was not pre-written"
    doc = seen_at_run["doc"]
    assert [c["task_id"] for c in doc] == ["a", "b"]
    assert all(c["captions"] == {"formal": ""} for c in doc)


def test_pipeline_reports_each_result_incrementally(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """`run(tasks, on_result=...)` fires after every task with results so far."""
    calls: list[int] = []

    monkeypatch.setattr(
        orch.CaptionPipeline,
        "_run_task",
        lambda self, task: build_result(task.task_id, {}, task.styles),
    )
    pipeline = orch.CaptionPipeline(settings)
    results = pipeline.run([_task("a"), _task("b")], on_result=lambda done: calls.append(len(done)))

    assert len(results) == 2
    assert calls == [1, 2]


# --- 3. budget guard with in-flight reserve --------------------------------------


def test_budget_reserve_stops_starting_new_tasks(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """No new task starts once elapsed > budget - reserve; results stay complete."""
    cfg = settings.model_copy(update={"total_runtime_budget_s": 100.0, "budget_reserve_s": 40.0})

    clock = {"now": 1000.0}
    monkeypatch.setattr(orch.time, "monotonic", lambda: clock["now"])

    def fake_run_task(self: orch.CaptionPipeline, task: Task):  # noqa: ANN202
        clock["now"] += 35.0  # each task consumes 35s
        return build_result(task.task_id, {s: "real" for s in task.styles}, task.styles)

    monkeypatch.setattr(orch.CaptionPipeline, "_run_task", fake_run_task)

    pipeline = orch.CaptionPipeline(cfg)
    results = pipeline.run([_task("a"), _task("b"), _task("c")])

    # t=0 start a (ends 35); t=35 start b (ends 70); t=70 > 100-40=60 -> c skipped-empty.
    assert [r.task_id for r in results] == ["a", "b", "c"]
    assert results[0].captions[Style.FORMAL] == "real"
    assert results[1].captions[Style.FORMAL] == "real"
    assert results[2].captions[Style.FORMAL] == ""
