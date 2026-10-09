from flyercheck.aggregate import aggregate
from flyercheck.domain.models import Category, Finding, Severity, Status
from flyercheck.rules import run_rules


def _f(fid: str, status: Status, severity: Severity, summary: str = "x") -> Finding:
    check_id, _, _ = fid.partition(":")
    return Finding(id=fid, check_id=check_id, category=Category.E03_ARITHMETIC,
                   severity=severity, status=status, summary=summary)


def test_dedupe_keeps_first():
    out = aggregate([_f("R-01:o-1", Status.FAIL, Severity.HIGH, "first"),
                     _f("R-01:o-1", Status.PASS, Severity.LOW, "second")])
    assert len(out) == 1 and out[0].summary == "first"


def test_sort_status_then_severity_then_id():
    findings = [
        _f("R-08:doc", Status.PASS, Severity.CRITICAL),
        _f("R-07:doc", Status.NOT_EVALUABLE, Severity.CRITICAL),
        _f("R-06:doc", Status.ERROR, Severity.CRITICAL),
        _f("R-05:doc", Status.NEEDS_REVIEW, Severity.CRITICAL),
        _f("R-04:b", Status.FAIL, Severity.LOW),
        _f("R-04:a", Status.FAIL, Severity.LOW),
        _f("R-03:doc", Status.FAIL, Severity.CRITICAL),
    ]
    assert [f.id for f in aggregate(findings)] == [
        "R-03:doc", "R-04:a", "R-04:b", "R-05:doc", "R-06:doc", "R-07:doc", "R-08:doc"]


def test_aggregate_designer(designer_ctx):
    out = aggregate(run_rules(designer_ctx))
    assert out[0].id == "R-01:o-6"
    assert out[-1].status is Status.PASS
    assert aggregate([]) == []
