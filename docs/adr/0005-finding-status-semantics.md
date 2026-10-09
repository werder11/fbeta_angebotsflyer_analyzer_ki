# ADR-0005: Five-state finding status; severity independent of confidence

## Status
Accepted

## Context
The classic failure of automated QA is a check that did not run (missing data, timeout) and is reported as green. Reviewers must also triage: a critical but uncertain finding still needs urgent attention.

## Decision
`Status ∈ {pass, fail, needs_review, not_evaluable, error}`. `Severity ∈ {critical, high, medium, low, info}`, set by business policy per check. `confidence ∈ [0,1]` comes from evidence quality. They are never combined into one score until a calibrated policy exists. The report shows passes too, so "checked and OK" is visible and different from "not checked".

## Consequences
**+** honest coverage reporting; the reviewer sees what *wasn't* checked. **−** more states to handle in the UI.

## Links
[domain-model §status](../domain/domain-model.md#status-semantics-adr-0005) · [ADR-0004](0004-canonical-contract.md)
