# ADR-0006: Decision support; a human approves publication

## Status
Accepted

## Context
Pricing errors in flyers have legal (PAngV, UWG) and reputational consequences. AI judgements are probabilistic. EU AI Act: this is not a high-risk use case, but transparency and human oversight are good practice.

## Decision
FlyerCheck **recommends**. A reviewer confirms, rejects or escalates each `fail`/`needs_review`. Publication approval stays in the existing workflow. Reviewer decisions are stored and feed the golden set (active learning loop). "No findings" is never presented as "defect-free".

## Consequences
**+** clear accountability; reviewer feedback improves the system. **−** savings are bounded by the review time per finding, so precision matters (QA-02).
**Automation path:** once per-category precision is proven, low-severity `pass` categories can be auto-accepted (a sampled audit continues).

## Links
[vision](../vision/README.md) · [risks](../operations/risks.md)
