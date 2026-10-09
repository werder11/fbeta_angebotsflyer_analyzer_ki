# Sample Flyer Analysis — `Designer.pdf` (Frischfeld Markt)

← [domain](README.md) · [docs index](../README.md) · Rules: [rules-catalog](../design/rules-catalog.md)

Hand analysis, verified by computation. It becomes `data/golden/designer.json`, the target the PoC must reproduce. It is **one page and synthetic**, so it can't support accuracy claims; it is a functional test.

## Offer inventory

| # | Offer | Price | Orig. | Disc. | Quantity | Printed Grundpreis | Computed Grundpreis |
|---|---|---|---|---|---|---|---|
| 1 | Sonnenäpfel Rubinette | 1.69 | – | – | 1 kg | (price = per kg) | 1.69 €/kg |
| 2 | Rispentomaten NL | 1.49 | 1.99 | −25 % | 1 kg | (price = per kg) | 1.49 €/kg; disc. 25.13 % |
| 3 | Nordmeer Lachsfilet | 2.99 | – | – | 100 g | **missing** | 29.90 €/kg |
| 4 | Bergtal Fruchtjoghurt | 0.39 | 0.59 | −33 % | 150 g | 2.60 €/kg | 2.60 ✓; disc. 33.90 % |
| 5 | Goldkrone Röstkaffee | 6.99 | – | – | 500 g | 13.98 €/kg | 13.98 ✓ |
| 6 | Steinofen Pizza Salami | 1.69 | 2.89 | −42 % | 320 g | **5.59 €/kg** | **5.28** ✗; disc. **41.52 %** |
| 7 | Quellklar Mineralwasser | 3.99 | – | – | 6 × 1.5 l | 0.44 €/l | 0.443 ✓; deposit 6 × 0.25 = 1.50 ✓ |
| 8 | Schola Schokolade | 0.99 | 1.29 | −23 % | 100 g | **missing** | 9.90 €/kg; disc. 23.26 % ✓ |
| 9 | Softina Toilettenpapier | 2.79 | – | – | 8 × 150 sheets | **missing** | 0.23 €/100 sheets |

Campaign: "Gültig von **Mo.** 07.10. bis **Sa.** 12.10." Mon/Sat holds only in **2024 and 2030**. 2025 = Tue/Sun, 2026 = Wed/Mon.

## Golden findings

| ID | Offer | Check | Status | Severity | Evidence |
|---|---|---|---|---|---|
| G-01 | Schola Schokolade | V-01 image↔text | **fail** | critical | The image shows an aubergine; the text says milk chocolate bar |
| G-02 | Pizza | R-01 unit price | **fail** | critical | 1.69 / 0.32 kg = 5.28 ≠ 5.59 (5.59 ≈ 1.79/0.32, likely a stale price) |
| G-03 | Pizza | R-02 discount | **fail** | high | −42 % advertised, actual 41.52 %. **Overstated** (UWG risk) |
| G-04 | Document (Bergtal vs. Pizza) | R-02b rounding consistency | needs_review | low | Bergtal 33.90 → −33 % (floor); Pizza 41.52 → −42 % (round-up). Mixed policy |
| G-05 | Lachsfilet | R-04 Grundpreis | **fail** | high | No €/kg shown (PAngV) → expected 29.90 €/kg |
| G-06 | Schola | R-04 Grundpreis | **fail** | high | No €/kg → expected 9.90 €/kg |
| G-07 | Softina | R-04 Grundpreis | needs_review | medium | No unit price per sheet/roll. The basis depends on policy |
| G-08 | Campaign | R-05 weekday↔date | **fail** (year 2026 from PDF metadata) | high | "Mo. 07.10." is Monday only in 2024/2030; in 2026 it is a Wednesday |
| G-09 | Recipe teaser | R-07 page reference | **fail** | medium | "Rezept auf Seite 6", but the document has 1 page |
| G-10 | all | R-08 master-data price | not_evaluable | — | No PIM reference available (A-02) |

**Expected passes (to prove there are no false positives):** Goldkrone, Bergtal and Quellklar unit prices; Tomaten and Schola discounts; Quellklar deposit; image↔text for apples, tomatoes, salmon, yoghurt, coffee, pizza, water and toilet paper.

## Edge cases to label in the pilot
- Salmon: "Nordmeer" (a catch-area wording) together with "Aquakultur" and ASC. Plausible, but a semantic claim → V-02 only with references.
- Tomaten "aus den Niederlanden" under the footer slogan "Regional". Not a defect: the regional badge applies only to apples.
