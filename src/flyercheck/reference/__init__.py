"""Reference (master) data adapter for R-08 (E-02). Owned by Phase 3 track E7.

Activated via env FLYERCHECK_REFERENCE_CSV (set by `flyercheck run --reference PATH`).
The CSV adapter is a stand-in for a PIM / price DB behind `ReferencePort` (P-04, P-06).
"""
from __future__ import annotations

import csv
import os
import unicodedata
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from flyercheck.domain.models import Offer

ENV_VAR = "FLYERCHECK_REFERENCE_CSV"
MIN_PREFIX_LEN = 6
COLUMNS = ("sku", "product_name", "price", "original_price", "quantity_raw", "valid_from", "valid_until")


class ReferenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: str
    product_name: str
    price: Decimal
    original_price: Decimal | None = None
    quantity_raw: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    source: str


class ReferencePort(Protocol):
    def lookup(self, offer: Offer) -> ReferenceItem | None: ...


def normalize_name(name: str) -> str:
    """NFC, casefold, collapse whitespace."""
    return " ".join(unicodedata.normalize("NFC", name).casefold().split())


def _opt(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


class CsvReference:
    """Reference items loaded from a CSV file (synthetic PIM / price-DB stand-in)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(f"Reference CSV not found: {self.path} (set via {ENV_VAR} / --reference)")
        self.items: list[ReferenceItem] = []
        with self.path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"Reference CSV {self.path} lacks columns: {', '.join(missing)}")
            for row in reader:
                orig = _opt(row["original_price"])
                vf, vu = _opt(row["valid_from"]), _opt(row["valid_until"])
                self.items.append(ReferenceItem(
                    sku=row["sku"].strip(),
                    product_name=row["product_name"].strip(),
                    price=Decimal(row["price"].strip()),
                    original_price=Decimal(orig) if orig else None,
                    quantity_raw=_opt(row["quantity_raw"]),
                    valid_from=date.fromisoformat(vf) if vf else None,
                    valid_until=date.fromisoformat(vu) if vu else None,
                    source=self.path.name,
                ))
        self._by_name = {normalize_name(i.product_name): i for i in self.items}

    def lookup(self, offer: Offer) -> ReferenceItem | None:
        """Exact casefold name match, else longest reference name that is a prefix of the
        offer name or vice versa (both >= MIN_PREFIX_LEN chars), else None."""
        if not offer.product_name:
            return None
        name = normalize_name(offer.product_name)
        if name in self._by_name:
            return self._by_name[name]
        best: tuple[int, ReferenceItem] | None = None
        for ref_name, item in self._by_name.items():
            if min(len(ref_name), len(name)) < MIN_PREFIX_LEN:
                continue
            if (name.startswith(ref_name) or ref_name.startswith(name)) and (
                best is None or len(ref_name) > best[0]
            ):
                best = (len(ref_name), item)
        return best[1] if best else None


def load_reference_from_env() -> ReferencePort | None:
    """CsvReference from $FLYERCHECK_REFERENCE_CSV, or None if unset. Missing file → FileNotFoundError."""
    path = os.environ.get(ENV_VAR, "").strip()
    if not path:
        return None
    return CsvReference(path)
