# Evaluation & Monitoring

← [operations](README.md) · ADR: [0008](../adr/0008-evaluation-gated-replay.md)

## Golden set
- Start with `designer.json` (10 labels, see [sample analysis](../domain/sample-flyer-analysis.md)).
- Pilot: 20–50 historical flyers, using **real past defects from the review logs** plus **synthetic mutations** (change a price, swap an image, delete a Grundpreis, shift a date). Mutation testing gives labeled positives at scale.
- Every label records page, bbox, check, expected status, severity, labeler and adjudication.

## Metrics (per category and severity, never only aggregate)
Precision = TP/(TP+FP) · Recall = TP/(TP+FN) · F1 · evidence completeness · `not_evaluable` rate · `error` rate · p95 latency · € per flyer · reviewer minutes per flyer · reviewer reject rate (a live precision proxy).
Matching rule: a predicted finding matches a label when `check_id` and `offer` (bbox IoU ≥ 0.3 or name match) agree.

## Release gate
Any change to a prompt, model, rule or extraction parameter → record → eval → no critical-category recall drop, precision ≥ baseline − 2 pp → human review of the diff → release (with a pinned model version).

## Runtime monitoring
LLM trace per call (prompt version, tokens, latency, cost); drift: the weekly reviewer reject rate per check; alerts when the error rate exceeds 2 % or the schema-violation rate rises.
