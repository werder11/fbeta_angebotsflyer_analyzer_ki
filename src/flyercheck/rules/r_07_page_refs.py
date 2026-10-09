"""R-07: page references point to existing pages."""
from __future__ import annotations

from flyercheck.domain.models import Category, DocumentContext, Evidence, Finding, Severity, Status
from flyercheck.rules.base import register
from flyercheck.rules.r_common import make_finding

CHECK_ID = "R-07"
RULE_VERSION = "R-07@1.0"


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    refs = ctx.page_refs
    if not refs:
        return []
    n = ctx.document.page_count
    bad = [r for r in refs if r.target_page > n]
    common = {
        "category": Category.E09_CROSS_REFERENCE,
        "severity": Severity.MEDIUM,
        "rule_version": RULE_VERSION,
        "observed": {"references": "; ".join(f"{r.raw} → page {r.target_page}" for r in refs)},
        "expected": {"max_page": str(n)},
        "evidence": [Evidence(page=r.page, bbox=r.bbox, raw=r.raw, source="flyer") for r in (bad or refs)],
    }
    if bad:
        return [make_finding(
            CHECK_ID, status=Status.FAIL,
            summary="Page reference out of range: "
            + "; ".join(f'"{r.raw}" → page {r.target_page} of {n}' for r in bad) + ".",
            **common)]
    return [make_finding(CHECK_ID, status=Status.PASS,
                         summary=f"All {len(refs)} page reference(s) resolve within {n} page(s).", **common)]
