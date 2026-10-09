# FlyerCheck — Architecture Documentation

AI-assisted consistency validation for retail promotional flyers (Angebotsflyer).
The system ingests a flyer PDF, extracts offers with their location on the page, runs **deterministic rules** and **targeted multimodal-LLM checks**, and gives a human reviewer findings backed by evidence.

> **Current phase:** PoC — 30-min implementation sprint + 10-min presentation.
> **Implementation plan (detailed, executable):** [../.docs/adhoc/flyercheck-poc/flyercheck-poc-plan.md](../.docs/adhoc/flyercheck-poc/flyercheck-poc-plan.md) · tasks: [checklist](../.docs/adhoc/flyercheck-poc/flyercheck-poc-tasks.md)
> **Agent rules:** [../CLAUDE.md](../CLAUDE.md)

## How to navigate (humans and coding agents)

1. Read this file.
2. [architecture/principles.md](architecture/principles.md): the non-negotiables.
3. [architecture/system-context.md](architecture/system-context.md) → [architecture/components.md](architecture/components.md): the structure.
4. [domain/domain-model.md](domain/domain-model.md): **the contract all modules share.**
5. The ADRs for the area you touch.
6. The design doc for your component ([design/](design/README.md)).
7. Implement; then update the docs if a boundary changed.

## Documentation map

| Layer | Question it answers | Entry |
|---|---|---|
| Vision | Why does this exist? What counts as success? | [vision/README.md](vision/README.md) |
| Architecture | What is the structure? | [architecture/README.md](architecture/README.md) |
| Domain | Which concepts and contracts exist? | [domain/README.md](domain/README.md) |
| Design | How does each component work? | [design/README.md](design/README.md) |
| Decisions | Why was it built this way? | [adr/README.md](adr/README.md) |
| Interfaces | How do components and clients communicate? | [api/README.md](api/README.md) |
| Operations | How is it deployed, evaluated, monitored? What are the risks? | [operations/README.md](operations/README.md) |
| Plan | How do we build it fast, in parallel? | [plan/implementation-plan.md](plan/implementation-plan.md) |

## Active decisions

| ADR | Topic | Status |
|---|---|---|
| [ADR-0001](adr/0001-hybrid-validation-architecture.md) | Hybrid: deterministic rules + LLM for perception only | Accepted |
| [ADR-0002](adr/0002-multimodal-llm-extraction.md) | Multimodal-LLM extraction with bounding boxes (OCR cross-check in prod) | Accepted |
| [ADR-0003](adr/0003-provider-agnostic-llm-port.md) | Provider-agnostic LLM port; Gemini (`gemini-3.5-flash` + fallback chain) | Accepted |
| [ADR-0004](adr/0004-canonical-contract.md) | Canonical Offer/Finding contract as the integration boundary | Accepted |
| [ADR-0005](adr/0005-finding-status-semantics.md) | Five-state finding status; severity ⟂ confidence | Accepted |
| [ADR-0006](adr/0006-human-in-the-loop.md) | Decision support only, no auto-publish | Accepted |
| [ADR-0007](adr/0007-modular-monolith-serverless.md) | Modular monolith; serverless container in prod | Accepted |
| [ADR-0008](adr/0008-evaluation-gated-replay.md) | Golden set + recorded LLM replay gate every change | Accepted |

## Source material

- The task (Arbeitsprobe KI Consultant) and the sample flyer `Designer.pdf` go in `data/samples/`.
- Master architecture baseline v0: reviewed in [architecture/master-baseline-review.md](architecture/master-baseline-review.md). Its content has been split into the layers above.
