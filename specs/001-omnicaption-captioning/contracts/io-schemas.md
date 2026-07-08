# Contract: Input & Output JSON Schemas

**Feature branch:** `001-omnicaption-captioning`
**Related:** [../spec.md](../spec.md) · [../data-model.md](../data-model.md) · [pipeline-stages.md](pipeline-stages.md)

This is the **authoritative** JSON contract between the evaluation harness and OmniCaption. The
harness mounts `/input/tasks.json` and reads `/output/results.json`. Both are validated in
`tests/contract/`. The four known style keys are the closed set
`{formal, sarcastic, humorous_tech, humorous_non_tech}`.

---

## Input — `/input/tasks.json`

A **JSON array** of task objects.

### Field table

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `task_id` | string | yes | Non-empty; unique within the batch. |
| `video_url` | string | yes | Non-empty; fetchable by the downloader. |
| `styles` | array of string | yes | Non-empty; items **should** be known styles. Unknown items are dropped (warned); duplicates de-duplicated. |

### JSON Schema (input)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://omnicaption/schemas/tasks.schema.json",
  "title": "OmniCaption tasks input",
  "type": "array",
  "items": {
    "type": "object",
    "additionalProperties": false,
    "required": ["task_id", "video_url", "styles"],
    "properties": {
      "task_id": { "type": "string", "minLength": 1 },
      "video_url": { "type": "string", "minLength": 1 },
      "styles": {
        "type": "array",
        "minItems": 1,
        "items": {
          "type": "string",
          "enum": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
        }
      }
    }
  }
}
```

> **Tolerance note.** The schema above is the *strict* form used to validate our own fixtures. At
> runtime the loader is **lenient about unknown style strings** — it drops them and continues
> (spec AC1.4) rather than rejecting the whole batch — but it is **strict** about structural shape
> (array of objects with the three required keys). A structurally malformed document fails fast
> (spec AC1.5).

---

## Output — `/output/results.json`

A **JSON object** with a `results` array — one entry per input task, in input order.

### Field table

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `results` | array | yes | One `ClipResult` per input task. `len == len(tasks)`. |
| `results[].task_id` | string | yes | Echoes the input `task_id`. |
| `results[].captions` | object | yes | Map `style_key → caption`. Keys ⊆ known styles; equals the task's requested+known styles. Each value non-empty. |

### JSON Schema (output)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://omnicaption/schemas/results.schema.json",
  "title": "OmniCaption results output",
  "type": "object",
  "additionalProperties": false,
  "required": ["results"],
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["task_id", "captions"],
        "properties": {
          "task_id": { "type": "string", "minLength": 1 },
          "captions": {
            "type": "object",
            "minProperties": 0,
            "additionalProperties": false,
            "propertyNames": {
              "enum": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
            },
            "patternProperties": {
              "^(formal|sarcastic|humorous_tech|humorous_non_tech)$": {
                "type": "string",
                "minLength": 1
              }
            }
          }
        }
      }
    }
  }
}
```

---

## The missing-style rule (scored 0)

The harness scores **each requested `(clip, style)` pair**. For a given task:

- If a requested style key is **present** in `results[i].captions` with a non-empty string, that pair
  is scored on Accuracy + Style Match.
- If a requested style key is **absent** (or empty, or the whole `results` entry is missing/invalid),
  that pair contributes **0** to Φ.

Therefore OmniCaption's overriding output rule is: **emit a caption for every requested + known style,
always** — using the deterministic fallback caption when synthesis fails (spec AC4.4, AC6.2). It is
always better to emit a grounded fallback than to omit a style.

### Consistency requirements

- `results` length equals the number of input tasks; order preserved.
- Every `captions` key is a member of the closed style set.
- The document as a whole validates against the output schema **before** it is written; a validation
  failure triggers a repair-to-valid write, never an invalid file (spec AC6.2).
- The process exits `0` after writing (spec AC6.3).

---

## Contract tests

| Test | Asserts |
| --- | --- |
| `tests/contract/test_input_schema.py` | Valid fixtures pass; structurally malformed inputs are rejected; unknown styles are dropped at load. |
| `tests/contract/test_output_schema.py` | Generated `results.json` validates; every requested+known style is present; keys are within the closed set. |
| `tests/integration/test_missing_style_scores_zero.py` | A deliberately dropped style is absent and the documented 0-score behavior holds. |
