# Reference (master) data

`designer_prices.csv` is a **synthetic stand-in** for PIM / price-DB data used by
rule R-08 (E-02, principle P-06 "authoritative data wins"). It is not real data.

- Columns: `sku,product_name,price,original_price,quantity_raw,valid_from,valid_until`
  (decimal point, ISO dates, empty cell = absent).
- All offers mirror the printed flyer values **except** the Steinofen pizza: the approved
  price is 1.79 € (original 2.89 €). The printed 1.69 € is the actual error, which also
  explains why the printed unit price 5.59 €/kg (= 1.79 / 0.32 kg) and the -42 % discount
  look wrong (R-01, R-02).
- Validity 2026-10-05 (Monday) to 2026-10-10 (Saturday), consistent with the R-05 finding
  that the printed dates are wrong.

Usage: `flyercheck run data/samples/Designer.pdf --reference data/reference/designer_prices.csv`
