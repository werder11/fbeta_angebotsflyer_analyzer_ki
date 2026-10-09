from decimal import Decimal

import pytest

from flyercheck.domain.models import BBox, DocumentContext, Quantity, Status, Unit
from flyercheck.llm.port import FakeLLM, request_key


def test_fixture_roundtrip(designer_ctx):
    assert len(designer_ctx.offers) == 9
    again = DocumentContext.model_validate_json(designer_ctx.model_dump_json())
    assert again == designer_ctx


def test_bbox_from_box_2d():
    b = BBox.from_box_2d([187, 11, 371, 331])
    assert (b.x0, b.y0, b.x1, b.y1) == pytest.approx((0.011, 0.187, 0.331, 0.371))


def test_quantity_total_base():
    assert Quantity(amount=Decimal("1.5"), unit=Unit.L, pack_count=6).total_base() == (Decimal("9.0"), Unit.L)
    assert Quantity(amount=Decimal(320), unit=Unit.G).total_base() == (Decimal("0.32"), Unit.KG)


def test_golden_loads(golden):
    assert len(golden.labels) == 10 and golden.labels[0].status is Status.FAIL


def test_request_key_stable():
    assert request_key("extract", "p", [b"x"], {"a": 1}) == request_key("extract", "p", [b"x"], {"a": 1})


def test_fake_llm_list_and_exception():
    llm = FakeLLM({"vision": [{"ok": 1}, RuntimeError("boom")]})
    assert llm.generate_json("p", [], {}, purpose="vision") == {"ok": 1}
    with pytest.raises(RuntimeError):
        llm.generate_json("p", [], {}, purpose="vision")
