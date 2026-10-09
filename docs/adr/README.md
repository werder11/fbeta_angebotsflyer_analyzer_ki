# Architecture Decision Records

← [docs index](../README.md) · Template: [template.md](template.md)

| ADR | Title | Status | Relations |
|---|---|---|---|
| [0001](0001-hybrid-validation-architecture.md) | Hybrid validation: deterministic rules + LLM for perception | Accepted | enables 0002, 0005 |
| [0002](0002-multimodal-llm-extraction.md) | Multimodal-LLM extraction with bboxes; OCR cross-check in prod | Accepted | depends on 0001, 0003 |
| [0003](0003-provider-agnostic-llm-port.md) | Provider-agnostic LLM port; Gemini 3.5-flash + fallback chain | Accepted | enables 0002, 0008 |
| [0004](0004-canonical-contract.md) | Canonical Offer/Finding contract as the integration boundary | Accepted | enables parallel build |
| [0005](0005-finding-status-semantics.md) | Five-state status; severity ⟂ confidence | Accepted | complements 0004 |
| [0006](0006-human-in-the-loop.md) | Decision support, human approves publication | Accepted | — |
| [0007](0007-modular-monolith-serverless.md) | Modular monolith; serverless container in prod | Accepted | — |
| [0008](0008-evaluation-gated-replay.md) | Golden set + LLM record/replay gate every change | Accepted | depends on 0003 |

```mermaid
flowchart LR
  A1[0001 Hybrid] --> A2[0002 VLM extraction]
  A3[0003 LLM port] --> A2
  A3 --> A8[0008 Eval/replay]
  A1 --> A5[0005 Status]
  A4[0004 Contract] --> A5
  A6[0006 HITL]
  A7[0007 Monolith]
```

Lifecycle: Proposed → Accepted → (Deprecated | Superseded). Don't rewrite accepted ADRs; write a new one.
