"""Builds designer_context.json: spike extraction + HAND-normalized values (ground truth for T3-T5).

Run: uv run python tests/fixtures/build_designer_context.py
"""
import hashlib
import json
import pathlib
from decimal import Decimal as D

from flyercheck.domain.models import (
    BBox,
    Document,
    DocumentContext,
    Offer,
    PageImage,
    PageRef,
    Quantity,
    TextBlock,
    Unit,
    UnitPrice,
    Validity,
)

HERE = pathlib.Path(__file__).parent
raw = json.loads((HERE / "llm_extract_designer.json").read_text())
pdf = pathlib.Path("data/samples/Designer.pdf").read_bytes()
sha = hashlib.sha256(pdf).hexdigest()

# (price, original, discount, quantity, unit_price, deposit) — hand-normalized from the printed strings
NORM = {
    "Sonnenäpfel": (D("1.69"), None, None, Quantity(amount=D(1), unit=Unit.KG), None, None),
    "Rispentomaten": (D("1.49"), D("1.99"), D(25), Quantity(amount=D(1), unit=Unit.KG), None, None),
    "Nordmeer Lachsfilet": (D("2.99"), None, None, Quantity(amount=D(100), unit=Unit.G), None, None),
    "Bergtal Fruchtjoghurt": (D("0.39"), D("0.59"), D(33), Quantity(amount=D(150), unit=Unit.G),
                              UnitPrice(value=D("2.60"), per_unit=Unit.KG), None),
    "Goldkrone Röstkaffee": (D("6.99"), None, None, Quantity(amount=D(500), unit=Unit.G),
                             UnitPrice(value=D("13.98"), per_unit=Unit.KG), None),
    "Steinofen Genuss Pizza Salami": (D("1.69"), D("2.89"), D(42), Quantity(amount=D(320), unit=Unit.G),
                                      UnitPrice(value=D("5.59"), per_unit=Unit.KG), None),
    "Quellklar Mineralwasser": (D("3.99"), None, None, Quantity(amount=D("1.5"), unit=Unit.L, pack_count=6),
                                UnitPrice(value=D("0.44"), per_unit=Unit.L), D("1.50")),
    "Schola Schokolade": (D("0.99"), D("1.29"), D(23), Quantity(amount=D(100), unit=Unit.G), None, None),
    "Softina Toilettenpapier Samtweich": (D("2.79"), None, None,
                                          Quantity(amount=D(150), unit=Unit.SHEET, pack_count=8), None, None),
}

offers = []
for i, o in enumerate(raw["offers"], 1):
    key = next(k for k in NORM if o["product_name"].startswith(k.split()[0]))
    price, orig, disc, qty, up, dep = NORM[key]
    offers.append(Offer(
        id=f"o-{i}", product_name=o["product_name"], description_lines=o["description_lines"],
        image_description=o["image_description"],
        bbox=BBox.from_box_2d(o["offer_box_2d"]), image_bbox=BBox.from_box_2d(o["image_box_2d"]),
        price_raw=o["price_raw"], original_price_raw=o["original_price_raw"], discount_raw=o["discount_raw"],
        quantity_raw=o["quantity_raw"], unit_price_raw=o["unit_price_raw"], deposit_raw=o["deposit_raw"],
        price=price, original_price=orig, discount_pct=disc, quantity=qty, unit_price=up, deposit=dep,
        badges=["AUS DER REGION"] if key == "Sonnenäpfel" else [],
    ))

blocks = [TextBlock(text=b["text"], bbox=BBox.from_box_2d(b["box_2d"])) for b in raw["text_blocks"]]
ctx = DocumentContext(
    document=Document(id=sha[:12], sha256=sha, filename="Designer.pdf", page_count=1,
                      campaign_year=2026, campaign_year_source="pdf_metadata"),
    pages=[PageImage(number=1, width_px=1024, height_px=1536, path="tests/fixtures/page1.png")],
    offers=offers,
    validity=Validity(raw=raw["validity_raw"], from_day=7, from_month=10, from_weekday="Mo",
                      until_day=12, until_month=10, until_weekday="Sa",
                      bbox=BBox.from_box_2d(raw["validity_box_2d"])),
    page_refs=[PageRef(raw="Rezept auf Seite 6.", target_page=6, bbox=blocks[0].bbox)],
    text_blocks=blocks,
)
(HERE / "designer_context.json").write_text(ctx.model_dump_json(indent=1))
print("offers:", len(offers))
