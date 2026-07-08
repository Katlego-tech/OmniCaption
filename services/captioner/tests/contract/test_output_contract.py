"""Contract tests: written results.json matches the harness schema exactly."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.schema import ClipResult, Style
from app.pipeline.output import build_result, validate_and_write


def test_written_output_matches_contract(tmp_path: Path) -> None:
    """validate_and_write emits a list of {task_id, captions{style:str}}."""
    requested = [Style.FORMAL, Style.SARCASTIC, Style.HUMOROUS_TECH, Style.HUMOROUS_NON_TECH]
    result = build_result(
        "v1",
        {
            Style.FORMAL: "A person assembles a device.",
            Style.SARCASTIC: "Groundbreaking.",
            Style.HUMOROUS_TECH: "Shipped straight to prod.",
            Style.HUMOROUS_NON_TECH: "Some assembly required, batteries not included.",
        },
        requested,
    )
    out = tmp_path / "results.json"
    validate_and_write([result], out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    entry = payload[0]
    assert set(entry.keys()) == {"task_id", "captions"}
    assert entry["task_id"] == "v1"
    assert set(entry["captions"].keys()) == {s.value for s in requested}
    assert all(isinstance(v, str) for v in entry["captions"].values())


def test_missing_style_is_flagged_and_backfilled(tmp_path: Path) -> None:
    """A missing requested style is backfilled empty and detectable via has_all."""
    requested = [Style.FORMAL, Style.SARCASTIC]
    result = build_result("v2", {Style.FORMAL: "Only one style present."}, requested)

    # Every requested key is present (contract), but has_all flags the gap.
    assert set(result.captions.keys()) == set(requested)
    assert result.has_all(requested) is False

    out = tmp_path / "results.json"
    validate_and_write([result], out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload[0]["captions"]["sarcastic"] == ""


def test_sample_fixtures_are_consistent() -> None:
    """The committed sample fixtures parse and agree on task ids/styles."""
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    tasks = json.loads((fixtures / "tasks.sample.json").read_text(encoding="utf-8"))
    results = json.loads((fixtures / "results.sample.json").read_text(encoding="utf-8"))

    task_ids = {t["task_id"] for t in tasks}
    result_ids = {r["task_id"] for r in results}
    assert task_ids == result_ids

    for task, result in zip(tasks, results, strict=True):
        # Every result validates and contains exactly the requested styles.
        ClipResult(
            task_id=result["task_id"],
            captions={Style(k): v for k, v in result["captions"].items()},
        )
        assert set(task["styles"]) == set(result["captions"].keys())
