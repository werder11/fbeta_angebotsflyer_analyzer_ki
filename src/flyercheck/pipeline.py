"""Orchestration: ingest → extract → (rules ∥ vision) → aggregate → report."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from flyercheck import aggregate, extract, ingest, report, rules, vision_checks
from flyercheck.domain.models import DocumentContext, RunResult
from flyercheck.llm.factory import make_llm

RULES_VERSION = "1.0"


def run(
    pdf: str,
    out: str = "out",
    mode: str = "replay",
    year: int | None = None,
    from_context: str | None = None,
    recordings_dir: str = "data/recordings",
) -> RunResult:
    t0 = time.perf_counter()
    started = datetime.now(UTC)
    llm = make_llm(mode, recordings_dir)

    if from_context:  # fallback path: skip ingest/extract, use a normalized context
        ctx = DocumentContext.model_validate_json(Path(from_context).read_text())
        if year:
            ctx.document.campaign_year, ctx.document.campaign_year_source = year, "cli"
    else:
        staging = Path(out) / f"_staging-{started:%Y%m%dT%H%M%S}"
        doc, pages = ingest.load(pdf, str(staging), year)
        ctx = extract.extract_document(doc, pages, llm)
    extract_model = getattr(llm, "model_id", "n/a") if not from_context else "n/a (context)"

    with ThreadPoolExecutor(max_workers=2) as ex:  # deterministic ∥ AI-assisted
        f_rules = ex.submit(rules.run_rules, ctx)
        f_vision = ex.submit(vision_checks.run_vision_checks, ctx, llm)
        findings = aggregate.aggregate(f_rules.result() + f_vision.result())

    run_id = f"{ctx.document.id[:8]}-{started:%Y%m%dT%H%M%S}"
    run_dir = Path(out) / run_id
    if not from_context:
        staging.rename(run_dir)
        for p in ctx.pages:
            p.path = str(run_dir / Path(p.path).name)

    result = RunResult(
        run_id=run_id,
        started_at=started,
        duration_s=round(time.perf_counter() - t0, 2),
        mode="context" if from_context else mode,
        context=ctx,
        findings=findings,
        versions={
            "model": extract_model,
            "extract_model": extract_model,
            "vision_model": ", ".join(
                sorted({f.model_version for f in findings if f.check_id.startswith("V-") and f.model_version})
            ),
            "extract_prompt": extract.PROMPT_VERSION,
            "rules": RULES_VERSION,
        },
        llm_usage=dict(getattr(llm, "usage", {}) or {}),
    )
    report.write_report(result, str(run_dir))
    return result
