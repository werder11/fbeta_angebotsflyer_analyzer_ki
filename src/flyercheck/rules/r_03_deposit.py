"""R-03: deposit (Pfand) present and plausible for bottled/canned beverages."""
from __future__ import annotations

import re
from decimal import Decimal

from flyercheck.domain.models import Category, DocumentContext, Finding, Severity, Status, Unit
from flyercheck.rules.base import register
from flyercheck.rules.r_common import fmt, make_finding

CHECK_ID = "R-03"
RULE_VERSION = "R-03@1.0"
DEPOSIT_PER_ITEM = Decimal("0.25")
CONTAINER = re.compile(r"pet|flasche|dose", re.IGNORECASE)


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    out: list[Finding] = []
    for o in ctx.offers:
        q = o.quantity
        if q is None or q.unit not in (Unit.L, Unit.ML) or not CONTAINER.search(o.quantity_raw or ""):
            continue
        expected = DEPOSIT_PER_ITEM * q.pack_count
        calc = f"{q.pack_count} × {fmt(DEPOSIT_PER_ITEM)} €"
        common = {
            "category": Category.E08_COMPLETENESS,
            "severity": Severity.HIGH,
            "rule_version": RULE_VERSION,
            "offer": o,
            "raw": o.deposit_raw or o.quantity_raw,
            "expected": {"deposit": f"{fmt(expected)} € ({calc})"},
        }
        observed = {"deposit": fmt(o.deposit) if o.deposit is not None else "missing",
                    "quantity": o.quantity_raw or ""}
        if o.deposit is None:
            out.append(make_finding(
                CHECK_ID, status=Status.FAIL,
                summary=f"Deposit missing for {o.quantity_raw}; expected {fmt(expected)} € ({calc}).",
                observed=observed, **common))
        elif o.deposit != expected:
            out.append(make_finding(
                CHECK_ID, status=Status.FAIL,
                summary=f"Deposit {fmt(o.deposit)} € ≠ expected {fmt(expected)} € ({calc}).",
                observed=observed, **common))
        else:
            out.append(make_finding(
                CHECK_ID, status=Status.PASS,
                summary=f"Deposit {fmt(o.deposit)} € matches {calc}.", observed=observed, **common))
    return out
