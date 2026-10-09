"""FlyerCheck CLI."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import typer

from flyercheck.domain.models import GoldenSet, RunResult

app = typer.Typer(add_completion=False, help="AI-assisted consistency validation for promotional flyers.")


@app.command("run")
def run_cmd(
    pdf: str = typer.Argument(..., help="Flyer PDF/PNG/JPG"),
    out: str = typer.Option("out", help="Output directory"),
    mode: str = typer.Option("replay", help="replay | record | live"),
    year: int | None = typer.Option(None, help="Campaign year (overrides PDF metadata)"),
    from_context: str | None = typer.Option(None, help="Skip extraction; use a DocumentContext JSON"),
) -> None:
    """Validate a flyer and write findings.json + report.html."""
    from flyercheck import pipeline

    res = pipeline.run(pdf, out=out, mode=mode, year=year, from_context=from_context)
    counts = Counter(f.status.value for f in res.findings)
    order = ["fail", "needs_review", "error", "not_evaluable", "pass"]
    summary = " · ".join(f"{counts[s]} {s}" for s in order if counts[s])
    typer.echo(f"✔ {len(res.context.offers)} offers · {summary}   ({res.mode}, {res.duration_s}s)")
    run_dir = Path(out) / res.run_id
    typer.echo(f"→ {run_dir / 'findings.json'}\n→ {run_dir / 'report.html'}")


@app.command("eval")
def eval_cmd(
    findings: str = typer.Argument(..., help="findings.json from a run"),
    golden: str = typer.Argument("data/golden/designer.json", help="Golden label file"),
) -> None:
    """Score a run against golden labels (per-category precision/recall)."""
    from flyercheck.evaluation import evaluate, format_eval

    res = RunResult.model_validate_json(Path(findings).read_text())
    gold = GoldenSet.model_validate_json(Path(golden).read_text())
    typer.echo(format_eval(evaluate(res.findings, gold)))


if __name__ == "__main__":
    app()
