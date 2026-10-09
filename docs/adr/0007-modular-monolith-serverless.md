# ADR-0007: Modular monolith; serverless container in production

## Status
Accepted

## Context
Load is weekly batches (dozens of flyers, hundreds of pages), with bursts before deadlines. The LLM call dominates latency (seconds per page). The team is small.

## Considered Options
A. Microservice per stage · B. **One Python package with clear module boundaries; deployed as a container on Cloud Run Jobs / Azure Container Apps Jobs, triggered via a queue** · C. Workflow engine (Cloud Workflows / Durable Functions) per stage

## Decision
B. The module boundaries (ports) allow a later split; a page-level fan-out happens inside the job (async LLM calls). Re-evaluate C when multi-step human approvals or more than 1k pages/day appear.

## Consequences
**+** one deployable, trivial local dev, scales to zero. **−** a stage can't scale independently (not needed: every stage is LLM-bound).

## Links
[system-context](../architecture/system-context.md) · [deployment](../operations/deployment.md)
