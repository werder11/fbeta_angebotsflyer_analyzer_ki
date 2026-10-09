"""Export machine-readable specs: OpenAPI for the REST API and JSON Schemas for all data contracts.

    uv run python scripts/export_specs.py          # write files
    uv run python scripts/export_specs.py --check  # exit 1 if committed specs are stale (used in tests/CI)

Specs are generated from code (pydantic / FastAPI), so they cannot drift from the implementation.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "data" / "schemas"
OPENAPI_PATH = ROOT / "docs" / "api" / "openapi.json"

RECORDING_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "LLMRecording",
    "description": "One recorded LLM response in data/recordings/<request_key>.json (ADR-0008). "
    "Key = sha256(purpose, prompt, schema, image hashes)[:32].",
    "type": "object",
    "required": ["purpose", "model_id", "response", "usage", "recorded_at"],
    "properties": {
        "purpose": {"type": "string", "enum": ["extract", "vision"]},
        "model_id": {"type": "string", "description": "Model that actually served the request"},
        "response": {"type": "object", "description": "Parsed JSON returned by the model"},
        "usage": {"type": "object", "additionalProperties": {"type": "integer"}},
        "recorded_at": {"type": "string", "format": "date-time"},
    },
}

REFERENCE_CSV_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "ReferencePriceCsvRow",
    "description": "One row of a reference price CSV (data/reference/*.csv), stand-in for PIM/price-DB data. "
    "Columns in this order; decimal point '.', dates ISO 8601; empty cell = null.",
    "type": "object",
    "required": ["sku", "product_name", "price"],
    "properties": {
        "sku": {"type": "string"},
        "product_name": {"type": "string"},
        "price": {"type": "string", "pattern": r"^\d+(\.\d{1,2})?$"},
        "original_price": {"type": ["string", "null"], "pattern": r"^\d+(\.\d{1,2})?$"},
        "quantity_raw": {"type": ["string", "null"]},
        "valid_from": {"type": ["string", "null"], "format": "date"},
        "valid_until": {"type": ["string", "null"], "format": "date"},
    },
}


def _schemas() -> dict[str, tuple[dict, str]]:
    from flyercheck.domain import models as m
    from flyercheck.extract import ExtractedPage
    from flyercheck.reference import ReferenceItem
    from flyercheck.vision_checks.prompts import V01_SCHEMA

    def js(model) -> dict:
        return {"$schema": "https://json-schema.org/draft/2020-12/schema", **model.model_json_schema()}

    return {
        "run-result.schema.json": (js(m.RunResult), "out/<run_id>/findings.json — full run incl. context + findings"),
        "finding.schema.json": (js(m.Finding), "a single finding (check result with evidence)"),
        "document-context.schema.json": (
            js(m.DocumentContext),
            "normalized offers + document facts (tests/fixtures/designer_context.json, `--from-context`)",
        ),
        "offer.schema.json": (js(m.Offer), "one extracted offer (raw + normalized values)"),
        "review-decision.schema.json": (js(m.ReviewDecision), "human decision, out/<run_id>/decisions.jsonl"),
        "golden-set.schema.json": (js(m.GoldenSet), "data/golden/*.json — evaluation labels"),
        "reference-item.schema.json": (js(ReferenceItem), "parsed reference record (R-08)"),
        "reference-price-csv.schema.json": (REFERENCE_CSV_SCHEMA, "data/reference/*.csv row format"),
        "llm-extract-response.schema.json": (
            {"$schema": "https://json-schema.org/draft/2020-12/schema", **ExtractedPage.model_json_schema()},
            "response schema sent to the LLM for page extraction (structured output)"),
        "llm-vision-v01-response.schema.json": (
            {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "V01Response", **V01_SCHEMA},
            "response schema sent to the LLM for the V-01 image↔text check"),
        "llm-recording.schema.json": (RECORDING_SCHEMA, "data/recordings/*.json — record/replay cache"),
    }


def _openapi() -> dict:
    from flyercheck.api import create_app

    with tempfile.TemporaryDirectory() as tmp:
        return create_app(out_dir=tmp).openapi()


def _dump(obj: dict) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def render() -> dict[Path, str]:
    files: dict[Path, str] = {OPENAPI_PATH: _dump(_openapi())}
    rows = []
    for name, (schema, purpose) in _schemas().items():
        files[SCHEMA_DIR / name] = _dump(schema)
        rows.append(f"| [`{name}`]({name}) | {purpose} |")
    files[SCHEMA_DIR / "README.md"] = (
        "# Data Schemas\n\n"
        "JSON Schemas (draft 2020-12) for every data contract of FlyerCheck. **Generated** from code by "
        "`uv run python scripts/export_specs.py` — do not edit by hand; `tests/test_specs.py` fails if they are stale.\n\n"
        "REST API: [docs/api/openapi.json](../../docs/api/openapi.json) · Contract docs: "
        "[docs/domain/domain-model.md](../../docs/domain/domain-model.md) · ADR: "
        "[0004 canonical contract](../../docs/adr/0004-canonical-contract.md)\n\n"
        "| Schema | Describes |\n|---|---|\n" + "\n".join(rows) + "\n"
    )
    return files


def main(argv: list[str]) -> int:
    check = "--check" in argv
    stale = []
    for path, content in render().items():
        if check:
            if not path.exists() or path.read_text() != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print("stale specs (run scripts/export_specs.py):\n  " + "\n  ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
