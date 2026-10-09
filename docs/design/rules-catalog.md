# Rules Catalog (deterministic)

← [design](README.md) · [docs index](../README.md) · ADR: [0001](../adr/0001-hybrid-validation-architecture.md) · Golden: [sample analysis](../domain/sample-flyer-analysis.md)

All arithmetic uses `Decimal` with `ROUND_HALF_UP` to 2 dp unless the config says otherwise. Config lives in `rules/config.yaml` (tolerance, rounding, discount policy) and is versioned with the rule.

| ID | Name | Cat. | Logic | Status mapping | Golden |
|---|---|---|---|---|---|
| R-01 | Unit price (Grundpreis) correct | E-03/E-04 | `expected = price / total_qty_in(kg\|l) ` rounded; compare to printed | equal → pass · differs > 0.01 → **fail** (critical) · price/qty/printed unparseable → not_evaluable | G-02, passes 4/5/7 |
| R-02 | Discount % correct | E-03 | `actual = (orig − price)/orig × 100`; policy `no_overstatement` (configurable) | printed ≤ actual → pass · printed > actual → **fail** (high, UWG) · printed < floor(actual) → needs_review (under-advertised) · orig missing → not_evaluable | G-03 |
| R-02b | Discount rounding consistent (document) | E-03 | Classify each discount as floor-rounded or half-up-rounded; are both used in one flyer? | mixed → needs_review (low) | G-04 |
| R-03 | Deposit plausible | E-08 | If beverage in PET/can: `deposit == pack_count × 0.25`; deposit text present | mismatch → fail · beverage without deposit → fail | pass 7 |
| R-04 | Grundpreis present | E-08 | PAngV: if sold in pre-packed quantity ≠ 1 kg/1 l (and not by piece) → a printed unit price is required. Sheets/pieces → needs_review (basis is policy) | missing → **fail** (high) | G-05, G-06, G-07 |
| R-05 | Validity weekday ↔ date | E-06 | For `year = campaign_year or current_year`: weekday(date) == printed label; from ≤ until; duration ≤ 14 d | mismatch with known year → fail · year unknown → needs_review listing the years where it matches | G-08 |
| R-06 | Required fields | E-08 | Each offer has product_name, price, quantity | missing → fail | — |
| R-07 | Page references resolve | E-09 | Every "Seite N" in `page_refs` has N ≤ page_count | out of range → fail (medium) | G-09 |
| R-08 | Price vs. master data | E-02 | `ReferencePort.lookup(offer)`; compare price, orig, quantity | no reference → **not_evaluable** | G-10 |

## Adding a rule
1. Add a row here (ID, logic, mapping, golden case).
2. Implement `rules/r_XX_name.py` with the `@register` decorator.
3. Add positive, negative and not-evaluable tests.
4. Add or extend the golden labels → the eval gate must stay green.
