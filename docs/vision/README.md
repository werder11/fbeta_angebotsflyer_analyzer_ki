# Vision

← [docs index](../README.md)

## Problem
A large retailer produces promotional flyers every week. Before a flyer is published, a reviewer checks it by hand for consistency: does the image match the product, is the price arithmetic right, are the mandatory price details present, are the dates plausible, do the references resolve? This is slow, repetitive and easy to get wrong under deadline pressure.

## Goal
Automate **most** of the check with AI, while a human stays accountable for publication ([ADR-0006](../adr/0006-human-in-the-loop.md)).

| Dimension | Outcome | Measure |
|---|---|---|
| Effectiveness | Catch publication-relevant defects | Recall per defect category (critical classes first) |
| Trust | No noise and no invented findings | Precision; evidence completeness = 100 % |
| Efficiency | Less manual review time | Minutes per flyer vs. baseline |
| Operability | Fits the weekly cycle | p95 latency per flyer, € per flyer |

Targets are **not invented**. They are agreed with the business after a baseline measurement. Working hypotheses for the PoC: recall ≥ 0.9 on price and arithmetic classes, precision ≥ 0.8, < 2 min and < €0.50 per page.

## Scope
**In:** PDF/image ingestion · offer extraction with bounding boxes · deterministic price, unit-price, discount, deposit, date and completeness rules · LLM image↔text match · cross-references within the document · evidence report · review decisions · evaluation harness.
**Out (PoC):** editing the flyer · writing back to the PIM or price systems · auto-approval · legal sign-off on claims.

## Assumptions (to be validated)
| ID | Assumption | Impact if false |
|---|---|---|
| A-01 | Input is a print-ready PDF (one or more pages) | Add an image-only path (already supported through rendering) |
| A-02 | No PIM/price master data is available for the PoC | Reference checks are `not_evaluable`; the adapter is a stub |
| A-03 | Azure **or** GCP LLMs are allowed for confidential pre-publication data in an EU region | Without this, an on-prem VLM is needed and the architecture holds |
| A-04 | The campaign year is supplied as metadata (or defaults to the current year) | Weekday checks degrade to `needs_review` |
| A-05 | The legal basis is German PAngV (Grundpreis per kg/l) and UWG (no misleading discounts) | Rule configs change, not code |

## Roadmap
1. **PoC (this sprint):** single flyer, replayable, findings report. → [plan](../plan/implementation-plan.md)
2. **Shadow pilot (4–6 wks):** runs next to the manual review on ~20 real flyers; build the golden set; measure the baseline.
3. **Assisted production:** integrate with the DTP/PIM workflow, review UI, monitoring, change-gated releases.
4. **Scale-out:** reference-data checks against PIM and the price DB, regional variants, multi-page cross-checks.
