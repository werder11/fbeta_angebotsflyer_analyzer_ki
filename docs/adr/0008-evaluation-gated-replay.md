# ADR-0008: Golden set + LLM record/replay gate every change

## Status
Accepted

## Context
LLM outputs are non-deterministic, and prompt or model changes can silently regress. Live API calls make tests slow, costly and flaky, and they are a demo risk.

## Decision
1. The `LLMPort` supports `live | record | replay`. Recordings are keyed by a hash of (model, prompt, image hash, schema) and stored in `data/recordings/`.
2. Golden labels live in `data/golden/<doc>.json` (format = expected findings `{offer_match, check_id, status}`).
3. `flyercheck eval` reports P/R/F1 **per category**, plus evidence completeness, latency and cost.
4. CI: unit tests + replay pipeline + eval must not drop below the baseline. A model or prompt change requires a fresh `record` run and a reviewed diff of the eval report.

## Consequences
**+** deterministic tests, offline demo, quantitative vendor comparison (Gemini vs. Azure). **−** recordings go stale; refresh them on each prompt change.

## Links
[evaluation-and-monitoring](../operations/evaluation-and-monitoring.md) · [ADR-0003](0003-provider-agnostic-llm-port.md)
