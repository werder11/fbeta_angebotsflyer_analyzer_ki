"""Shared helpers for deterministic rules (no LLM, Decimal only)."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from flyercheck.domain.models import (
    BBox,
    Category,
    Evidence,
    Finding,
    Offer,
    Severity,
    Status,
)

CENT = Decimal("0.01")


def q2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(value: Decimal, places: str = "0.01") -> str:
    return str(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def pct(value: Decimal) -> str:
    """Printed percentage without trailing zeros, e.g. 42."""
    return f"{value.normalize():f}"


def make_finding(
    check_id: str,
    *,
    category: Category,
    severity: Severity,
    status: Status,
    summary: str,
    rule_version: str,
    offer: Offer | None = None,
    observed: dict[str, str] | None = None,
    expected: dict[str, str] | None = None,
    evidence: list[Evidence] | None = None,
    confidence: float = 1.0,
    page: int = 1,
    bbox: BBox | None = None,
    raw: str | None = None,
) -> Finding:
    if evidence is None:
        if offer is not None:
            evidence = [Evidence(page=offer.page, bbox=offer.bbox, raw=raw, source="flyer")]
        else:
            evidence = [Evidence(page=page, bbox=bbox, raw=raw, source="flyer")]
    return Finding(
        id=f"{check_id}:{offer.id if offer else 'doc'}",
        check_id=check_id,
        category=category,
        severity=severity,
        status=status,
        summary=summary,
        offer_id=offer.id if offer else None,
        offer_name=offer.product_name if offer else None,
        observed=observed or {},
        expected=expected or {},
        evidence=evidence,
        confidence=confidence,
        rule_version=rule_version,
    )
