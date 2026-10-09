# ADR-0004: Canonical Offer/Finding contract as the integration boundary

## Status
Accepted

## Context
Extraction, rules, vision checks, report and eval are built **in parallel by separate agents in separate git worktrees**. They need one stable contract. Observation, validation and decision must stay separate for auditability.

## Decision Drivers
Parallel development without merge conflicts · testability with fixtures · audit

## Considered Options
A. Pass loose dicts between stages · B. **Pydantic v2 models in `domain/`, exported as JSON Schema** · C. Protobuf
(C is overkill in-process; A breaks under parallel development.)

## Decision
B. `src/flyercheck/domain/models.py` is written **first (Wave 0)** and frozen. A versioned JSON schema is exported to `docs/api/schemas/`. Fixtures (`tests/fixtures/designer_offers.json`) let every module be built and tested without upstream code.

## Consequences
**Positive:** teams and agents code against fixtures; integration is a wiring exercise.
**Negative:** contract changes need coordination (only the integrator changes it).

## Links
[domain-model](../domain/domain-model.md) · [api](../api/README.md) · [plan](../plan/implementation-plan.md)
