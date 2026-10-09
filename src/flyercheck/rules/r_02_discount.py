"""R-02: printed discount percentage is not overstated (UWG)."""
from __future__ import annotations

import math
from decimal import Decimal

from flyercheck.domain.models import Category, DocumentContext, Finding, Offer, Severity, Status
from flyercheck.rules.base import register
from flyercheck.rules.r_common import fmt, make_finding, pct

CHECK_ID = "R-02"
RULE_VERSION = "R-02@1.0"


def actual_discount(o: Offer) -> Decimal | None:
    if o.original_price is None or o.price is None or o.original_price == 0:
        return None
    return (o.original_price - o.price) / o.original_price * 100


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    out: list[Finding] = []
    for o in ctx.offers:
        if o.discount_pct is None or o.original_price is None or o.price is None:
            continue
        common = {
            "category": Category.E03_ARITHMETIC,
            "rule_version": RULE_VERSION,
            "offer": o,
            "raw": o.discount_raw,
        }
        printed = o.discount_pct
        observed = {"discount": f"-{pct(printed)}%", "price": fmt(o.price),
                    "original_price": fmt(o.original_price)}
        actual = actual_discount(o)
        if actual is None:
            out.append(make_finding(
                CHECK_ID, severity=Severity.HIGH, status=Status.NOT_EVALUABLE,
                summary="Original price is 0; discount cannot be computed.", observed=observed, **common))
            continue
        a = fmt(actual)
        expected = {"actual_discount": f"{a}%",
                    "formula": f"({fmt(o.original_price)} − {fmt(o.price)}) / {fmt(o.original_price)} × 100"}
        if printed > actual:
            out.append(make_finding(
                CHECK_ID, severity=Severity.HIGH, status=Status.FAIL,
                summary=(f"Printed discount -{pct(printed)}% overstates actual {a}% "
                         f"({fmt(o.original_price)} € → {fmt(o.price)} €)."),
                observed=observed, expected=expected, **common))
        elif printed < math.floor(actual):
            out.append(make_finding(
                CHECK_ID, severity=Severity.MEDIUM, status=Status.NEEDS_REVIEW,
                summary=f"Printed discount -{pct(printed)}% under-advertises actual {a}%.",
                observed=observed, expected=expected, **common))
        else:
            out.append(make_finding(
                CHECK_ID, severity=Severity.HIGH, status=Status.PASS,
                summary=f"Printed discount -{pct(printed)}% does not exceed actual {a}%.",
                observed=observed, expected=expected, **common))
    return out
