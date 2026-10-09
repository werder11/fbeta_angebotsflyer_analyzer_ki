"""V-01: does the product photo plausibly depict the advertised product?"""
from __future__ import annotations

import io
import os
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

from flyercheck.domain.models import (
    BBox,
    Category,
    DocumentContext,
    Evidence,
    Finding,
    Offer,
    Severity,
    Status,
)
from flyercheck.llm.port import LLMPort
from flyercheck.vision_checks.prompts import (
    V01_BLIND_PROMPT,
    V01_BLIND_SCHEMA,
    V01_COMPARE_PROMPT,
    V01_COMPARE_SCHEMA,
    V01_PROMPT,
    V01_SCHEMA,
    V01_TWO_STEP_VERSION,
    V01_VERSION,
)

CHECK_ID = "V-01"
MARGIN = 0.05
FAIL_CONFIDENCE = 0.7
MAX_WORKERS = 3
TWO_STEP_ENV = "FLYERCHECK_V01_TWO_STEP"


def two_step_enabled() -> bool:
    return os.environ.get(TWO_STEP_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def crop_png(page_path: str, bbox: BBox, margin: float = MARGIN) -> bytes:
    """Crop normalized bbox plus `margin` (of bbox size) on each side, clamped to the image; PNG bytes."""
    with Image.open(page_path) as img:
        w, h = img.size
        bw, bh = bbox.x1 - bbox.x0, bbox.y1 - bbox.y0
        x0 = max(0.0, bbox.x0 - margin * bw)
        y0 = max(0.0, bbox.y0 - margin * bh)
        x1 = min(1.0, bbox.x1 + margin * bw)
        y1 = min(1.0, bbox.y1 + margin * bh)
        left, top = min(w - 1, int(x0 * w)), min(h - 1, int(y0 * h))
        right = min(w, max(left + 1, round(x1 * w)))
        bottom = min(h, max(top + 1, round(y1 * h)))
        crop = img.convert("RGB").crop((left, top, right, bottom))
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        return buf.getvalue()


def _description(offer: Offer) -> str:
    parts = ([offer.brand] if offer.brand else []) + list(offer.description_lines)
    return ", ".join(p for p in parts if p) or "no further description"


def _ask_single(png: bytes, name: str, offer: Offer, llm: LLMPort) -> dict:
    """Default MVP: one vision call; prompt/schema/crop byte-identical to the recordings."""
    prompt = V01_PROMPT.format(product_name=name, description=_description(offer))
    return llm.generate_json(prompt, [png], V01_SCHEMA, purpose="vision")


def _ask_two_step(png: bytes, name: str, offer: Offer, llm: LLMPort) -> dict:
    """Opt-in: blind description of the crop, then a text-only comparison (no image)."""
    blind = llm.generate_json(V01_BLIND_PROMPT, [png], V01_BLIND_SCHEMA, purpose="vision")
    depicted = str(blind.get("depicted_object", ""))
    depicted_cat = str(blind.get("depicted_category", ""))
    prompt = V01_COMPARE_PROMPT.format(
        depicted_object=depicted,
        depicted_category=depicted_cat,
        product_name=name,
        description=_description(offer),
    )
    cmp = llm.generate_json(prompt, [], V01_COMPARE_SCHEMA, purpose="vision")
    return {**cmp, "depicted_object": depicted, "depicted_category": depicted_cat}


def check_offer(
    ctx: DocumentContext, offer: Offer, llm: LLMPort, *, two_step: bool = False
) -> Finding:
    bbox = offer.image_bbox or offer.bbox
    name = offer.product_name or "(unnamed offer)"
    base = {
        "id": f"{CHECK_ID}:{offer.id}",
        "check_id": CHECK_ID,
        "category": Category.E01_PRODUCT_IMAGE,
        "severity": Severity.CRITICAL,
        "offer_id": offer.id,
        "offer_name": offer.product_name,
        "evidence": [Evidence(page=offer.page, bbox=bbox, source="model")],
        "rule_version": V01_TWO_STEP_VERSION if two_step else V01_VERSION,
        "model_version": getattr(llm, "model_id", None),
    }
    if bbox is None:
        return Finding(
            **base,
            status=Status.NOT_EVALUABLE,
            summary=f"No image/offer bbox for '{name}'; image-text check not possible",
        )
    try:
        page = next((p for p in ctx.pages if p.number == offer.page), None) or ctx.pages[offer.page - 1]
        png = crop_png(page.path, bbox)
        ask = _ask_two_step if two_step else _ask_single
        resp = ask(png, name, offer, llm)
        matches = str(resp.get("matches", "unclear")).lower()
        confidence = max(0.0, min(1.0, float(resp.get("confidence", 0.0))))
        depicted = str(resp.get("depicted_object", ""))
        depicted_cat = str(resp.get("depicted_category", ""))
        advertised_cat = str(resp.get("advertised_category", ""))
        reason = str(resp.get("reason", ""))
    except Exception as exc:  # noqa: BLE001 - any failure becomes an ERROR finding
        return Finding(
            **base,
            status=Status.ERROR,
            summary=f"V-01 failed for '{name}': {type(exc).__name__}: {exc}",
            confidence=0.0,
        )

    if matches == "no" and confidence >= FAIL_CONFIDENCE:
        status = Status.FAIL
        summary = f"Image shows '{depicted}' but offer advertises '{name}' ({advertised_cat})"
    elif matches == "yes" and confidence >= FAIL_CONFIDENCE:
        status = Status.PASS
        summary = f"Image of '{depicted}' matches '{name}'"
    else:
        status = Status.NEEDS_REVIEW
        summary = (
            f"Unclear whether image ('{depicted}') matches '{name}' "
            f"(model: {matches}, confidence {confidence:.2f})"
        )
    if reason:
        summary += f" — {reason}"
    return Finding(
        **base,
        status=status,
        summary=summary,
        observed={
            "depicted": depicted,
            "depicted_category": depicted_cat,
            "extraction_image_description": offer.image_description or "",
        },
        expected={"advertised": name, "advertised_category": advertised_cat},
        confidence=confidence,
    )


def run_v01(ctx: DocumentContext, llm: LLMPort) -> list[Finding]:
    """One vision call per offer (two with FLYERCHECK_V01_TWO_STEP=1), max 3 offers in parallel;
    output order equals offer order."""
    if not ctx.offers:
        return []
    two_step = two_step_enabled()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        return list(pool.map(lambda o: check_offer(ctx, o, llm, two_step=two_step), ctx.offers))
