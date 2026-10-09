"""R-02b: discount rounding convention is consistent across the document."""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

from flyercheck.domain.models import Category, DocumentContext, Evidence, Finding, Severity, Status
from flyercheck.rules.base import register
from flyercheck.rules.r_02_discount import actual_discount
from flyercheck.rules.r_common import fmt, make_finding, pct

CHECK_ID = "R-02b"
RULE_VERSION = "R-02b@1.0"


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    classes: dict[str, list[str]] = {"rounded_up": [], "floored": []}
    evidence: list[Evidence] = []
    for o in ctx.offers:
        if o.discount_pct is None:
            continue
        actual = actual_discount(o)
        if actual is None:
            continue
        printed = o.discount_pct
        label = f"{o.product_name or o.id} (-{pct(printed)}% vs {fmt(actual)}%)"
        if printed == math.ceil(actual) and printed > actual:
            cls = "rounded_up"
        elif printed == math.floor(actual) and printed < actual.quantize(Decimal(1), rounding=ROUND_HALF_UP):
            cls = "floored"
        else:
            continue
        classes[cls].append(label)
        evidence.append(Evidence(page=o.page, bbox=o.bbox, raw=o.discount_raw, source="flyer"))
    observed = {k: "; ".join(v) for k, v in classes.items() if v}
    common = {"category": Category.E03_ARITHMETIC, "severity": Severity.LOW, "rule_version": RULE_VERSION}
    if classes["rounded_up"] and classes["floored"]:
        return [make_finding(
            CHECK_ID, status=Status.NEEDS_REVIEW,
            summary=("Mixed discount rounding: rounded up for " + ", ".join(classes["rounded_up"])
                     + "; floored for " + ", ".join(classes["floored"]) + "."),
            observed=observed, expected={"rounding": "one consistent convention (floor recommended)"},
            evidence=evidence, **common)]
    return [make_finding(
        CHECK_ID, status=Status.PASS, summary="Discount rounding is consistent across the document.",
        observed=observed, evidence=evidence or None, **common)]
