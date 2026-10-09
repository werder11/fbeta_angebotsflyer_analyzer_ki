"""R-06: every offer has product name, price and quantity."""
from __future__ import annotations

from flyercheck.domain.models import Category, DocumentContext, Finding, Severity, Status
from flyercheck.rules.base import register
from flyercheck.rules.r_common import make_finding

CHECK_ID = "R-06"
RULE_VERSION = "R-06@1.0"
FIELDS = ("product_name", "price", "quantity")


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    out: list[Finding] = []
    for o in ctx.offers:
        missing = [f for f in FIELDS if getattr(o, f) is None]
        common = {
            "category": Category.E08_COMPLETENESS,
            "severity": Severity.HIGH,
            "rule_version": RULE_VERSION,
            "offer": o,
            "raw": o.price_raw,
            "observed": {f: ("missing" if f in missing else "present") for f in FIELDS},
        }
        if missing:
            out.append(make_finding(
                CHECK_ID, status=Status.FAIL,
                summary=f"Offer {o.id} is missing required field(s): {', '.join(missing)}.",
                expected=dict.fromkeys(missing, "present"), **common))
        else:
            out.append(make_finding(CHECK_ID, status=Status.PASS,
                                    summary="Product name, price and quantity present.", **common))
    return out
