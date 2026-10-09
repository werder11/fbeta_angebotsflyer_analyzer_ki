# ADR-0001: Hybrid validation — deterministic rules + LLM for perception

## Status
Accepted

## Context
Flyer checks fall into two kinds: **perception** (read the price, see that the image shows an aubergine) and **verification** (is 1.69/0.32 = 5.59?). LLMs are strong at perception and unreliable at exact arithmetic, date logic and policy consistency. The results must be auditable.

## Decision Drivers
Correctness of calculations · reproducibility · explainability · cost · legal defensibility (PAngV, UWG)

## Considered Options
### A. End-to-end LLM ("here is the flyer, find the errors")
+ fastest prototype · − non-deterministic, hallucinated arithmetic, no stable evidence, hard to test or regress
### B. Classical only (OCR + layout heuristics + rules)
+ deterministic · − cannot judge image↔text and breaks on creative layouts
### C. Hybrid: the LLM extracts structured observations; code verifies; the LLM judges only visual/semantic questions
+ the best of both; each check is testable · − more components, and extraction quality bounds everything downstream

## Decision
**Option C.** The LLM is a *sensor* (extraction, image description, image↔text judgement). Every calculable rule is plain Python over the canonical model.

## Consequences
**Positive:** unit-testable rules, exact evidence ("expected 5.28, printed 5.59"), cheap re-runs, model swaps without touching rules.
**Negative:** extraction errors propagate, so the extraction confidence must be surfaced (→ `needs_review`).
**Risks:** an extraction miss gives a false "pass". Mitigation: R-06 required fields, and in prod an OCR cross-check (ADR-0002).

## Links
[principles P-01/P-06](../architecture/principles.md) · [rules-catalog](../design/rules-catalog.md) · [pipeline](../design/pipeline.md)
