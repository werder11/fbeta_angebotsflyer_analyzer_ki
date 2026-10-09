"""Committed specs (OpenAPI + JSON Schemas) must match the code."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
_spec = importlib.util.spec_from_file_location("export_specs", ROOT / "scripts/export_specs.py")
export_specs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(export_specs)


def test_specs_are_up_to_date():
    assert export_specs.main(["--check"]) == 0, "run: uv run python scripts/export_specs.py"


def test_openapi_lists_review_endpoint():
    spec = json.loads((ROOT / "docs/api/openapi.json").read_text())
    assert any(p.endswith("/decision") for p in spec["paths"])


def test_golden_files_validate_against_schema_shape():
    from flyercheck.domain.models import GoldenSet

    for f in (ROOT / "data/golden").glob("*.json"):
        GoldenSet.model_validate_json(f.read_text())
