# ADR-0009: Review UI as server-rendered pages (FastAPI + Jinja2 + HTMX), self-hosted assets

## Status
Proposed (2026-10-09)

## Context
Reviewers need a web UI to work through findings with visual evidence and record decisions (ADR-0006). The data is confidential (unpublished prices), so the browser must not load third-party resources. The team is small and the backend is a Python modular monolith (ADR-0007) that already has a REST API and an HTML evidence report.

## Decision Drivers
Confidentiality (no external assets, strict CSP) · same-origin auth via SSO proxy · delivery speed · one deployable · testability without a JS toolchain

## Considered Options
### A. React/Vite SPA against the REST API
+ rich interactions, large ecosystem · − separate build pipeline and deployable, larger attack surface (npm supply chain), CSP and auth across two origins, more effort
### B. Streamlit / Gradio
+ very fast prototype · − limited control over CSP/headers and auth, weak fit for a keyboard-driven review workflow, its own server process
### C. Server-rendered Jinja2 + HTMX inside the existing FastAPI app, vendored assets
+ one deployable and one origin, strict CSP is easy (no inline scripts), no npm supply chain, reuses the report's overlay approach, testable with TestClient · − less suited to very rich client interactions

## Decision
**Option C.** UI routes live under `/ui/`, share the service layer with `/v1/` API routes, and serve only self-hosted static assets. Authentication comes from an SSO proxy header (Google IAP / Entra ID) mapped to roles.

## Consequences
**Positive:** minimal moving parts; confidentiality constraints are enforceable and testable (CSP, "no external URL" test); the same container runs on Cloud Run or Container Apps.
**Negative:** complex client widgets (e.g. advanced image annotation) would need more custom JS; revisit if the UI grows beyond review workflows.
**Risks:** HTMX partial updates need care for accessibility → keyboard/focus tests.

## Links
Design: [ui-spec.md](../design/ui-spec.md) · Related: [0006](0006-human-in-the-loop.md), [0007](0007-modular-monolith-serverless.md) · API: [openapi.json](../api/openapi.json)
