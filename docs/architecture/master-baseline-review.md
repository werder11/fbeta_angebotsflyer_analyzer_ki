# Review — Master Architecture Baseline v0

← [architecture](README.md) · [docs index](../README.md)

**Verdict:** The method is sound and the requirements are disciplined: hybrid design, evidence model, five-state status, evaluation as a first-class capability. It is **too abstract for a 1 h prep / 30 min build / 15 min talk**, and it holds back the concrete decisions the task asks for ("LLMs in Azure or GCP"). Keep the substance, cut the ceremony, make decisions.

## Keep
- Hybrid principle: deterministic checks first, LLM for perception (→ [ADR-0001](../adr/0001-hybrid-validation-architecture.md)).
- Canonical Offer/Finding/Evidence model as the boundary (→ [ADR-0004](../adr/0004-canonical-contract.md)).
- `pass / fail / needs_review / not_evaluable / error`; severity ⟂ confidence (→ [ADR-0005](../adr/0005-finding-status-semantics.md)).
- Error taxonomy E-01…E-10 (→ [domain](../domain/domain-model.md#error-taxonomy)).
- Golden set, per-category metrics, regression gate (→ [ADR-0008](../adr/0008-evaluation-gated-replay.md)).
- Human decision boundary (→ [ADR-0006](../adr/0006-human-in-the-loop.md)).

## Cut or shrink for this context
- The TOGAF ADM table: one slide at most, as framing. The reviewers are KI consultants and want the solution.
- 18 FRs and 11 QAs: kept as traceability ([components](components.md#traceability)), not presented.
- "Technology-neutral until justified": already justified by the task's constraint. Decide now ([ADR-0002](../adr/0002-multimodal-llm-extraction.md), [ADR-0003](../adr/0003-provider-agnostic-llm-port.md)).

## Gaps (added here)
1. **No concrete cloud or model choice**, and the brief requires one. → ADR-0003 (Gemini on Vertex AI EU by default, Azure OpenAI as an equal adapter).
2. **No regulatory anchor.** German PAngV (Grundpreis per 1 kg/1 l is mandatory) and UWG (an advertised discount must not overstate the real one) turn "consistency" into concrete rules. → [rules-catalog](../design/rules-catalog.md).
3. **The sample analysis is incomplete.** v0 found 2 defects. A systematic check finds **8+** ([sample analysis](../domain/sample-flyer-analysis.md)), including an **overstated discount** (Pizza −42 % vs. actual 41.52 %), **missing Grundpreis** (Lachs, Schola, Softina) and a weekday/year mismatch.
4. **Rendering bug in v0 §5.2:** the LaTeX for 1.69/320×1000 is broken. The value is 5.28125 → **€5.28/kg**, and the flyer prints 5.59.
5. **No LLM-specific risks:** prompt injection through flyer text, non-determinism, bbox hallucination, model deprecation, data residency for unpublished prices. → [risks](../operations/risks.md).
6. **No replay strategy.** Without recorded LLM responses, tests are flaky and the live demo is fragile. → ADR-0008.
7. **No production path.** Where does it run, how is it triggered, what does it cost? → [deployment](../operations/deployment.md).
8. **v0 was truncated** after §14.1 in the hand-over. Sections 14.2+ (risks, roadmap) were reconstructed here from the task.
