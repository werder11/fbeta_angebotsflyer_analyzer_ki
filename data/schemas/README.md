# Data Schemas

JSON Schemas (draft 2020-12) for every data contract of FlyerCheck. **Generated** from code by `uv run python scripts/export_specs.py` — do not edit by hand; `tests/test_specs.py` fails if they are stale.

REST API: [docs/api/openapi.json](../../docs/api/openapi.json) · Contract docs: [docs/domain/domain-model.md](../../docs/domain/domain-model.md) · ADR: [0004 canonical contract](../../docs/adr/0004-canonical-contract.md)

| Schema | Describes |
|---|---|
| [`run-result.schema.json`](run-result.schema.json) | out/<run_id>/findings.json — full run incl. context + findings |
| [`finding.schema.json`](finding.schema.json) | a single finding (check result with evidence) |
| [`document-context.schema.json`](document-context.schema.json) | normalized offers + document facts (tests/fixtures/designer_context.json, `--from-context`) |
| [`offer.schema.json`](offer.schema.json) | one extracted offer (raw + normalized values) |
| [`review-decision.schema.json`](review-decision.schema.json) | human decision, out/<run_id>/decisions.jsonl |
| [`golden-set.schema.json`](golden-set.schema.json) | data/golden/*.json — evaluation labels |
| [`reference-item.schema.json`](reference-item.schema.json) | parsed reference record (R-08) |
| [`reference-price-csv.schema.json`](reference-price-csv.schema.json) | data/reference/*.csv row format |
| [`llm-extract-response.schema.json`](llm-extract-response.schema.json) | response schema sent to the LLM for page extraction (structured output) |
| [`llm-vision-v01-response.schema.json`](llm-vision-v01-response.schema.json) | response schema sent to the LLM for the V-01 image↔text check |
| [`llm-recording.schema.json`](llm-recording.schema.json) | data/recordings/*.json — record/replay cache |
