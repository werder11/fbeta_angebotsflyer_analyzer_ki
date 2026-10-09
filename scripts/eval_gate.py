"""CI evaluation gate (ADR-0008).

Scores a run's findings.json against golden labels and fails (exit 1) when overall recall
or status agreement drops below the configured thresholds. An undefined metric (no labels
to score) counts as a failure.

    python scripts/eval_gate.py out/<run>/findings.json data/golden/designer.json \
        --min-recall 1.0 --min-agreement 0.9
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from flyercheck.domain.models import GoldenSet, RunResult
from flyercheck.evaluation import evaluate, format_eval


def _check(name: str, value: float | None, minimum: float) -> str | None:
    if value is None:
        return f"{name} is undefined (nothing to score), required >= {minimum:.2f}"
    if value < minimum:
        return f"{name} {value:.2f} < {minimum:.2f}"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when a run regresses against the golden set.")
    parser.add_argument("findings", help="findings.json from `flyercheck run`")
    parser.add_argument("golden", help="golden label file, e.g. data/golden/designer.json")
    parser.add_argument("--min-recall", type=float, default=1.0, help="minimum overall recall")
    parser.add_argument("--min-agreement", type=float, default=0.9, help="minimum status agreement")
    args = parser.parse_args(argv)

    run = RunResult.model_validate_json(Path(args.findings).read_text())
    golden = GoldenSet.model_validate_json(Path(args.golden).read_text())
    result = evaluate(run.findings, golden)
    print(format_eval(result))
    print()

    checks = (
        _check("overall recall", result["overall"]["recall"], args.min_recall),
        _check("status_agreement", result["status_agreement"], args.min_agreement),
    )
    failures = [msg for msg in checks if msg]
    if failures:
        for msg in failures:
            print(f"EVAL GATE FAILED: {msg}")
        return 1
    print(f"EVAL GATE PASSED (recall >= {args.min_recall:.2f}, status_agreement >= {args.min_agreement:.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
