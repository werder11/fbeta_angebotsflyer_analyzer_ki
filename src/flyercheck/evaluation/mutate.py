"""Mutation-based synthetic defects for rule-level evaluation (risk R10). Owned by Phase 3 track E2.

One real flyer cannot support accuracy claims. Instead we (1) repair the known real defects of a context
into a *clean baseline*, (2) seed one known defect per case with a mutation operator, (3) run the
deterministic rules and check that the seeded defect is reported with the expected status. Per-operator
and per-check recall plus collateral false positives (new positive findings that were not seeded) are
reported. No LLM calls (ADR-0001).
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from decimal import Decimal

from flyercheck.domain.models import DocumentContext, Offer, PageRef, Status, Unit, UnitPrice
from flyercheck.rules import run_rules
from flyercheck.rules.r_02_discount import actual_discount
from flyercheck.rules.r_03_deposit import CONTAINER, DEPOSIT_PER_ITEM
from flyercheck.rules.r_05_validity_weekday import WEEKDAYS, YEAR_RANGE, _matches
from flyercheck.rules.r_common import q2

POSITIVE = {Status.FAIL, Status.NEEDS_REVIEW}
COUNT_BASIS = Decimal(100)

Key = tuple[str, str | None, Status]  # (check_id, offer_id, status)


@dataclass
class Case:
    operator: str
    description: str
    ctx: DocumentContext
    expected: list[Key]
    # Findings that legitimately follow from the seeded defect (e.g. a price change also invalidates the
    # printed discount). Neither scored as detection nor counted as collateral false positives.
    consequential: list[Key] = field(default_factory=list)


# --------------------------------------------------------------------------- baseline


def _set_offer(ctx: DocumentContext, offer_id: str, **update) -> DocumentContext:
    offers = [o.model_copy(update=update) if o.id == offer_id else o for o in ctx.offers]
    return ctx.model_copy(update={"offers": offers})


def _computed_unit_price(o: Offer) -> UnitPrice | None:
    if o.price is None or o.quantity is None:
        return None
    total, unit = o.quantity.total_base()
    if total == 0:
        return None
    if unit in (Unit.SHEET, Unit.PIECE):
        return UnitPrice(value=q2(o.price / total * COUNT_BASIS), per_amount=COUNT_BASIS, per_unit=unit)
    return UnitPrice(value=q2(o.price / total), per_unit=unit)


def _repair_offer(o: Offer) -> Offer:
    upd: dict = {}
    q = o.quantity
    if q is not None and o.price is not None:
        total, _ = q.total_base()
        needs_up = o.unit_price is not None or q.unit in (Unit.SHEET, Unit.PIECE) or total != 1
        computed = _computed_unit_price(o)
        if needs_up and computed is not None:
            cur = o.unit_price
            if cur is None or cur.per_unit is not computed.per_unit or cur.per_amount != computed.per_amount:
                upd["unit_price"] = computed
            else:
                exp = q2(o.price / total * cur.per_amount)
                if abs(exp - cur.value) > Decimal("0.01"):
                    upd["unit_price"] = cur.model_copy(update={"value": exp})
        if q.unit in (Unit.L, Unit.ML) and CONTAINER.search(o.quantity_raw or ""):
            dep = DEPOSIT_PER_ITEM * q.pack_count
            if o.deposit != dep:
                upd["deposit"] = dep
    actual = actual_discount(o)
    if o.discount_pct is not None and actual is not None:
        floored = Decimal(math.floor(actual))
        if o.discount_pct > actual or o.discount_pct < floored:
            upd["discount_pct"] = floored
    return o.model_copy(update=upd) if upd else o


def build_baseline(ctx: DocumentContext) -> DocumentContext:
    """Copy ctx and repair known real defects so offer-level rules report no positives."""
    base = ctx.model_copy(deep=True)
    base = base.model_copy(update={"offers": [_repair_offer(o) for o in base.offers]})
    v = base.validity
    year = base.document.campaign_year
    if v is not None and (year is None or not _matches(v, year)):
        good = next((y for y in YEAR_RANGE if _matches(v, y)), None)
        if good is not None:
            base = base.model_copy(update={"document": base.document.model_copy(update={"campaign_year": good})})
    n = base.document.page_count
    base = base.model_copy(update={"page_refs": [r for r in base.page_refs if r.target_page <= n]})
    return base


def _positives(ctx: DocumentContext) -> set[Key]:
    return {(f.check_id, f.offer_id, f.status) for f in run_rules(ctx) if f.status in POSITIVE}


# --------------------------------------------------------------------------- operators


def _discount_consequences(o: Offer, mutated: Offer) -> list[Key]:
    """A price change can legitimately make the printed discount wrong (R-02) or change rounding (R-02b)."""
    out: list[Key] = []
    if mutated.discount_pct is not None:
        out += [("R-02", o.id, Status.FAIL), ("R-02", o.id, Status.NEEDS_REVIEW), ("R-02b", None, Status.NEEDS_REVIEW)]
    return out


def m1_price_change(ctx: DocumentContext) -> Iterator[Case]:
    for o in ctx.offers:
        if o.unit_price is None or o.price is None or o.quantity is None:
            continue
        if o.quantity.total_base()[1] is not o.unit_price.per_unit:
            continue
        new = o.model_copy(update={"price": o.price + Decimal("0.10")})
        yield Case("M1_price_change", f"{o.id} {o.product_name}: price {o.price} → {new.price}, unit price kept",
                   _set_offer(ctx, o.id, price=new.price), [("R-01", o.id, Status.FAIL)],
                   _discount_consequences(o, new))


def m2_unit_price_typo(ctx: DocumentContext) -> Iterator[Case]:
    for o in ctx.offers:
        if o.unit_price is None or o.price is None or o.quantity is None:
            continue
        up = o.unit_price.model_copy(update={"value": o.unit_price.value + Decimal("0.31")})
        yield Case("M2_unit_price_typo", f"{o.id} {o.product_name}: unit price {o.unit_price.value} → {up.value}",
                   _set_offer(ctx, o.id, unit_price=up), [("R-01", o.id, Status.FAIL)])


def m3_discount_overstated(ctx: DocumentContext) -> Iterator[Case]:
    for o in ctx.offers:
        actual = actual_discount(o)
        if actual is None or o.discount_pct is None:
            continue
        printed = Decimal(math.ceil(actual) + 1)
        yield Case("M3_discount_overstated", f"{o.id} {o.product_name}: discount -{o.discount_pct}% → -{printed}% "
                   f"(actual {actual:.2f}%)",
                   _set_offer(ctx, o.id, discount_pct=printed), [("R-02", o.id, Status.FAIL)])


def m4_drop_grundpreis(ctx: DocumentContext) -> Iterator[Case]:
    for o in ctx.offers:
        q = o.quantity
        if o.unit_price is None or q is None or q.unit not in (Unit.G, Unit.ML) or q.total_base()[0] == 1:
            continue
        yield Case("M4_drop_grundpreis", f"{o.id} {o.product_name}: unit price removed ({o.quantity_raw})",
                   _set_offer(ctx, o.id, unit_price=None, unit_price_raw=None), [("R-04", o.id, Status.FAIL)])


def m5_wrong_deposit(ctx: DocumentContext) -> Iterator[Case]:
    wrong = Decimal("1.00")
    for o in ctx.offers:
        q = o.quantity
        if q is None or q.unit not in (Unit.L, Unit.ML) or not CONTAINER.search(o.quantity_raw or ""):
            continue
        if DEPOSIT_PER_ITEM * q.pack_count == wrong:
            continue
        yield Case("M5_wrong_deposit", f"{o.id} {o.product_name}: deposit {o.deposit} → {wrong}",
                   _set_offer(ctx, o.id, deposit=wrong), [("R-03", o.id, Status.FAIL)])


def m6_weekday_shift(ctx: DocumentContext) -> Iterator[Case]:
    v = ctx.validity
    if v is None or ctx.document.campaign_year is None:
        return
    for key in ("from_weekday", "until_weekday"):
        wd = getattr(v, key)
        if wd not in WEEKDAYS:
            continue
        nxt = WEEKDAYS[(WEEKDAYS.index(wd) + 1) % 7]
        yield Case("M6_weekday_shift", f"validity {key} {wd} → {nxt}",
                   ctx.model_copy(update={"validity": v.model_copy(update={key: nxt})}),
                   [("R-05", None, Status.FAIL)])


def m7_dangling_page_ref(ctx: DocumentContext) -> Iterator[Case]:
    target = ctx.document.page_count + 3
    ref = PageRef(raw=f"Mehr auf Seite {target}.", target_page=target, page=1)
    yield Case("M7_dangling_page_ref", f"added page reference → page {target} of {ctx.document.page_count}",
               ctx.model_copy(update={"page_refs": [*ctx.page_refs, ref]}), [("R-07", None, Status.FAIL)])


def m8_missing_price(ctx: DocumentContext) -> Iterator[Case]:
    for o in ctx.offers:
        if o.price is None:
            continue
        yield Case("M8_missing_price", f"{o.id} {o.product_name}: price removed",
                   _set_offer(ctx, o.id, price=None, price_raw=None), [("R-06", o.id, Status.FAIL)])


def m9_quantity_unit_swap(ctx: DocumentContext) -> Iterator[Case]:
    for o in ctx.offers:
        q = o.quantity
        if o.unit_price is None or q is None or q.unit is not Unit.G:
            continue
        nq = q.model_copy(update={"unit": Unit.KG})
        yield Case("M9_quantity_unit_swap", f"{o.id} {o.product_name}: quantity {q.amount} g → {q.amount} kg",
                   _set_offer(ctx, o.id, quantity=nq), [("R-01", o.id, Status.FAIL)])


OPERATORS: list[Callable[[DocumentContext], Iterator[Case]]] = [
    m1_price_change, m2_unit_price_typo, m3_discount_overstated, m4_drop_grundpreis, m5_wrong_deposit,
    m6_weekday_shift, m7_dangling_page_ref, m8_missing_price, m9_quantity_unit_swap,
]


def generate_cases(baseline: DocumentContext) -> list[Case]:
    return [c for op in OPERATORS for c in op(baseline)]


# --------------------------------------------------------------------------- evaluation


def _key_str(k: Key) -> str:
    return f"{k[0]}:{k[1] or 'doc'}={k[2].value}"


def _ratio(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def run_mutation_eval(ctx: DocumentContext) -> dict:
    """Apply each mutation operator to ctx, run rules, check the seeded defect is detected."""
    baseline = build_baseline(ctx)
    base_pos = _positives(baseline)
    cases = generate_cases(baseline)

    per_op: dict[str, dict] = defaultdict(lambda: {"cases": 0, "detected": 0, "collateral_fp": 0})
    per_check: dict[str, dict] = defaultdict(lambda: {"cases": 0, "detected": 0})
    misses: list[str] = []
    collateral: list[str] = []
    detected_total = fp_total = 0

    for c in cases:
        found = {(f.check_id, f.offer_id, f.status) for f in run_rules(c.ctx)}
        hit = all(k in found for k in c.expected)
        extra = {k for k in found if k[2] in POSITIVE} - base_pos - set(c.expected) - set(c.consequential)
        op = per_op[c.operator]
        op["cases"] += 1
        op["detected"] += hit
        op["collateral_fp"] += len(extra)
        for chk in sorted({k[0] for k in c.expected}):
            per_check[chk]["cases"] += 1
            per_check[chk]["detected"] += hit
        detected_total += hit
        fp_total += len(extra)
        if not hit:
            misses.append(f"{c.operator}: {c.description} (expected {', '.join(map(_key_str, c.expected))})")
        if extra:
            collateral.append(f"{c.operator}: {c.description} → {', '.join(sorted(map(_key_str, extra)))}")

    for d in (*per_op.values(), *per_check.values()):
        d["recall"] = _ratio(d["detected"], d["cases"])
    return {
        "cases": len(cases),
        "per_operator": dict(per_op),
        "per_check": dict(sorted(per_check.items())),
        "overall": {"detected": detected_total, "recall": _ratio(detected_total, len(cases)),
                    "collateral_fp": fp_total, "collateral_fp_rate": _ratio(fp_total, len(cases))},
        "baseline_residuals": sorted(_key_str(k) for k in base_pos),
        "misses": misses,
        "collateral": collateral,
    }


def format_mutation_eval(result: dict) -> str:
    def pct(v: float | None) -> str:
        return "   n/a" if v is None else f"{v * 100:5.1f}%"

    lines = ["Mutation evaluation (synthetic defects on repaired baseline)", ""]
    head = f"{'operator':<24} {'cases':>5} {'detected':>8} {'recall':>7} {'collat.FP':>9}"
    lines += [head, "-" * len(head)]
    for op, d in result["per_operator"].items():
        lines.append(f"{op:<24} {d['cases']:>5} {d['detected']:>8} {pct(d['recall']):>7} {d['collateral_fp']:>9}")
    lines.append("-" * len(head))
    o = result["overall"]
    lines.append(f"{'OVERALL':<24} {result['cases']:>5} {o['detected']:>8} {pct(o['recall']):>7} "
                 f"{o['collateral_fp']:>9}")
    lines += ["", f"{'check':<24} {'cases':>5} {'detected':>8} {'recall':>7}"]
    for chk, d in result["per_check"].items():
        lines.append(f"{chk:<24} {d['cases']:>5} {d['detected']:>8} {pct(d['recall']):>7}")
    lines += ["", f"collateral FP rate: {o['collateral_fp_rate']} per case",
              "baseline residuals (excluded): " + (", ".join(result["baseline_residuals"]) or "none")]
    lines.append(f"misses ({len(result['misses'])}):" if result["misses"] else "misses: none")
    lines += [f"  - {m}" for m in result["misses"]]
    if result["collateral"]:
        lines.append(f"collateral findings ({len(result['collateral'])}):")
        lines += [f"  - {c}" for c in result["collateral"]]
    return "\n".join(lines)
