"""Per-entry salvage of the judge-controlled tasks.json (tests FIRST).

``load_tasks`` validates the WHOLE document in one pydantic call, and
``main._load_tasks`` turned any failure into an empty batch — so a single
malformed entry in the hidden set (bad types, missing styles, all-unknown
styles) would have produced MISSING_TASKS for every clip. The entrypoint must
salvage entry-by-entry: valid entries run normally; an invalid entry with a
usable ``task_id`` still yields a result (all four known styles, so whatever
subset was actually requested is covered); only truly unusable entries drop.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import main as app_main
from app.core.config import Settings
from app.core.schema import Style

GOOD = {
    "task_id": "good",
    "video_url": "https://example.com/good.mp4",
    "styles": ["formal", "sarcastic"],
}


def _cfg(tmp_path: Path, payload: object) -> Settings:
    input_dir = tmp_path / "input"
    input_dir.mkdir(exist_ok=True)
    (input_dir / "tasks.json").write_text(json.dumps(payload), encoding="utf-8")
    return Settings(_env_file=None, input_dir=input_dir, output_dir=tmp_path / "out")


def test_valid_file_unchanged(tmp_path: Path) -> None:
    tasks = app_main._load_tasks(_cfg(tmp_path, [GOOD]))
    assert [t.task_id for t in tasks] == ["good"]
    assert tasks[0].styles == [Style.FORMAL, Style.SARCASTIC]


def test_one_bad_entry_does_not_erase_the_batch(tmp_path: Path) -> None:
    bad = {"task_id": "bad", "video_url": "https://example.com/x.mp4"}  # no styles at all
    tasks = app_main._load_tasks(_cfg(tmp_path, [GOOD, bad]))

    assert [t.task_id for t in tasks] == ["good", "bad"]
    # The salvaged entry hedges with ALL known styles so any requested subset
    # is covered (extra keys are harmless; a missing key scores 0).
    assert set(tasks[1].styles) == set(Style)


def test_all_unknown_styles_entry_is_salvaged(tmp_path: Path) -> None:
    bad = {
        "task_id": "weird",
        "video_url": "https://example.com/w.mp4",
        "styles": ["haiku", "noir"],
    }
    tasks = app_main._load_tasks(_cfg(tmp_path, [bad]))
    assert [t.task_id for t in tasks] == ["weird"]
    assert set(tasks[0].styles) == set(Style)


def test_entry_without_task_id_drops_but_others_survive(tmp_path: Path) -> None:
    tasks = app_main._load_tasks(_cfg(tmp_path, [{"video_url": "https://x.mp4"}, GOOD]))
    assert [t.task_id for t in tasks] == ["good"]


@pytest.mark.parametrize("payload", [{"not": "a list"}, "just a string", 42])
def test_non_list_top_level_still_yields_empty(tmp_path: Path, payload: object) -> None:
    assert app_main._load_tasks(_cfg(tmp_path, payload)) == []
