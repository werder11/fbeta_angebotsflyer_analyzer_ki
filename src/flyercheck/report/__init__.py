"""findings.json + self-contained report.html. Owned by track T5."""
from __future__ import annotations

import base64
import pathlib
from collections import Counter

from jinja2 import Environment

from flyercheck.domain.models import RunResult, Status
from flyercheck.report.template import REPORT_TEMPLATE

STATUS_ORDER = [Status.FAIL, Status.NEEDS_REVIEW, Status.ERROR, Status.NOT_EVALUABLE, Status.PASS]
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

_template = Environment(autoescape=True).from_string(REPORT_TEMPLATE)


def _image_data_uri(path: str) -> str | None:
    p = pathlib.Path(path)
    try:
        data = p.read_bytes()
    except OSError:
        return None
    mime = "image/jpeg" if p.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _render(run: RunResult) -> str:
    counts = Counter(f.status for f in run.findings)
    findings = sorted(
        run.findings,
        key=lambda f: (STATUS_ORDER.index(f.status), _SEVERITY_RANK[f.severity.value], f.check_id),
    )
    pages = []
    for page in run.context.pages:
        rects = []
        for f in findings:
            ev = next((e for e in f.evidence if e.bbox is not None and e.page == page.number), None)
            if ev is None or ev.bbox is None:
                continue
            b = ev.bbox
            rects.append({
                "fid": f.id, "status": f.status.value,
                "x": b.x0, "y": b.y0, "w": max(b.x1 - b.x0, 0.0), "h": max(b.y1 - b.y0, 0.0),
                "title": f"{f.check_id} {f.status.value}: {f.summary}",
            })
        pages.append({
            "number": page.number, "width": page.width_px, "height": page.height_px,
            "src": _image_data_uri(page.path), "path": page.path, "rects": rects,
        })
    return _template.render(
        run=run,
        chips=[(s.value, counts.get(s, 0)) for s in STATUS_ORDER],
        findings=findings,
        pages=pages,
        model=run.versions.get("model") or run.versions.get("extract_model") or "—",
        filename=run.context.document.filename,
    )


def write_report(run: RunResult, out_dir: str) -> str:
    """Write findings.json and report.html into out_dir; return the html path."""
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "findings.json").write_text(run.model_dump_json(indent=2), encoding="utf-8")
    html_path = out / "report.html"
    html_path.write_text(_render(run), encoding="utf-8")
    return str(html_path)
