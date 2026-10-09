from decimal import Decimal

import pytest

from flyercheck.domain.models import DocumentContext, Status
from flyercheck.evaluation.mutate import (
    OPERATORS,
    POSITIVE,
    build_baseline,
    format_mutation_eval,
    run_mutation_eval,
)
from flyercheck.rules import run_rules


@pytest.fixture
def result(designer_ctx: DocumentContext) -> dict:
    return run_mutation_eval(designer_ctx)


def test_baseline_has_no_positives(designer_ctx: DocumentContext) -> None:
    base = build_baseline(designer_ctx)
    positives = [f.id for f in run_rules(base) if f.status in POSITIVE]
    assert positives == []
    assert base.document.campaign_year == 2024
    assert base.page_refs == []
    pizza = next(o for o in base.offers if o.id == "o-6")
    assert pizza.unit_price.value == Decimal("5.28")
    assert pizza.discount_pct == Decimal(41)


def test_baseline_does_not_mutate_input(designer_ctx: DocumentContext) -> None:
    before = designer_ctx.model_dump_json()
    run_mutation_eval(designer_ctx)
    assert designer_ctx.model_dump_json() == before


def test_every_operator_yields_cases(designer_ctx: DocumentContext, result: dict) -> None:
    base = build_baseline(designer_ctx)
    for op in OPERATORS:
        assert list(op(base)), op.__name__
    assert len(result["per_operator"]) == len(OPERATORS)
    assert result["cases"] == sum(d["cases"] for d in result["per_operator"].values())
    assert result["baseline_residuals"] == []


def test_no_collateral_false_positives(result: dict) -> None:
    assert result["overall"]["collateral_fp"] == 0, result["collateral"]


def test_operators_other_than_price_change_fully_detected(result: dict) -> None:
    for op, d in result["per_operator"].items():
        if op != "M1_price_change":
            assert d["recall"] == 1.0, (op, result["misses"])


def test_price_change_misses_are_tolerance_blind_spot(result: dict) -> None:
    """Rule finding: R-01 tolerance (±0.01 on the 2-dp unit price) absorbs a +0.10 price change on large
    packs (9 l water: 0.44 → 0.4544; 1200 sheets per 100: 0.23 → 0.2408), so the seeded defect is missed."""
    misses = [m for m in result["misses"] if m.startswith("M1_price_change")]
    assert len(misses) == 2
    assert any("o-7" in m for m in misses) and any("o-9" in m for m in misses)


def test_overall_recall_is_perfect(result: dict) -> None:
    if result["overall"]["recall"] != 1.0:
        pytest.xfail("R-01 tolerance blind spot: M1 price_change undetected on large packs "
                     f"({len(result['misses'])} misses); finding about the rules, not the evaluator")
    assert result["overall"]["recall"] == 1.0


def test_detection_requires_expected_status(designer_ctx: DocumentContext) -> None:
    base = build_baseline(designer_ctx)
    findings = {(f.check_id, f.offer_id): f.status for f in run_rules(base)}
    assert findings[("R-01", "o-6")] is Status.PASS


def test_format_contains_recall(result: dict) -> None:
    text = format_mutation_eval(result)
    assert "recall" in text
    assert "OVERALL" in text
    assert "M9_quantity_unit_swap" in text
