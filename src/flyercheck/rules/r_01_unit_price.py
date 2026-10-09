"""R-01: printed unit price (Grundpreis) matches price / quantity."""
from __future__ import annotations

from decimal import Decimal

from flyercheck.domain.models import Category, DocumentContext, Finding, Severity, Status
from flyercheck.rules.base import register
from flyercheck.rules.r_common import fmt, make_finding, q2

CHECK_ID = "R-01"
RULE_VERSION = "R-01@1.0"
TOLERANCE = Decimal("0.01")


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    out: list[Finding] = []
    for o in ctx.offers:
        up = o.unit_price
        if up is None:
            continue
        basis = up.per_unit.value if up.per_amount == 1 else f"{up.per_amount.normalize():f} {up.per_unit.value}"
        common = {
            "category": Category.E03_ARITHMETIC,
            "severity": Severity.CRITICAL,
            "rule_version": RULE_VERSION,
            "offer": o,
            "raw": o.unit_price_raw,
        }
        observed = {"unit_price": f"{fmt(up.value)} €/{basis}"}
        if o.price is None or o.quantity is None:
            out.append(make_finding(
                CHECK_ID, status=Status.NOT_EVALUABLE,
                summary="Unit price printed but price or quantity missing; cannot verify.",
                observed=observed, **common))
            continue
        total, unit = o.quantity.total_base()
        if unit is not up.per_unit or total == 0:
            out.append(make_finding(
                CHECK_ID, status=Status.NOT_EVALUABLE,
                summary=f"Unit price basis {up.per_unit.value} does not match quantity unit {unit.value}.",
                observed=observed, **common))
            continue
        expected = q2(o.price / total * up.per_amount)
        formula = f"{fmt(o.price)} € / {total:.3f} {unit.value}"
        observed.update(price=fmt(o.price), quantity=f"{total:.3f} {unit.value}")
        exp = {"unit_price": f"{expected} €/{basis}", "formula": formula}
        if abs(expected - up.value) > TOLERANCE:
            out.append(make_finding(
                CHECK_ID, status=Status.FAIL,
                summary=(f"Printed unit price {fmt(up.value)} €/{basis} ≠ computed {expected} €/{basis} "
                         f"({formula})"),
                observed=observed, expected=exp, **common))
        else:
            out.append(make_finding(
                CHECK_ID, status=Status.PASS,
                summary=f"Printed unit price {fmt(up.value)} €/{basis} matches computed {expected} €/{basis}.",
                observed=observed, expected=exp, **common))
    return out
