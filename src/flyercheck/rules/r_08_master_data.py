"""R-08: prices vs. master data (E-02, P-06 "authoritative data wins").

Without a configured reference source ($FLYERCHECK_REFERENCE_CSV) the rule emits a single
doc-level not_evaluable finding. With a reference, each offer is compared against its record.
"""
from __future__ import annotations

from flyercheck.domain.models import Category, DocumentContext, Evidence, Finding, Offer, Severity, Status
from flyercheck.reference import ReferenceItem, ReferencePort, load_reference_from_env
from flyercheck.rules.base import register
from flyercheck.rules.r_common import fmt, make_finding

CHECK_ID = "R-08"
RULE_VERSION = "R-08@2.0"
# No-reference path is byte-identical to the pre-E7 rule (golden set + contract tests pin it).
RULE_VERSION_NO_REFERENCE = "R-08@1.0"
CAT = Category.E02_MASTER_DATA


def _evidence(offer: Offer, ref: ReferenceItem | None) -> list[Evidence]:
    ev = [Evidence(page=offer.page, bbox=offer.bbox, raw=offer.price_raw, source="flyer")]
    if ref is not None:
        ev.append(Evidence(page=offer.page, raw=f"{ref.source} {ref.sku}", source="reference"))
    return ev


def check_offers(ctx: DocumentContext, reference: ReferencePort) -> list[Finding]:
    out: list[Finding] = []
    for offer in ctx.offers:
        ref = reference.lookup(offer)
        if ref is None:
            out.append(make_finding(
                CHECK_ID, category=CAT, severity=Severity.MEDIUM, status=Status.NOT_EVALUABLE, offer=offer,
                summary=f"No reference record for '{offer.product_name}'.",
                observed={"product_name": offer.product_name or ""}, expected={"reference": "record"},
                evidence=_evidence(offer, None), rule_version=RULE_VERSION))
            continue
        exp = {"sku": ref.sku, "price": fmt(ref.price)}
        if offer.price is None:
            out.append(make_finding(
                CHECK_ID, category=CAT, severity=Severity.MEDIUM, status=Status.NOT_EVALUABLE, offer=offer,
                summary=f"Printed price unreadable; approved price {fmt(ref.price)} € (SKU {ref.sku}).",
                observed={"price_raw": offer.price_raw or ""}, expected=exp,
                evidence=_evidence(offer, ref), rule_version=RULE_VERSION))
        elif offer.price != ref.price:
            out.append(make_finding(
                CHECK_ID, category=CAT, severity=Severity.CRITICAL, status=Status.FAIL, offer=offer,
                summary=f"Printed price {fmt(offer.price)} € ≠ approved price {fmt(ref.price)} € (SKU {ref.sku}).",
                observed={"price": fmt(offer.price)}, expected=exp,
                evidence=_evidence(offer, ref), rule_version=RULE_VERSION))
        else:
            out.append(make_finding(
                CHECK_ID, category=CAT, severity=Severity.CRITICAL, status=Status.PASS, offer=offer,
                summary=f"Printed price {fmt(offer.price)} € matches master data (SKU {ref.sku}).",
                observed={"price": fmt(offer.price)}, expected=exp,
                evidence=_evidence(offer, ref), rule_version=RULE_VERSION))
        if (offer.original_price is not None and ref.original_price is not None
                and offer.original_price != ref.original_price):
            f = make_finding(
                CHECK_ID, category=CAT, severity=Severity.HIGH, status=Status.FAIL, offer=offer,
                summary=(f"Printed original price {fmt(offer.original_price)} € ≠ approved original price "
                         f"{fmt(ref.original_price)} € (SKU {ref.sku})."),
                observed={"original_price": fmt(offer.original_price)},
                expected={"sku": ref.sku, "original_price": fmt(ref.original_price)},
                evidence=_evidence(offer, ref), rule_version=RULE_VERSION)
            out.append(f.model_copy(update={"id": f"{f.id}:orig"}))
    return out


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    reference = load_reference_from_env()
    if reference is None:
        return [make_finding(
            CHECK_ID, category=CAT, severity=Severity.MEDIUM, status=Status.NOT_EVALUABLE,
            summary="No reference data source (PIM/price DB) configured.",
            observed={"offers": str(len(ctx.offers))}, expected={"reference": "PIM/price DB lookup"},
            rule_version=RULE_VERSION_NO_REFERENCE)]
    return check_offers(ctx, reference)
