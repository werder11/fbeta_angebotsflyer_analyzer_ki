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
    provider: str = typer.Option("gemini", help="gemini | azure"),
    reference: str | None = typer.Option(None, help="Reference price CSV for R-08 (master-data check)"),
) -> None:
    """Validate a flyer and write findings.json + report.html."""
    import os

    from flyercheck import pipeline
    from flyercheck.reference import ENV_VAR

    if reference:
        os.environ[ENV_VAR] = reference
    res = pipeline.run(pdf, out=out, mode=mode, year=year, from_context=from_context, provider=provider)
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


@app.command("mutate-eval")
def mutate_eval_cmd(
    context: str = typer.Argument("tests/fixtures/designer_context.json", help="Normalized DocumentContext JSON"),
) -> None:
    """Seed synthetic defects into a context and measure rule detection (per operator)."""
    from flyercheck.domain.models import DocumentContext
    from flyercheck.evaluation.mutate import format_mutation_eval, run_mutation_eval

    ctx = DocumentContext.model_validate_json(Path(context).read_text())
    typer.echo(format_mutation_eval(run_mutation_eval(ctx)))


@app.command("serve")
def serve_cmd(host: str = "127.0.0.1", port: int = 8000, out: str = "out") -> None:
    """Run the REST API (validations, findings, review decisions)."""
    import uvicorn

    from flyercheck.api import create_app

    uvicorn.run(create_app(out_dir=out), host=host, port=port)


if __name__ == "__main__":
    app()
