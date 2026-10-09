# Interfaces

← [docs index](../README.md) · ADR: [0004](../adr/0004-canonical-contract.md)

## CLI (PoC)
```
flyercheck run <file.pdf> [--year 2026] [--mode replay|record|live] [--provider gemini|azure] --out out/
flyercheck eval out/<run>/findings.json data/golden/designer.json
```

## REST API (implemented, `flyercheck serve`)
Machine-readable spec: **[openapi.json](openapi.json)** (generated from code; interactive docs at `/docs` when running). Data schemas: **[data/schemas/](../../data/schemas/README.md)**.

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Liveness |
| POST | `/v1/validations` | Multipart upload `file` + form `mode` (replay\|record\|live), `year`, `provider` (gemini\|azure) → `201 {run_id, status_counts, offers, report_url, findings_url}` |
| GET | `/v1/validations` | List runs (newest first) |
| GET | `/v1/validations/{run_id}` | Run summary + status and decision counts |
| GET | `/v1/validations/{run_id}/findings[?status=fail]` | Findings, each with its latest review decision |
| GET | `/v1/validations/{run_id}/report` | HTML evidence report |
| POST | `/v1/validations/{run_id}/findings/{finding_id}/decision` | `{decision: confirm\|reject\|escalate, reviewer?, reason?}` → `201 ReviewDecision` |
| GET | `/v1/validations/{run_id}/decisions` | All decisions (append-only audit log) |

Errors: 400 invalid input/run id, 404 unknown run/finding, 422 validation or LLM failure (e.g. replay miss). PoC: synchronous, file-based store (`out/<run_id>/`); production: queue + Postgres ([ADR-0007](../adr/0007-modular-monolith-serverless.md)).

## Finding JSON
Generated from pydantic → `schemas/finding.schema.json` (Wave 0). Example:
```json
{
  "id": "f-6-R01", "run_id": "a1b2c3d4-20261009", "offer_id": "o-6",
  "check_id": "R-01", "category": "E03_arithmetic", "severity": "critical", "status": "fail",
  "summary": "Printed unit price 5.59 €/kg ≠ computed 5.28 €/kg (1.69 € / 0.320 kg)",
  "observed": {"price": "1.69", "quantity": "320 g", "unit_price_printed": "5.59"},
  "expected": {"unit_price": "5.28", "basis": "EUR/kg"},
  "evidence": [{"page": 1, "bbox": [0.68, 0.38, 0.99, 0.57], "source": "flyer", "raw": "(1 kg = 5,59)"}],
  "confidence": 0.95, "rule_version": "R-01@1.0", "model_version": "extract:gemini-2.5-pro@prompt-v1"
}
```
