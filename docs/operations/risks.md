# Risks & Limits

← [operations](README.md) · [docs index](../README.md)

| # | Risk / limit | Impact | Mitigation |
|---|---|---|---|
| R1 | **Misread numbers** (VLM OCR error) → false fail or false pass | High | Verbatim prompt, OCR cross-check (ADR-0002), evidence crop for 5-s verification, `needs_review` on disagreement |
| R2 | **Wrong offer grouping** in dense or creative layouts | High | Bbox per field, geometry sanity checks (price box inside offer box), page tiling |
| R3 | **Hallucinated findings** / LLM non-determinism | Med | Temperature 0, structured output, blind-describe-then-compare, deterministic rules for all arithmetic |
| R4 | **False sense of safety** ("no findings = OK") | High | Report coverage (`not_evaluable` visible), HITL (ADR-0006), no auto-publish |
| R5 | **No master data** → price correctness vs. intent is not checkable | High | A PIM/price adapter is the #1 roadmap item; until then only internal consistency is checked |
| R6 | **Confidential data** at a cloud LLM | High | EU region, enterprise no-training terms, private endpoints, retention policy, DPA |
| R7 | **Prompt injection** through flyer text | Low/Med | Flyer text is treated as data in the prompt; outputs are schema-validated; the LLM has no tools or side effects |
| R8 | **Model deprecation / silent drift** | Med | Pinned versions, provider port (ADR-0003), regression gate (ADR-0008) |
| R9 | **Legal rules are policy-dependent** (rounding, Grundpreis basis for sheets) | Med | Rules configurable, confirmed with the legal/compliance owner |
| R10 | **Small eval set** → overstated accuracy | Med | Mutation-based synthetic defects + pilot on real flyers before claims |
| R11 | **Cost/latency** at scale (hundreds of pages before a deadline) | Low | Flash-class for vision checks, parallel page fan-out, caching by page hash |
| R12 | **Image↔text limits**: a generic image or invisible variant (flavour, weight) is not decidable | Med | `unclear` → needs_review; compare category, not SKU |

**Out of reach for the AI:** legal truth of claims (e.g. "nachhaltig") without references; intent (was 1.69 the *planned* price?); brand-design taste.
