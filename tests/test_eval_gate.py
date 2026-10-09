"""scripts/eval_gate.py: pass/fail decisions on synthetic runs built from the golden labels."""
from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flyercheck.domain.models import (
    Category,
    Document,
    DocumentContext,
    Finding,
    GoldenSet,
    RunResult,
    Severity,
    Status,
)

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "golden" / "designer.json"


def _load_gate():
    spec = importlib.util.spec_from_file_location("eval_gate", ROOT / "scripts" / "eval_gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gate = _load_gate()


def _findings_from_golden(golden: GoldenSet) -> list[Finding]:
    return [
        Finding(
            id=f"{lb.check_id}:{i}",
            check_id=lb.check_id,
            category=Category.E03_ARITHMETIC,
            severity=lb.severity or Severity.INFO,
            status=lb.status,
            summary=lb.note or lb.id,
            offer_id=f"o-{i}" if lb.offer_name else None,
            offer_name=lb.offer_name,
        )
        for i, lb in enumerate(golden.labels + golden.expected_passes)
    ]


def _write_run(tmp_path: Path, findings: list[Finding]) -> Path:
    ctx = DocumentContext(
        document=Document(id="x", sha256="x", filename="Designer.pdf", page_count=1),
        pages=[],
        offers=[],
    )
    run = RunResult(run_id="t", started_at=datetime(2026, 10, 9, tzinfo=UTC), duration_s=0.0,
                    mode="replay", context=ctx, findings=findings)
    path = tmp_path / "findings.json"
    path.write_text(run.model_dump_json())
    return path


@pytest.fixture
def golden() -> GoldenSet:
    return GoldenSet.model_validate_json(GOLDEN.read_text())


def test_perfect_run_passes(tmp_path, golden, capsys):
    path = _write_run(tmp_path, _findings_from_golden(golden))
    assert gate.main([str(path), str(GOLDEN)]) == 0
    assert "EVAL GATE PASSED" in capsys.readouterr().out


def test_missed_defect_fails_recall(tmp_path, golden, capsys):
    # Drop the aubergine/chocolate finding (G-01): recall 8/9.
    findings = [f for f in _findings_from_golden(golden)
                if not (f.check_id == "V-01" and f.status == Status.FAIL)]
    path = _write_run(tmp_path, findings)
    assert gate.main([str(path), str(GOLDEN), "--min-agreement", "0.0"]) == 1
    assert "EVAL GATE FAILED: overall recall" in capsys.readouterr().out


def test_status_disagreement_fails_agreement(tmp_path, golden, capsys):
    # Flip expected passes to needs_review: recall stays 1.0, agreement drops to 10/20.
    findings = [f.model_copy(update={"status": Status.NEEDS_REVIEW}) if f.status == Status.PASS else f
                for f in _findings_from_golden(golden)]
    path = _write_run(tmp_path, findings)
    assert gate.main([str(path), str(GOLDEN), "--min-recall", "0.0"]) == 1
    out = capsys.readouterr().out
    assert "EVAL GATE FAILED: status_agreement" in out
    assert "overall recall" not in out.split("EVAL GATE")[1]


def test_undefined_metrics_count_as_failure(tmp_path):
    empty = tmp_path / "golden.json"
    empty.write_text(GoldenSet(document="x", labels=[]).model_dump_json())
    path = _write_run(tmp_path, [])
    assert gate.main([str(path), str(empty), "--min-recall", "0.0", "--min-agreement", "0.0"]) == 1
