"""V-02: claims register. Deterministic, no LLM.

Advertising claims (origin, sustainability/certification, quality) cannot be verified without a
reference source (certification/origin registry). V-02 makes them visible as NOT_EVALUABLE
instead of silently skipping them or hallucinating their truth (coverage honesty, ADR-0005).
"""
from __future__ import annotations

import re

from flyercheck.domain.models import (
    BBox,
    Category,
    DocumentContext,
    Evidence,
    Finding,
    Severity,
    Status,
)

CHECK_ID = "V-02"
V02_VERSION = "V-02@1.0"

# (claim type, case-insensitive pattern). Word boundaries avoid hits inside other words or
# domains (e.g. "frischfeld-markt.de"); "aus \w+" is the catch-all for origin claims.
CLAIM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (kind, re.compile(pat, re.IGNORECASE))
    for kind, pat in [
        ("origin", r"\baus der region\b"),
        ("origin", r"\bregional\b"),
        ("origin", r"\baus den niederlanden\b"),
        ("origin", r"\baus deutschland\b"),
        ("origin", r"\baus \w+"),
        ("sustainability", r"\bnachhaltig\w*"),
        ("certification", r"\basc\b"),
        ("certification", r"\bmsc\b"),
        ("certification", r"\bbio\b"),
        ("certification", r"\bfairtrade\b"),
        ("sustainability", r"\bverantwortungsvolle\w* fischzucht\b"),
        ("sustainability", r"\baquakultur\b"),
        ("quality", r"\bklasse i\b"),
        ("quality", r"\b100\s*%\s*arabica\b"),
        ("quality", r"\bfrisch\b"),
    ]
]


def find_claims(text: str) -> list[tuple[str, str]]:
    """Return [(claim_type, first matched keyword)] for `text`, one entry per claim type."""
    hits: dict[str, str] = {}
    for kind, pat in CLAIM_PATTERNS:
        if kind in hits:
            continue
        m = pat.search(text)
        if m:
            hits[kind] = m.group(0)
    return list(hits.items())


def _finding(
    n: int,
    owner: str,
    text: str,
    claims: list[tuple[str, str]],
    page: int,
    bbox: BBox | None,
    offer_id: str | None = None,
    offer_name: str | None = None,
) -> Finding:
    return Finding(
        id=f"{CHECK_ID}:{owner}:{n}",
        check_id=CHECK_ID,
        category=Category.E07_SEMANTIC,
        severity=Severity.MEDIUM,
        status=Status.NOT_EVALUABLE,
        summary=(
            f"Claim '{text}' requires a reference source "
            "(certification/origin registry) — not verified"
        ),
        offer_id=offer_id,
        offer_name=offer_name,
        observed={
            "claim": text,
            "claim_types": ", ".join(k for k, _ in claims),
            "keywords": ", ".join(kw for _, kw in claims),
        },
        evidence=[Evidence(page=page, bbox=bbox, raw=text, source="flyer")],
        rule_version=V02_VERSION,
    )


def _scan(texts: list[str]) -> list[tuple[str, list[tuple[str, str]], int]]:
    """Claim-bearing texts (deduped case-insensitively) with their claims and source index."""
    out: list[tuple[str, list[tuple[str, str]], int]] = []
    seen: set[str] = set()
    for i, raw in enumerate(texts):
        text = (raw or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        claims = find_claims(text)
        if claims:
            seen.add(key)
            out.append((text, claims, i))
    return out


def run_v02(ctx: DocumentContext) -> list[Finding]:
    findings: list[Finding] = []
    for offer in ctx.offers:
        texts = [offer.product_name or "", *offer.badges, *offer.description_lines]
        for n, (text, claims, _) in enumerate(_scan(texts), start=1):
            findings.append(
                _finding(n, offer.id, text, claims, offer.page, offer.bbox, offer.id, offer.product_name)
            )
    blocks = ctx.text_blocks
    for n, (text, claims, i) in enumerate(_scan([b.text for b in blocks]), start=1):
        findings.append(_finding(n, "doc", text, claims, blocks[i].page, blocks[i].bbox))
    return findings
