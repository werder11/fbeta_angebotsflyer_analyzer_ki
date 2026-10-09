import copy

import pytest

from flyercheck.domain.models import Document, PageImage
from flyercheck.extract import EXTRACTION_PROMPT, PROMPT_VERSION, SCHEMA, extract_document
from flyercheck.llm.port import FakeLLM

FIELDS = ("product_name", "price", "original_price", "discount_pct", "quantity", "unit_price", "deposit",
          "price_raw", "quantity_raw", "unit_price_raw", "deposit_raw", "bbox", "image_bbox", "image_description")


@pytest.fixture
def doc_and_pages(tmp_path):
    png = tmp_path / "page-1.png"
    png.write_bytes(b"\x89PNG fake")
    doc = Document(id="abc", sha256="abc", filename="Designer.pdf", page_count=1)
    return doc, [PageImage(number=1, width_px=1024, height_px=1536, path=str(png))]


def test_extract_matches_designer_context(doc_and_pages, extract_response, designer_ctx):
    doc, pages = doc_and_pages
    llm = FakeLLM({"extract": extract_response})
    ctx = extract_document(doc, pages, llm)

    assert llm.calls == [("extract", EXTRACTION_PROMPT)]
    assert PROMPT_VERSION == "extract-v1"
    assert [o.id for o in ctx.offers] == [f"o-{i}" for i in range(1, 10)]
    assert len(ctx.offers) == len(designer_ctx.offers) == 9
    for got, want in zip(ctx.offers, designer_ctx.offers, strict=True):
        for f in FIELDS:
            assert getattr(got, f) == getattr(want, f), (want.product_name, f)

    assert ctx.validity is not None and designer_ctx.validity is not None
    assert ctx.validity.model_dump() == designer_ctx.validity.model_dump()
    assert [(r.raw, r.target_page, r.bbox) for r in ctx.page_refs] == [
        (r.raw, r.target_page, r.bbox) for r in designer_ctx.page_refs
    ]
    assert ctx.page_refs[0].target_page == 6
    assert ctx.text_blocks == designer_ctx.text_blocks


def test_extract_tolerates_malformed_boxes_and_missing_fields(doc_and_pages, extract_response):
    doc, pages = doc_and_pages
    resp = copy.deepcopy(extract_response)
    resp["offers"][0]["offer_box_2d"] = [1, 2, 3]
    resp["offers"][0]["image_box_2d"] = None
    resp["offers"][1]["price_raw"] = None
    del resp["validity_raw"]
    ctx = extract_document(doc, pages, FakeLLM({"extract": resp}))
    assert ctx.offers[0].bbox is None and ctx.offers[0].image_bbox is None
    assert ctx.offers[1].price is None
    assert ctx.validity is None


def test_multi_page_ids_and_validity(tmp_path, extract_response):
    pages = []
    for n in (1, 2):
        p = tmp_path / f"page-{n}.png"
        p.write_bytes(b"png")
        pages.append(PageImage(number=n, width_px=10, height_px=10, path=str(p)))
    second = {"offers": extract_response["offers"][:2], "validity_raw": None}
    doc = Document(id="x", sha256="x", filename="x.pdf", page_count=2)
    ctx = extract_document(doc, pages, FakeLLM({"extract": [extract_response, second]}))
    assert [o.id for o in ctx.offers][-2:] == ["o-10", "o-11"]
    assert {o.page for o in ctx.offers[-2:]} == {2}
    assert ctx.validity is not None and ctx.validity.from_day == 7


def test_schema_shape():
    assert set(SCHEMA["properties"]) >= {"validity_raw", "validity_box_2d", "offers", "text_blocks"}
