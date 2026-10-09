"""Wiring test: stages monkeypatched, so it runs independently of track implementations."""
import json
from pathlib import Path
from typing import ClassVar

from flyercheck import pipeline
from flyercheck.domain.models import Category, Finding, Severity, Status


class _LLM:
    model_id = "fake-model"
    usage: ClassVar[dict[str, int]] = {"calls": 0}


def _finding(check_id: str, status: Status) -> Finding:
    return Finding(id=f"{check_id}:doc", check_id=check_id, category=Category.E03_ARITHMETIC,
                   severity=Severity.HIGH, status=status, summary=check_id)


def test_pipeline_from_context_wires_stages(monkeypatch, tmp_path):
    calls = {}
    monkeypatch.setattr(pipeline, "make_llm", lambda mode, rec, provider: _LLM())
    monkeypatch.setattr(pipeline.rules, "run_rules", lambda ctx: [_finding("R-01", Status.FAIL)])
    monkeypatch.setattr(pipeline.vision_checks, "run_vision_checks",
                        lambda ctx, llm: [_finding("V-01", Status.PASS)])
    monkeypatch.setattr(pipeline.aggregate, "aggregate", lambda fs: fs)

    def fake_report(run, out_dir):
        calls["out_dir"] = out_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / "findings.json").write_text(run.model_dump_json())
        return str(Path(out_dir) / "report.html")

    monkeypatch.setattr(pipeline.report, "write_report", fake_report)

    res = pipeline.run("ignored.pdf", out=str(tmp_path), from_context="tests/fixtures/designer_context.json",
                       year=2026)
    assert [f.check_id for f in res.findings] == ["R-01", "V-01"]
    assert res.mode == "context" and res.versions["extract_model"] == "n/a (context)"
    assert res.context.document.campaign_year_source == "cli"
    assert calls["out_dir"].endswith(res.run_id)
    assert json.loads((Path(calls["out_dir"]) / "findings.json").read_text())["run_id"] == res.run_id
