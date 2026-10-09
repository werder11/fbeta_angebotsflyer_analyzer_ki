"""Pure parsing of raw flyer strings (prices, quantities, unit prices, validity). Owned by track T2.

All functions are deterministic, use Decimal only, and return None when a value is absent or unparseable.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from flyercheck.domain.models import PageRef, Quantity, TextBlock, Unit, UnitPrice, Validity

_NUM = r"\d+(?:[.,]\d+)?"

_UNITS: dict[str, Unit] = {
    "g": Unit.G,
    "gr": Unit.G,
    "kg": Unit.KG,
    "ml": Unit.ML,
    "l": Unit.L,
    "ltr": Unit.L,
    "stück": Unit.PIECE,
    "stk": Unit.PIECE,
    "st": Unit.PIECE,
    "blatt": Unit.SHEET,
}
_UNIT_RE = r"(kg|gr|g|ml|ltr|l|stück|stk|st|blatt)\b\.?"


def _dec(s: str) -> Decimal | None:
    try:
        return Decimal(s.replace(".", "").replace(",", ".") if "," in s else s)
    except InvalidOperation:
        return None


def parse_price(raw: str | None) -> Decimal | None:
    """"1,69" → Decimal("1.69"); "-" / "" / None → None."""
    if not raw:
        return None
    m = re.search(_NUM, raw)
    return _dec(m.group(0)) if m else None


def parse_discount(raw: str | None) -> Decimal | None:
    """"-42%" → Decimal("42") (always positive)."""
    if not raw:
        return None
    m = re.search(rf"({_NUM})\s*%", raw)
    return _dec(m.group(1)) if m else None


def parse_quantity(raw: str | None) -> Quantity | None:
    """"6 x 1,5 l PET-Flaschen" → (1.5, l, 6); "8 x 150 Blatt" → (150, sheet, 8); "320 g Packung" → (320, g)."""
    if not raw:
        return None
    s = raw.strip().lower()
    m = re.search(rf"(\d+)\s*[x×]\s*({_NUM})\s*{_UNIT_RE}", s)
    if m:
        amount = _dec(m.group(2))
        if amount is None:
            return None
        return Quantity(amount=amount, unit=_UNITS[m.group(3)], pack_count=int(m.group(1)))
    m = re.search(rf"({_NUM})\s*{_UNIT_RE}", s)
    if m:
        amount = _dec(m.group(1))
        return None if amount is None else Quantity(amount=amount, unit=_UNITS[m.group(2)])
    return None


def parse_unit_price(raw: str | None) -> UnitPrice | None:
    """"(1 kg = 5,59)" / "1 l = 0,44" → UnitPrice(value, per_amount, per_unit)."""
    if not raw:
        return None
    m = re.search(rf"({_NUM})?\s*{_UNIT_RE}\s*=\s*({_NUM})", raw.lower())
    if not m:
        return None
    per_amount = _dec(m.group(1)) if m.group(1) else Decimal(1)
    value = _dec(m.group(3))
    if per_amount is None or value is None:
        return None
    return UnitPrice(value=value, per_amount=per_amount, per_unit=_UNITS[m.group(2)])


def parse_deposit(raw: str | None) -> Decimal | None:
    """"zzgl. 1,50 Pfand" → Decimal("1.50")."""
    return parse_price(raw)


_WD = r"(Mo|Di|Mi|Do|Fr|Sa|So)\.?"
_DATE = r"(\d{1,2})\.(\d{1,2})\.?"


def parse_validity(raw: str | None) -> Validity | None:
    """"Gültig von Mo. 07.10. bis Sa. 12.10." → Validity(from 7.10. Mo, until 12.10. Sa)."""
    if not raw:
        return None
    v = Validity(raw=raw)
    m = re.search(rf"(?:{_WD}\s*)?{_DATE}\s*(?:bis|-|–)\s*(?:{_WD}\s*)?{_DATE}", raw)
    if m:
        v.from_weekday, v.from_day, v.from_month = m.group(1), int(m.group(2)), int(m.group(3))
        v.until_weekday, v.until_day, v.until_month = m.group(4), int(m.group(5)), int(m.group(6))
        return v
    m = re.search(rf"(?:{_WD}\s*)?{_DATE}", raw)
    if m:
        v.from_weekday, v.from_day, v.from_month = m.group(1), int(m.group(2)), int(m.group(3))
    return v


_PAGE_REF = re.compile(r"Seite\s+(\d+)")


def find_page_refs(blocks: list[TextBlock]) -> list[PageRef]:
    """Deterministic page-reference detection; raw = the sentence fragment containing "Seite N"."""
    refs: list[PageRef] = []
    for b in blocks:
        for m in _PAGE_REF.finditer(b.text):
            start = max(b.text.rfind(c, 0, m.start()) for c in ".!?:")
            start = 0 if start < 0 else start + 1
            end_m = re.search(r"[.!?]", b.text[m.end():])
            end = m.end() + end_m.end() if end_m else len(b.text)
            refs.append(PageRef(raw=b.text[start:end].strip(), target_page=int(m.group(1)), page=b.page, bbox=b.bbox))
    return refs
