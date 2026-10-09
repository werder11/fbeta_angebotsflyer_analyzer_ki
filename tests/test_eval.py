from flyercheck.domain.models import Category, Finding, GoldenLabel, GoldenSet, Severity, Status
from flyercheck.evaluation import POSITIVE, evaluate, format_eval

CATEGORY = {
    "V-01": Category.E01_PRODUCT_IMAGE,
    "R-01": Category.E03_ARITHMETIC,
    "R-02": Category.E03_ARITHMETIC,
    "R-02b": Category.E03_ARITHMETIC,
    "R-03": Category.E03_ARITHMETIC,
    "R-04": Category.E04_QUANTITY,
    "R-05": Category.E06_TEMPORAL,
    "R-07": Category.E09_CROSS_REFERENCE,
    "R-08": Category.E02_MASTER_DATA,
}


def _from_label(label: GoldenLabel, i: int) -> Finding:
    offer_id = None if label.offer_name is None else f"o-{i}"
    offer_name = None if label.offer_name is None else f"{label.offer_name} Produkt"
    return Finding(
        id=f"{label.check_id}:{offer_id or 'doc'}",
        check_id=label.check_id,
        category=CATEGORY[label.check_id],
        severity=label.severity or Severity.INFO,
        status=label.status,
        summary=label.note or "synthetic",
        offer_id=offer_id,
        offer_name=offer_name,
    )


def _perfect(golden: GoldenSet) -> list[Finding]:
    return [_from_label(lb, i) for i, lb in enumerate(golden.labels + golden.expected_passes)]


def test_perfect_predictions(golden):
    r = evaluate(_perfect(golden), golden)
    assert r["overall"]["precision"] == 1.0
    assert r["overall"]["recall"] == 1.0
    assert r["status_agreement"] == 1.0
    assert r["expected_pass_agreement"] == 1.0
    assert r["missing"] == [] and r["mismatched"] == []
    n_pos = sum(lb.status in POSITIVE for lb in golden.labels)
    assert r["overall"]["tp"] == n_pos


def test_dropping_a_positive_lowers_recall(golden):
    dropped = next(lb for lb in golden.labels if lb.status in POSITIVE)
    findings = [f for f in _perfect(golden)
                if not (f.check_id == dropped.check_id
                        and (f.offer_name or "").startswith(dropped.offer_name or ""))]
    r = evaluate(findings, golden)
    assert r["overall"]["recall"] < 1.0
    assert r["overall"]["fn"] == 1
    assert dropped.id in r["missing"]
    assert r["status_agreement"] < 1.0


def test_extra_fail_lowers_precision(golden):
    extra = Finding(id="R-03:o-99", check_id="R-03", category=Category.E03_ARITHMETIC,
                    severity=Severity.HIGH, status=Status.FAIL, summary="extra",
                    offer_id="o-99", offer_name="Unbekannt")
    r = evaluate(_perfect(golden) + [extra], golden)
    assert r["overall"]["precision"] < 1.0
    assert r["overall"]["fp"] == 1
    assert r["per_category"]["E03_arithmetic"]["fp"] == 1


def test_status_mismatch_and_case_insensitive_match(golden):
    findings = _perfect(golden)
    for f in findings:
        if f.offer_name:
            f.offer_name = f.offer_name.upper()
    passes = [f for f in findings if f.check_id == "R-01" and f.status is Status.PASS]
    passes[0].status = Status.NEEDS_REVIEW
    r = evaluate(findings, golden)
    assert r["missing"] == []
    assert len(r["mismatched"]) == 1 and r["mismatched"][0]["got"] == "needs_review"
    assert r["expected_pass_agreement"] < 1.0
    assert r["overall"]["fp"] == 1


def test_empty_findings_and_format(golden):
    r = evaluate([], golden)
    assert r["overall"]["precision"] is None
    assert r["overall"]["recall"] == 0.0
    assert "unmatched" in r["per_category"]
    text = format_eval(r)
    assert "precision" in text and "overall" in text and "—" in text
    assert "G-01" in text
    assert "precision" in format_eval(evaluate(_perfect(golden), golden))
