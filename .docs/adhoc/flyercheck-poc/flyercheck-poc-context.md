# FlyerCheck PoC — Quick Context

← [plan](flyercheck-poc-plan.md)

**Summary:** A Python CLI that extracts flyer offers with Gemini, validates them with deterministic rules plus a Gemini image↔text check, and outputs an evidence report. Built by 5 parallel worktree agents behind a frozen pydantic contract.

## Key Files
| Purpose | Path |
|---|---|
| Contract (frozen) | `src/flyercheck/domain/models.py`, `src/flyercheck/llm/port.py`, `src/flyercheck/rules/base.py` |
| Orchestration | `src/flyercheck/pipeline.py`, `src/flyercheck/cli.py` |
| Fixtures | `tests/fixtures/designer_context.json`, `tests/fixtures/llm_extract_designer.json`, `tests/fixtures/page1.png` |
| Golden | `data/golden/designer.json` |
| Recordings | `data/recordings/*.json` (committed after Phase 2) |
| Spike provenance | `data/spike/` |
| Input | `data/samples/Designer.pdf` |

## Dependencies
Runtime: `pydantic pymupdf pillow jinja2 typer pyyaml python-dotenv google-genai tenacity` · Dev: `pytest ruff` · Python 3.12 via uv.

## Key Decisions
- Hybrid: the LLM perceives, code verifies ([ADR-0001](../../../docs/adr/0001-hybrid-validation-architecture.md))
- Gemini Developer API, `gemini-3.5-flash` + fallback chain ([ADR-0003](../../../docs/adr/0003-provider-agnostic-llm-port.md))
- Frozen contract and fixtures enable parallelism ([ADR-0004](../../../docs/adr/0004-canonical-contract.md))
- Five statuses ([ADR-0005](../../../docs/adr/0005-finding-status-semantics.md)); record/replay ([ADR-0008](../../../docs/adr/0008-evaluation-gated-replay.md))

## Environment
| Var | Use |
|---|---|
| `GEMINI_API_KEY` | required for `live`/`record` (from `.env`, never committed) |
| `FLYERCHECK_MODELS_EXTRACT` | optional, comma-separated chain override |
| `FLYERCHECK_MODELS_VISION` | optional, comma-separated chain override |

## Commands
```
uv run pytest -q
uv run flyercheck run data/samples/Designer.pdf --mode replay|record|live [--year 2026] [--from-context PATH] --out out/
uv run flyercheck eval out/<run>/findings.json data/golden/designer.json
```

## Related
[Plan](flyercheck-poc-plan.md) · [Research](flyercheck-poc-research.md) · [Tasks](flyercheck-poc-tasks.md) · [Architecture index](../../../docs/README.md)
