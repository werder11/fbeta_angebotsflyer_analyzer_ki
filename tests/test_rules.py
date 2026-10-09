from decimal import Decimal

import pytest

from flyercheck.domain.models import DocumentContext, Finding, GoldenLabel, Quantity, Status, Unit
from flyercheck.rules import run_rules
from flyercheck.rules.base import REGISTRY


def _match(findings: list[Finding], label: GoldenLabel) -> list[Finding]:
    out = [f for f in findings if f.check_id == label.check_id]
    if label.offer_name is None:
        return [f for f in out if f.offer_id is None]
    prefix = label.offer_name.lower()
    return [f for f in out if (f.offer_name or "").lower().startswith(prefix)]


def _offer_ctx(ctx: DocumentContext, offer_id: str, **update) -> DocumentContext:
    offers = [o.model_copy(update=update) if o.id == offer_id else o for o in ctx.offers]
    return ctx.model_copy(update={"offers": offers})


def _one(findings: list[Finding], check_id: str, offer_id: str | None = None) -> Finding:
    hits = [f for f in findings if f.check_id == check_id and f.offer_id == offer_id]
    assert len(hits) == 1, hits
    return hits[0]


def test_golden_rule_labels_reproduced(designer_ctx, golden):
    findings = run_rules(designer_ctx)
    labels = [g for g in golden.labels + golden.expected_passes if g.check_id.startswith("R-")]
    assert labels
    for label in labels:
        hits = _match(findings, label)
        assert len(hits) == 1, (label, hits)
        assert hits[0].status == label.status, (label, hits[0])
        if label.severity is not None:
            assert hits[0].severity == label.severity, (label, hits[0])


def test_findings_have_ids_versions_and_evidence(designer_ctx):
    findings = run_rules(designer_ctx)
    assert len({f.id for f in findings}) == len(findings)
    for f in findings:
        assert f.id == f"{f.check_id}:{f.offer_id or 'doc'}"
        assert f.rule_version == f"{f.check_id}@1.0"
        assert f.evidence
        assert f.status is not Status.ERROR


def test_r01_summary_has_numbers(designer_ctx):
    f = _one(run_rules(designer_ctx), "R-01", "o-6")
    assert "5.59" in f.summary and "5.28" in f.summary
    assert f.expected["unit_price"] == "5.28 €/kg"


def test_r04_expected_unit_prices(designer_ctx):
    findings = run_rules(designer_ctx)
    assert _one(findings, "R-04", "o-3").expected["unit_price"] == "29.90 €/kg"
    assert _one(findings, "R-04", "o-8").expected["unit_price"] == "9.90 €/kg"
    assert _one(findings, "R-04", "o-9").expected["unit_price"] == "0.23 €/100 sheets"
    assert _one(findings, "R-04", "o-1").status is Status.PASS


def test_r05_fail_lists_matching_years(designer_ctx):
    f = _one(run_rules(designer_ctx), "R-05")
    assert f.status is Status.FAIL
    assert f.expected["matching_years"] == "2024, 2030"
    assert f.expected["from_weekday"] == "Mi"
    assert f.confidence == 0.8


def test_r05_cli_year_confidence(designer_ctx):
    doc = designer_ctx.document.model_copy(update={"campaign_year_source": "cli"})
    f = _one(run_rules(designer_ctx.model_copy(update={"document": doc})), "R-05")
    assert f.confidence == 0.95


def test_r05_year_unknown_needs_review(designer_ctx):
    doc = designer_ctx.document.model_copy(update={"campaign_year": None, "campaign_year_source": None})
    f = _one(run_rules(designer_ctx.model_copy(update={"document": doc})), "R-05")
    assert f.status is Status.NEEDS_REVIEW
    assert "2024" in f.summary and "2030" in f.summary


def test_r05_matching_year_passes_and_reversed_dates_fail(designer_ctx):
    doc = designer_ctx.document.model_copy(update={"campaign_year": 2024})
    ctx = designer_ctx.model_copy(update={"document": doc})
    assert _one(run_rules(ctx), "R-05").status is Status.PASS
    v = designer_ctx.validity.model_copy(update={"until_day": 5, "until_weekday": "Sa"})
    f = _one(run_rules(ctx.model_copy(update={"validity": v})), "R-05")
    assert f.status is Status.FAIL


def test_r05_no_validity_not_evaluable(designer_ctx):
    f = _one(run_rules(designer_ctx.model_copy(update={"validity": None})), "R-05")
    assert f.status is Status.NOT_EVALUABLE


def test_r02_original_price_zero_not_evaluable(designer_ctx):
    ctx = _offer_ctx(designer_ctx, "o-2", original_price=Decimal(0))
    assert _one(run_rules(ctx), "R-02", "o-2").status is Status.NOT_EVALUABLE


def test_r02_under_advertised_needs_review(designer_ctx):
    ctx = _offer_ctx(designer_ctx, "o-2", discount_pct=Decimal(10))
    f = _one(run_rules(ctx), "R-02", "o-2")
    assert f.status is Status.NEEDS_REVIEW


def test_r02b_consistent_passes(designer_ctx):
    ctx = _offer_ctx(designer_ctx, "o-6", discount_pct=Decimal(41))
    assert _one(run_rules(ctx), "R-02b").status is Status.PASS


def test_r01_missing_quantity_not_evaluable_and_r06_fails(designer_ctx):
    findings = run_rules(_offer_ctx(designer_ctx, "o-5", quantity=None))
    assert _one(findings, "R-01", "o-5").status is Status.NOT_EVALUABLE
    r06 = _one(findings, "R-06", "o-5")
    assert r06.status is Status.FAIL and "quantity" in r06.summary


def test_r03_deposit_missing_and_wrong(designer_ctx):
    assert _one(run_rules(_offer_ctx(designer_ctx, "o-7", deposit=None)), "R-03", "o-7").status is Status.FAIL
    wrong = _offer_ctx(designer_ctx, "o-7", deposit=Decimal("0.90"))
    assert _one(run_rules(wrong), "R-03", "o-7").status is Status.FAIL


def test_r04_pieces_needs_review(designer_ctx):
    q = Quantity(amount=Decimal(4), unit=Unit.PIECE)
    f = _one(run_rules(_offer_ctx(designer_ctx, "o-9", quantity=q)), "R-04", "o-9")
    assert f.status is Status.NEEDS_REVIEW


def test_r07_no_refs_no_finding_and_valid_ref_passes(designer_ctx):
    assert not [f for f in run_rules(designer_ctx.model_copy(update={"page_refs": []})) if f.check_id == "R-07"]
    doc = designer_ctx.document.model_copy(update={"page_count": 8})
    assert _one(run_rules(designer_ctx.model_copy(update={"document": doc})), "R-07").status is Status.PASS


def test_crashing_rule_becomes_error(designer_ctx, monkeypatch):
    def boom(ctx):
        raise RuntimeError("kaputt")

    monkeypatch.setitem(REGISTRY, "R-99", boom)
    findings = run_rules(designer_ctx)
    err = _one(findings, "R-99")
    assert err.status is Status.ERROR and "kaputt" in err.summary
    assert any(f.check_id == "R-01" for f in findings)


@pytest.mark.parametrize("check_id", ["R-01", "R-02", "R-02b", "R-03", "R-04", "R-05", "R-06", "R-07", "R-08"])
def test_all_rules_registered(check_id):
    assert check_id in REGISTRY
