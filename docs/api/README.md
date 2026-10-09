# Interfaces

← [docs index](../README.md) · ADR: [0004](../adr/0004-canonical-contract.md)

## CLI (PoC)
```
flyercheck run <file.pdf> [--year 2026] [--mode replay|record|live] [--provider gemini|azure] --out out/
flyercheck eval out/<run>/findings.json data/golden/designer.json
```

## REST (target)
| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/validations` | Upload PDF + metadata `{campaign_year, region, campaign_id}` → `202 {run_id}` |
| GET | `/v1/validations/{run_id}` | Status + summary |
| GET | `/v1/validations/{run_id}/findings` | `Finding[]` |
| POST | `/v1/findings/{id}/decision` | `{decision: confirm\|reject\|escalate, reason}` |
| GET | `/v1/validations/{run_id}/report` | HTML report |

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
