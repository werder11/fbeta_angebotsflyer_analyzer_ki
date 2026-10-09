from decimal import Decimal

from flyercheck.domain.models import (
    BBox,
    Category,
    DocumentContext,
    Finding,
    Quantity,
    Severity,
    Status,
    Unit,
)
from flyercheck.rules import run_rules
from flyercheck.rules.base import REGISTRY
from flyercheck.rules.r_09_layout_association import check as r09
from flyercheck.rules.r_10_duplicate_offers import check as r10

NEW = {"R-09", "R-10"}


def _offer_ctx(ctx: DocumentContext, offer_id: str, **update) -> DocumentContext:
    offers = [o.model_copy(update=update) if o.id == offer_id else o for o in ctx.offers]
    return ctx.model_copy(update={"offers": offers})


def _by_id(findings: list[Finding], fid: str) -> Finding:
    hits = [f for f in findings if f.id == fid]
    assert len(hits) == 1, findings
    return hits[0]


def test_rules_auto_discovered():
    assert REGISTRY["R-09"] is r09
    assert REGISTRY["R-10"] is r10


def test_no_interference_with_existing_rules(designer_ctx):
    baseline = [f for cid, fn in REGISTRY.items() if cid not in NEW for f in fn(designer_ctx)]
    after = [f for f in run_rules(designer_ctx) if f.check_id not in NEW]
    assert [f.model_dump() for f in after] == [f.model_dump() for f in baseline]


def test_designer_r09_all_pass_and_r10_silent(designer_ctx):
    findings = r09(designer_ctx)
    assert len(findings) == len(designer_ctx.offers)
    for f in findings:
        assert f.status is Status.PASS, f
        assert f.category is Category.E05_ASSOCIATION and f.severity is Severity.HIGH
        assert f.id == f"R-09:{f.offer_id}" and f.rule_version == "R-09@1.0"
        assert f.evidence and f.evidence[0].bbox is not None
    assert r10(designer_ctx) == []


def test_overlapping_offers_need_review_pair(designer_ctx):
    a, b = designer_ctx.offers[0], designer_ctx.offers[1]
    ctx = _offer_ctx(designer_ctx, b.id, bbox=a.bbox, image_bbox=a.image_bbox)
    f = _by_id(r09(ctx), f"R-09:{a.id}-{b.id}")
    assert f.status is Status.NEEDS_REVIEW and f.offer_id is None
    assert f.observed["iou"] == "1.00"
    assert a.id in f.summary and b.id in f.summary
    assert len(f.evidence) == 2 and all(e.bbox is not None for e in f.evidence)


def test_overlap_on_different_pages_ignored(designer_ctx):
    a, b = designer_ctx.offers[0], designer_ctx.offers[1]
    ctx = _offer_ctx(designer_ctx, b.id, bbox=a.bbox, image_bbox=a.image_bbox, page=2)
    assert not [f for f in r09(ctx) if f.offer_id is None]


def test_image_outside_offer_box_needs_review(designer_ctx):
    ctx = _offer_ctx(designer_ctx, "o-1", bbox=BBox(x0=0.1, y0=0.1, x1=0.3, y1=0.3),
                     image_bbox=BBox(x0=0.25, y0=0.1, x1=0.45, y1=0.3))
    f = _by_id(r09(ctx), "R-09:o-1")
    assert f.status is Status.NEEDS_REVIEW
    assert f.observed["image_inside_pct"] == "25.0"
    assert "neighbouring offer" in f.summary


def test_implausible_area_needs_review(designer_ctx):
    tiny = _offer_ctx(designer_ctx, "o-1", bbox=BBox(x0=0.1, y0=0.1, x1=0.15, y1=0.15), image_bbox=None)
    assert _by_id(r09(tiny), "R-09:o-1").status is Status.NEEDS_REVIEW
    huge = _offer_ctx(designer_ctx, "o-1", bbox=BBox(x0=0, y0=0, x1=1, y1=0.8), image_bbox=None)
    f = _by_id(r09(huge), "R-09:o-1")
    assert f.status is Status.NEEDS_REVIEW and "80.0 %" in f.summary


def test_missing_bbox_not_evaluable(designer_ctx):
    f = _by_id(r09(_offer_ctx(designer_ctx, "o-3", bbox=None)), "R-09:o-3")
    assert f.status is Status.NOT_EVALUABLE


def test_duplicate_with_different_price_fails(designer_ctx):
    src = designer_ctx.offers[0]
    dup = src.model_copy(update={"id": "o-10", "page": 2, "product_name": f"  {src.product_name.upper()} ",
                                 "price": src.price + Decimal("0.30")})
    ctx = designer_ctx.model_copy(update={"offers": [*designer_ctx.offers, dup]})
    findings = r10(ctx)
    assert len(findings) == 1
    f = findings[0]
    assert f.status is Status.FAIL and f.severity is Severity.HIGH
    assert f.category is Category.E09_CROSS_REFERENCE and f.id == f"R-10:{src.id}"
    assert "1.69" in f.summary and "1.99" in f.summary
    assert {e.page for e in f.evidence} == {1, 2}


def test_duplicate_with_different_quantity_fails(designer_ctx):
    src = designer_ctx.offers[0]
    dup = src.model_copy(update={"id": "o-10", "quantity": Quantity(amount=Decimal(2), unit=Unit.KG)})
    ctx = designer_ctx.model_copy(update={"offers": [*designer_ctx.offers, dup]})
    assert r10(ctx)[0].status is Status.FAIL


def test_identical_duplicate_passes_info(designer_ctx):
    src = designer_ctx.offers[0]
    dup = src.model_copy(update={"id": "o-10", "page": 2})
    ctx = designer_ctx.model_copy(update={"offers": [*designer_ctx.offers, dup]})
    findings = r10(ctx)
    assert len(findings) == 1
    assert findings[0].status is Status.PASS and findings[0].severity is Severity.INFO
    assert "consistent" in findings[0].summary
