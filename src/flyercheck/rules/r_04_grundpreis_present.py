"""R-04: a unit price (Grundpreis, PAngV) is printed where required."""
from __future__ import annotations

from decimal import Decimal

from flyercheck.domain.models import Category, DocumentContext, Finding, Severity, Status, Unit
from flyercheck.rules.base import register
from flyercheck.rules.r_common import fmt, make_finding, q2

CHECK_ID = "R-04"
RULE_VERSION = "R-04@1.0"
MASS_VOLUME = {Unit.G, Unit.KG, Unit.ML, Unit.L}
COUNTED = {Unit.SHEET: "sheets", Unit.PIECE: "pieces"}
COUNT_BASIS = Decimal(100)


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    out: list[Finding] = []
    for o in ctx.offers:
        q = o.quantity
        if q is None or o.unit_price is not None:
            continue
        total, unit = q.total_base()
        common = {
            "category": Category.E08_COMPLETENESS,
            "rule_version": RULE_VERSION,
            "offer": o,
            "raw": o.quantity_raw,
            "observed": {"unit_price": "missing", "quantity": o.quantity_raw or f"{total} {unit.value}"},
        }
        if q.unit in MASS_VOLUME:
            if total == 1:
                out.append(make_finding(
                    CHECK_ID, severity=Severity.HIGH, status=Status.PASS,
                    summary=f"Sold per 1 {unit.value}; the price is the unit price.", **common))
            elif o.price is None or total == 0:
                out.append(make_finding(
                    CHECK_ID, severity=Severity.HIGH, status=Status.FAIL,
                    summary=f"Unit price (€/{unit.value}) missing for pre-packed {o.quantity_raw}.",
                    expected={"unit_price": f"€/{unit.value} required"}, **common))
            else:
                computed = q2(o.price / total)
                out.append(make_finding(
                    CHECK_ID, severity=Severity.HIGH, status=Status.FAIL,
                    summary=(f"Unit price missing for {o.quantity_raw}; expected {computed} €/{unit.value} "
                             f"({fmt(o.price)} € / {total:.3f} {unit.value})."),
                    expected={"unit_price": f"{computed} €/{unit.value}"}, **common))
        elif q.unit in COUNTED:
            label = COUNTED[q.unit]
            exp = {"basis": f"policy decision (e.g. per 100 {label})"}
            summary = f"No unit price for {o.quantity_raw}; basis for {label} is a policy decision"
            if o.price is not None and total:
                computed = q2(o.price / total * COUNT_BASIS)
                exp["unit_price"] = f"{computed} €/100 {label}"
                summary += f" (computed {computed} €/100 {label})"
            out.append(make_finding(
                CHECK_ID, severity=Severity.MEDIUM, status=Status.NEEDS_REVIEW, summary=summary + ".",
                expected=exp, **common))
    return out
