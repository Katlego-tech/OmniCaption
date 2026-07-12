"""The committed JSON-schema fixtures must validate what the code ACTUALLY writes.

The submission audit found these schema files were dead (nothing validated
against them), which let the output fixture drift to a `{"results": [...]}`
object while the code — and the real Track 2 harness contract — use a bare
array. This test wires the fixtures to the real writer so any future drift
fails CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from app.core.schema import Style
from app.pipeline.output import build_result, validate_and_write

SCHEMAS = Path(__file__).parent.parent / "fixtures" / "schemas"


def test_written_results_validate_against_fixture_schema(tmp_path: Path) -> None:
    schema = json.loads((SCHEMAS / "results.schema.json").read_text(encoding="utf-8"))
    results = [
        build_result("v1", {Style.FORMAL: "A caption."}, [Style.FORMAL, Style.SARCASTIC]),
        build_result("v2", {}, [Style.HUMOROUS_TECH]),  # empty-string sentinel
    ]
    out = tmp_path / "results.json"
    validate_and_write(results, out)

    written = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(written, schema)  # raises on drift
    assert isinstance(written, list), "Track 2 harness contract: top level is a bare array"
    assert written[0]["captions"]["sarcastic"] == ""


def test_sample_tasks_validate_against_input_schema() -> None:
    schema = json.loads((SCHEMAS / "tasks.schema.json").read_text(encoding="utf-8"))
    fixtures = Path(__file__).parent.parent / "fixtures"
    for name in ("tasks.sample.json", "tasks.validation.json"):
        data = json.loads((fixtures / name).read_text(encoding="utf-8"))
        jsonschema.validate(data, schema)
