"""Dedupe and prioritize findings. Owned by track T3."""
from flyercheck.domain.models import Finding, Severity, Status

STATUS_ORDER = {s: i for i, s in enumerate(
    [Status.FAIL, Status.NEEDS_REVIEW, Status.ERROR, Status.NOT_EVALUABLE, Status.PASS])}
SEVERITY_ORDER = {s: i for i, s in enumerate(
    [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO])}


def aggregate(findings: list[Finding]) -> list[Finding]:
    """Dedupe by id (first wins), then sort by status, severity, id."""
    seen: dict[str, Finding] = {}
    for f in findings:
        seen.setdefault(f.id, f)
    return sorted(seen.values(), key=lambda f: (STATUS_ORDER[f.status], SEVERITY_ORDER[f.severity], f.id))
