"""R-10: the same product offered more than once must carry the same price and quantity (E-09)."""
from __future__ import annotations

from flyercheck.domain.models import Category, DocumentContext, Evidence, Finding, Offer, Severity, Status
from flyercheck.rules.base import register
from flyercheck.rules.r_common import make_finding

CHECK_ID = "R-10"
RULE_VERSION = "R-10@1.0"


def _norm(name: str) -> str:
    return " ".join(name.casefold().split())


def _qty(o: Offer) -> str:
    if o.quantity is None:
        return "-"
    q = o.quantity
    base = f"{q.amount.normalize():f} {q.unit.value}"
    return f"{q.pack_count} x {base}" if q.pack_count != 1 else base


def _price(o: Offer) -> str:
    return f"{o.price:.2f}" if o.price is not None else "-"


def _key(o: Offer) -> tuple[object, object]:
    total = o.quantity.total_base() if o.quantity is not None else None
    return (o.price.normalize() if o.price is not None else None,
            (total[0].normalize(), total[1]) if total else None)


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    groups: dict[str, list[Offer]] = {}
    for o in ctx.offers:
        if o.product_name and o.product_name.strip():
            groups.setdefault(_norm(o.product_name), []).append(o)
    findings: list[Finding] = []
    for group in groups.values():
        if len(group) < 2:
            continue
        first = group[0]
        listing = "; ".join(f"{o.id} p.{o.page}: {_price(o)} EUR / {_qty(o)}" for o in group)
        observed = {o.id: f"page {o.page}, price {_price(o)}, quantity {_qty(o)}" for o in group}
        evidence = [Evidence(page=o.page, bbox=o.bbox, raw=o.price_raw or o.product_name, source="flyer")
                    for o in group]
        if len({_key(o) for o in group}) == 1:
            status, severity = Status.PASS, Severity.INFO
            summary = f'Repeated offer, consistent: "{first.product_name}" appears {len(group)}x ({listing}).'
        else:
            status, severity = Status.FAIL, Severity.HIGH
            summary = (f'Inconsistent duplicate: "{first.product_name}" appears {len(group)}x '
                       f"with differing price/quantity ({listing}).")
        findings.append(make_finding(
            CHECK_ID, offer=first, category=Category.E09_CROSS_REFERENCE, severity=severity, status=status,
            summary=summary, rule_version=RULE_VERSION, observed=observed,
            expected={"consistency": "same price and quantity for every occurrence"}, evidence=evidence))
    return findings
