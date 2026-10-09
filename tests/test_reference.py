"""E7: CSV reference adapter and R-08 master-data price check."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from flyercheck.domain.models import Offer, Status
from flyercheck.reference import ENV_VAR, CsvReference, load_reference_from_env
from flyercheck.rules import r_08_master_data as r08

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data/reference/designer_prices.csv"
HEADER = "sku,product_name,price,original_price,quantity_raw,valid_from,valid_until\n"


def _csv(tmp_path: Path, rows: str) -> Path:
    p = tmp_path / "ref.csv"
    p.write_text(HEADER + rows, encoding="utf-8")
    return p


def test_no_env_single_doc_not_evaluable(monkeypatch, designer_ctx):
    monkeypatch.delenv(ENV_VAR, raising=False)
    findings = r08.check(designer_ctx)
    assert len(findings) == 1
    assert findings[0].id == "R-08:doc"
    assert findings[0].status is Status.NOT_EVALUABLE


def test_designer_reference_pizza_fails_others_pass(monkeypatch, designer_ctx):
    monkeypatch.setenv(ENV_VAR, str(CSV))
    findings = r08.check(designer_ctx)
    assert len(findings) == 9
    fails = [f for f in findings if f.status is Status.FAIL]
    assert len(fails) == 1
    pizza = fails[0]
    assert pizza.id == "R-08:o-6"
    assert pizza.offer_name.startswith("Steinofen")
    assert pizza.severity.value == "critical"
    assert pizza.expected["price"] == "1.79"
    assert pizza.observed["price"] == "1.69"
    assert "1.79" in pizza.summary and "SKU 100006" in pizza.summary
    assert any(e.source == "reference" and e.raw == "designer_prices.csv 100006" for e in pizza.evidence)
    assert sum(f.status is Status.PASS for f in findings) == 8
    assert all(f.rule_version == "R-08@2.0" for f in findings)


def test_unknown_product_not_evaluable(tmp_path, designer_ctx):
    ref = CsvReference(_csv(tmp_path, "1,Something Else Entirely,1.00,,,,\n"))
    findings = r08.check_offers(designer_ctx, ref)
    assert all(f.status is Status.NOT_EVALUABLE for f in findings)
    assert all(f.severity.value == "medium" for f in findings)
    assert "no reference record" in findings[0].summary.casefold()


def test_original_price_mismatch_separate_fail(tmp_path, designer_ctx):
    ref = CsvReference(_csv(tmp_path, "7,Rispentomaten,1.49,2.19,1 kg,,\n"))
    findings = {f.id: f for f in r08.check_offers(designer_ctx, ref)}
    assert findings["R-08:o-2"].status is Status.PASS
    orig = findings["R-08:o-2:orig"]
    assert orig.status is Status.FAIL
    assert orig.severity.value == "high"
    assert orig.expected["original_price"] == "2.19"


def test_csv_parsing(tmp_path):
    ref = CsvReference(CSV)
    assert len(ref.items) == 9
    pizza = next(i for i in ref.items if i.sku == "100006")
    assert pizza.price == Decimal("1.79") and pizza.original_price == Decimal("2.89")
    assert pizza.valid_from.isoformat() == "2026-10-05" and pizza.valid_from.weekday() == 0
    assert next(i for i in ref.items if i.sku == "100001").original_price is None


@pytest.mark.parametrize(("offer_name", "expected_sku"), [
    ("Steinofen Genuss Pizza Salami", "3"),        # exact
    ("STEINOFEN genuss  pizza salami", "3"),       # casefold + whitespace
    ("Steinofen Genuss Pizza Salami 320g", "3"),   # ref name is prefix of offer, longest wins
    ("Steinofen Genuss", "3"),                     # offer is prefix of refs; longest ref wins
    ("Bergtal Fruchtjoghurt", None),               # no match
    ("Stein", None),                               # below 6 chars
    (None, None),
])
def test_matching(tmp_path, offer_name, expected_sku):
    ref = CsvReference(_csv(tmp_path, (
        "1,Steinofen,1.00,,,,\n"
        "2,Steinofen Genuss Pizza,1.00,,,,\n"
        "3,Steinofen Genuss Pizza Salami,1.79,,,,\n")))
    item = ref.lookup(Offer(id="o-1", product_name=offer_name))
    assert (item.sku if item else None) == expected_sku


def test_load_from_env(monkeypatch, tmp_path):
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert load_reference_from_env() is None
    monkeypatch.setenv(ENV_VAR, str(CSV))
    assert isinstance(load_reference_from_env(), CsvReference)
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "missing.csv"))
    with pytest.raises(FileNotFoundError, match="missing.csv"):
        load_reference_from_env()
