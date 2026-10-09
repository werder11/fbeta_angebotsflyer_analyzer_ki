"""R-09: layout association sanity (E-05). Deterministic geometry check behind ADR-0002's grouping step."""
from __future__ import annotations

from itertools import combinations

from flyercheck.domain.models import BBox, Category, DocumentContext, Evidence, Finding, Severity, Status
from flyercheck.rules.base import register
from flyercheck.rules.r_common import make_finding

CHECK_ID = "R-09"
RULE_VERSION = "R-09@1.0"

MIN_IMAGE_INSIDE = 0.85  # share of image_bbox area that must lie inside the offer bbox
MIN_AREA = 0.005  # offer bbox area as share of page (normalized coords -> page area = 1)
MAX_AREA = 0.60
MAX_IOU = 0.15

_COMMON = {"category": Category.E05_ASSOCIATION, "severity": Severity.HIGH, "rule_version": RULE_VERSION}


def _area(b: BBox) -> float:
    return max(0.0, b.x1 - b.x0) * max(0.0, b.y1 - b.y0)


def _inter(a: BBox, b: BBox) -> float:
    w = min(a.x1, b.x1) - max(a.x0, b.x0)
    h = min(a.y1, b.y1) - max(a.y0, b.y0)
    return w * h if w > 0 and h > 0 else 0.0


def _iou(a: BBox, b: BBox) -> float:
    inter = _inter(a, b)
    union = _area(a) + _area(b) - inter
    return inter / union if union > 0 else 0.0


def _box(b: BBox) -> str:
    return f"[{b.x0:.3f}, {b.y0:.3f}, {b.x1:.3f}, {b.y1:.3f}]"


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    findings: list[Finding] = []
    expected = {"image_inside_pct_min": f"{MIN_IMAGE_INSIDE * 100:.0f}",
                "area_pct_range": f"{MIN_AREA * 100:.1f}-{MAX_AREA * 100:.0f}"}
    for o in ctx.offers:
        if o.bbox is None:
            findings.append(make_finding(
                CHECK_ID, offer=o, status=Status.NOT_EVALUABLE,
                summary="Offer bounding box missing; layout association cannot be checked.", **_COMMON))
            continue
        area = _area(o.bbox)
        observed = {"bbox": _box(o.bbox), "area_pct": f"{area * 100:.1f}"}
        evidence = [Evidence(page=o.page, bbox=o.bbox, raw=o.product_name, source="flyer")]
        problems: list[str] = []
        if o.image_bbox is not None:
            img_area = _area(o.image_bbox)
            inside = _inter(o.bbox, o.image_bbox) / img_area if img_area > 0 else 0.0
            observed["image_bbox"] = _box(o.image_bbox)
            observed["image_inside_pct"] = f"{inside * 100:.1f}"
            evidence.append(Evidence(page=o.page, bbox=o.image_bbox, raw="product image", source="flyer"))
            if inside < MIN_IMAGE_INSIDE:
                problems.append(
                    f"only {inside * 100:.0f} % of the product image lies inside the offer box "
                    f"(min {MIN_IMAGE_INSIDE * 100:.0f} %); image may belong to a neighbouring offer")
        if not MIN_AREA <= area <= MAX_AREA:
            problems.append(
                f"offer box covers {area * 100:.1f} % of the page (plausible {MIN_AREA * 100:.1f}-"
                f"{MAX_AREA * 100:.0f} %); implausible grouping")
        if problems:
            status = Status.NEEDS_REVIEW
            summary = "Layout association doubtful: " + "; ".join(problems) + "."
        else:
            status = Status.PASS
            summary = f"Offer box plausible ({area * 100:.1f} % of page); product image inside offer box."
        findings.append(make_finding(CHECK_ID, offer=o, status=status, summary=summary, observed=observed,
                                     expected=expected, evidence=evidence, **_COMMON))

    boxed = [o for o in ctx.offers if o.bbox is not None]
    for a, b in combinations(boxed, 2):
        if a.page != b.page or a.bbox is None or b.bbox is None:
            continue
        iou = _iou(a.bbox, b.bbox)
        if iou <= MAX_IOU:
            continue
        f = make_finding(
            CHECK_ID, status=Status.NEEDS_REVIEW, page=a.page,
            summary=(f'Offer boxes of {a.id} "{a.product_name}" and {b.id} "{b.product_name}" overlap '
                     f"(IoU {iou:.2f} > {MAX_IOU:.2f}); grouping may be wrong."),
            observed={"offers": f"{a.id}, {b.id}", "iou": f"{iou:.2f}"},
            expected={"iou_max": f"{MAX_IOU:.2f}"},
            evidence=[Evidence(page=a.page, bbox=a.bbox, raw=a.product_name, source="flyer"),
                      Evidence(page=b.page, bbox=b.bbox, raw=b.product_name, source="flyer")],
            **_COMMON)
        findings.append(f.model_copy(update={"id": f"{CHECK_ID}:{a.id}-{b.id}"}))
    return findings
