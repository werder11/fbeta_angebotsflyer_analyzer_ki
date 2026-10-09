"""Canonical contract (ADR-0004). FROZEN during parallel work — change only via integrator."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.1"


class Status(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"
    NOT_EVALUABLE = "not_evaluable"
    ERROR = "error"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(StrEnum):
    E01_PRODUCT_IMAGE = "E01_product_image"
    E02_MASTER_DATA = "E02_master_data"
    E03_ARITHMETIC = "E03_arithmetic"
    E04_QUANTITY = "E04_quantity"
    E05_ASSOCIATION = "E05_association"
    E06_TEMPORAL = "E06_temporal"
    E07_SEMANTIC = "E07_semantic"
    E08_COMPLETENESS = "E08_completeness"
    E09_CROSS_REFERENCE = "E09_cross_reference"
    E10_VISUAL_QUALITY = "E10_visual_quality"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BBox(Model):
    """Normalized to 0..1, origin top-left."""

    x0: float = Field(ge=0, le=1)
    y0: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)

    @classmethod
    def from_box_2d(cls, box: list[int | float]) -> BBox:
        """Gemini box_2d = [ymin, xmin, ymax, xmax] in 0..1000."""
        ymin, xmin, ymax, xmax = (max(0.0, min(1.0, v / 1000)) for v in box)
        return cls(x0=xmin, y0=ymin, x1=xmax, y1=ymax)


class Unit(StrEnum):
    G = "g"
    KG = "kg"
    ML = "ml"
    L = "l"
    PIECE = "piece"
    SHEET = "sheet"


class Quantity(Model):
    amount: Decimal  # per item, e.g. 1.5
    unit: Unit  # e.g. l
    pack_count: int = 1  # e.g. 6

    def total_base(self) -> tuple[Decimal, Unit]:
        """Total in base unit: g→kg, ml→l; piece/sheet unchanged."""
        total = self.amount * self.pack_count
        if self.unit is Unit.G:
            return total / 1000, Unit.KG
        if self.unit is Unit.ML:
            return total / 1000, Unit.L
        return total, self.unit


class UnitPrice(Model):
    value: Decimal  # 5.59
    per_amount: Decimal = Decimal(1)
    per_unit: Unit  # kg


class Offer(Model):
    id: str  # "o-1".."o-n", reading order
    page: int = 1
    bbox: BBox | None = None
    image_bbox: BBox | None = None
    product_name: str | None = None
    brand: str | None = None
    description_lines: list[str] = []
    badges: list[str] = []
    image_description: str | None = None  # blind description of the photo
    # raw (verbatim) ...
    price_raw: str | None = None
    original_price_raw: str | None = None
    discount_raw: str | None = None
    quantity_raw: str | None = None
    unit_price_raw: str | None = None
    deposit_raw: str | None = None
    # ... and normalized (None = unparseable/absent, never a default)
    price: Decimal | None = None
    original_price: Decimal | None = None
    discount_pct: Decimal | None = None  # positive, e.g. 42
    quantity: Quantity | None = None
    unit_price: UnitPrice | None = None
    deposit: Decimal | None = None
    extraction_confidence: float | None = None


class Validity(Model):
    raw: str
    from_day: int | None = None
    from_month: int | None = None
    from_weekday: str | None = None  # "Mo"
    until_day: int | None = None
    until_month: int | None = None
    until_weekday: str | None = None  # "Sa"
    bbox: BBox | None = None


class PageRef(Model):
    raw: str  # "Rezept auf Seite 6."
    target_page: int
    page: int = 1
    bbox: BBox | None = None


class TextBlock(Model):
    text: str
    page: int = 1
    bbox: BBox | None = None


class Document(Model):
    id: str  # sha256[:12]
    sha256: str
    filename: str
    page_count: int
    campaign_year: int | None = None
    campaign_year_source: Literal["cli", "pdf_metadata"] | None = None


class PageImage(Model):
    number: int
    width_px: int
    height_px: int
    path: str  # PNG on disk


class DocumentContext(Model):
    document: Document
    pages: list[PageImage]
    offers: list[Offer]
    validity: Validity | None = None
    page_refs: list[PageRef] = []
    text_blocks: list[TextBlock] = []


class Evidence(Model):
    page: int = 1
    bbox: BBox | None = None
    raw: str | None = None
    source: Literal["flyer", "rule", "model", "reference"] = "flyer"


class Finding(Model):
    id: str  # f"{check_id}:{offer_id or 'doc'}"
    check_id: str  # "R-01", "V-01"
    category: Category
    severity: Severity
    status: Status
    summary: str
    offer_id: str | None = None
    offer_name: str | None = None
    observed: dict[str, str] = {}
    expected: dict[str, str] = {}
    evidence: list[Evidence] = []
    confidence: float = Field(ge=0, le=1, default=1.0)
    rule_version: str | None = None
    model_version: str | None = None


class RunResult(Model):
    run_id: str
    contract_version: str = CONTRACT_VERSION
    started_at: datetime
    duration_s: float
    mode: Literal["live", "record", "replay", "context"]
    context: DocumentContext
    findings: list[Finding]
    versions: dict[str, str] = {}  # {"extract_model": ..., "prompt": ..., "rules": ...}
    llm_usage: dict[str, int] = {}  # {"calls": n, "input_tokens": .., "output_tokens": ..}


class GoldenLabel(Model):
    id: str  # "G-01"
    check_id: str
    offer_name: str | None = None  # None = document-level; matched case-insensitively by prefix
    status: Status
    severity: Severity | None = None
    note: str = ""


class GoldenSet(Model):
    document: str
    labels: list[GoldenLabel]
    expected_passes: list[GoldenLabel] = []


class Decision(StrEnum):
    CONFIRM = "confirm"
    REJECT = "reject"
    ESCALATE = "escalate"


class ReviewDecision(Model):
    """Human disposition of a finding (ADR-0006). Kept separate from model-generated conclusions."""

    run_id: str
    finding_id: str
    decision: Decision
    reviewer: str = "anonymous"
    reason: str = ""
    decided_at: datetime
