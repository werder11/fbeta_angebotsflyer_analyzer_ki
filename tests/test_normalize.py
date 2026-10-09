from decimal import Decimal as D

import pytest

from flyercheck.domain.models import BBox, Quantity, TextBlock, Unit, UnitPrice
from flyercheck.normalize import (
    find_page_refs,
    parse_deposit,
    parse_discount,
    parse_price,
    parse_quantity,
    parse_unit_price,
    parse_validity,
)


@pytest.mark.parametrize(("raw", "expected"), [
    ("1,69", D("1.69")), ("1,49", D("1.49")), ("1,99", D("1.99")), ("2,99", D("2.99")), ("0,39", D("0.39")),
    ("0,59", D("0.59")), ("6,99", D("6.99")), ("2,89", D("2.89")), ("3,99", D("3.99")), ("0,99", D("0.99")),
    ("1,29", D("1.29")), ("2,79", D("2.79")), ("-", None), ("", None), (None, None),
])
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


@pytest.mark.parametrize(("raw", "expected"), [
    ("-25%", D(25)), ("-33%", D(33)), ("-42%", D(42)), ("-23%", D(23)), ("- 10 %", D(10)), (None, None), ("x", None),
])
def test_parse_discount(raw, expected):
    assert parse_discount(raw) == expected


@pytest.mark.parametrize(("raw", "expected"), [
    ("1 kg", Quantity(amount=D(1), unit=Unit.KG)),
    ("100 g", Quantity(amount=D(100), unit=Unit.G)),
    ("150 g Becher", Quantity(amount=D(150), unit=Unit.G)),
    ("500 g Packung", Quantity(amount=D(500), unit=Unit.G)),
    ("320 g Packung", Quantity(amount=D(320), unit=Unit.G)),
    ("6 x 1,5 l PET-Flaschen", Quantity(amount=D("1.5"), unit=Unit.L, pack_count=6)),
    ("100 g Tafel", Quantity(amount=D(100), unit=Unit.G)),
    ("8 x 150 Blatt Packung", Quantity(amount=D(150), unit=Unit.SHEET, pack_count=8)),
    ("750 ml Flasche", Quantity(amount=D(750), unit=Unit.ML)),
    ("10 Stück", Quantity(amount=D(10), unit=Unit.PIECE)),
    ("lose", None),
    (None, None),
])
def test_parse_quantity(raw, expected):
    assert parse_quantity(raw) == expected


@pytest.mark.parametrize(("raw", "expected"), [
    ("1 kg = 2,60", UnitPrice(value=D("2.60"), per_unit=Unit.KG)),
    ("1 kg = 13,98", UnitPrice(value=D("13.98"), per_unit=Unit.KG)),
    ("1 kg = 5,59", UnitPrice(value=D("5.59"), per_unit=Unit.KG)),
    ("(1 kg = 5,59)", UnitPrice(value=D("5.59"), per_unit=Unit.KG)),
    ("1 l = 0,44", UnitPrice(value=D("0.44"), per_unit=Unit.L)),
    ("100 g = 0,99", UnitPrice(value=D("0.99"), per_amount=D(100), per_unit=Unit.G)),
    ("Grundpreis", None),
    (None, None),
])
def test_parse_unit_price(raw, expected):
    assert parse_unit_price(raw) == expected


def test_parse_deposit():
    assert parse_deposit("zzgl. 1,50 Pfand") == D("1.50")
    assert parse_deposit(None) is None


def test_parse_validity():
    v = parse_validity("Gültig von Mo. 07.10. bis Sa. 12.10.")
    assert v is not None
    assert (v.raw, v.from_day, v.from_month, v.from_weekday) == ("Gültig von Mo. 07.10. bis Sa. 12.10.", 7, 10, "Mo")
    assert (v.until_day, v.until_month, v.until_weekday) == (12, 10, "Sa")
    assert parse_validity(None) is None
    unparsed = parse_validity("Nur solange Vorrat reicht")
    assert unparsed is not None and unparsed.from_day is None


def test_find_page_refs():
    bbox = BBox(x0=0.5, y0=0.7, x1=0.7, y1=0.9)
    blocks = [
        TextBlock(text="Rezeptidee: Cremige Kürbissuppe mit gerösteten Kernen. Rezept auf Seite 6.", bbox=bbox),
        TextBlock(text="Regional. Vielfältig. Einfach gut."),
    ]
    refs = find_page_refs(blocks)
    assert len(refs) == 1
    assert (refs[0].raw, refs[0].target_page, refs[0].page, refs[0].bbox) == ("Rezept auf Seite 6.", 6, 1, bbox)
