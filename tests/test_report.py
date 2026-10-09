import base64
import pathlib
from datetime import UTC, datetime
from html.parser import HTMLParser

from flyercheck.domain.models import (
    BBox,
    Category,
    DocumentContext,
    Evidence,
    Finding,
    RunResult,
    Severity,
    Status,
)
from flyercheck.report import write_report


def _finding(check_id: str, status: Status, offer: tuple[str, str] | None, bbox: BBox | None) -> Finding:
    offer_id, offer_name = offer or (None, None)
    return Finding(
        id=f"{check_id}:{offer_id or 'doc'}",
        check_id=check_id,
        category=Category.E03_ARITHMETIC,
        severity=Severity.HIGH,
        status=status,
        summary=f"{check_id} <synthetic> & summary",
        offer_id=offer_id,
        offer_name=offer_name,
        observed={"price": "5.59"},
        expected={"price": "5.28"},
        evidence=[Evidence(bbox=bbox)] if bbox else [],
        confidence=0.9,
    )


def _run(ctx: DocumentContext) -> RunResult:
    findings = [
        _finding("R-01", Status.FAIL, ("o-6", "Steinofen Genuss Pizza Salami"), BBox(x0=0.1, y0=0.2, x1=0.4, y1=0.5)),
        _finding("R-04", Status.NEEDS_REVIEW, ("o-9", "Softina"), BBox(x0=0.5, y0=0.6, x1=0.9, y1=0.9)),
        _finding("R-01", Status.PASS, ("o-4", "Bergtal"), BBox(x0=0.0, y0=0.0, x1=0.2, y1=0.2)),
        _finding("R-08", Status.NOT_EVALUABLE, None, None),
        _finding("V-01", Status.ERROR, ("o-1", "Sonnenäpfel"), None),
    ]
    return RunResult(
        run_id="25c03aae-test",
        started_at=datetime(2026, 10, 9, 12, 0, tzinfo=UTC),
        duration_s=3.2,
        mode="replay",
        context=ctx,
        findings=findings,
        versions={"model": "gemini-test", "rules": "1.0"},
        llm_usage={"calls": 2, "input_tokens": 100, "output_tokens": 50},
    )


def test_write_report_files_and_html(designer_ctx, page_png, tmp_path):
    ctx = designer_ctx.model_copy(deep=True)
    png = tmp_path / "page1.png"
    png.write_bytes(page_png)
    ctx.pages[0].path = str(png)
    run = _run(ctx)

    html_path = pathlib.Path(write_report(run, str(tmp_path / "out")))
    assert html_path.name == "report.html" and html_path.exists()
    findings_json = tmp_path / "out" / "findings.json"
    assert RunResult.model_validate_json(findings_json.read_text()) == run

    html = html_path.read_text()
    with_bbox = [f for f in run.findings if any(e.bbox for e in f.evidence)]
    assert html.count("<rect") == len(with_bbox) == 3
    for f in with_bbox:
        assert f'data-finding-id="{f.id}"' in html
    assert "data:image/png;base64," + base64.b64encode(page_png).decode()[:64] in html
    assert 'viewBox="0 0 1 1"' in html and 'preserveAspectRatio="none"' in html
    assert "FlyerCheck report" in html and "Designer.pdf" in html and "gemini-test" in html
    assert "&lt;synthetic&gt;" in html  # autoescaped
    assert "No findings ≠ defect-free" in html
    assert "http://" not in html.replace('xmlns="http://www.w3.org/2000/svg"', "")
    HTMLParser().feed(html)  # parses without raising


def test_missing_page_image_shows_placeholder(designer_ctx, tmp_path):
    ctx = designer_ctx.model_copy(deep=True)
    ctx.pages[0].path = str(tmp_path / "does-not-exist.png")
    html = pathlib.Path(write_report(_run(ctx), str(tmp_path / "out"))).read_text()
    assert "image not available" in html
    assert "base64," not in html
    assert html.count("<rect") == 3
