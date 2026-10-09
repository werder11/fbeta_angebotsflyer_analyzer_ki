# Architecture Principles

← [architecture](README.md) · [docs index](../README.md)

| ID | Principle | Consequence for code | ADR |
|---|---|---|---|
| P-01 | **Deterministic first.** If a check can be computed, compute it. | No LLM in `rules/`. The LLM only perceives (extracts) and judges what is visual or semantic. | [0001](../adr/0001-hybrid-validation-architecture.md) |
| P-02 | **Evidence before verdict.** | Each `Finding` has a page, bbox, observed and expected values, and a rule or model version. | [0004](../adr/0004-canonical-contract.md) |
| P-03 | **Human accountability.** | The system recommends; it never publishes. | [0006](../adr/0006-human-in-the-loop.md) |
| P-04 | **Replaceable capabilities.** | LLM, OCR and reference data sit behind ports (`Protocol`). Vendors are swapped through config. | [0003](../adr/0003-provider-agnostic-llm-port.md) |
| P-05 | **Traceability.** | Requirement → capability → module → test ID ([components.md](components.md#traceability)). | — |
| P-06 | **Authoritative data wins.** | Where PIM or price data exists, it overrides model inference. | [0001](../adr/0001-hybrid-validation-architecture.md) |
| P-07 | **Uncertainty is explicit.** | Five-state status. "Could not check" is never "pass". Severity ⟂ confidence. | [0005](../adr/0005-finding-status-semantics.md) |
| P-08 | **Proportional complexity.** | A modular monolith until a requirement forces a split. No queue or microservices in the PoC. | [0007](../adr/0007-modular-monolith-serverless.md) |
| P-09 | **Evaluation-gated change.** | Prompt, model or rule changes ship only after the golden-set regression passes. | [0008](../adr/0008-evaluation-gated-replay.md) |
