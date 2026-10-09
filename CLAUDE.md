# FlyerCheck — Agent Rules

Read [docs/README.md](docs/README.md) before you change anything. Execution plan: [.docs/adhoc/flyercheck-poc/flyercheck-poc-plan.md](.docs/adhoc/flyercheck-poc/flyercheck-poc-plan.md).

## Hard rules
- Code that does arithmetic, date logic or required-field logic must not call an LLM ([ADR-0001](docs/adr/0001-hybrid-validation-architecture.md)).
- `src/flyercheck/domain/` is the shared contract ([ADR-0004](docs/adr/0004-canonical-contract.md)). In parallel worktrees treat it as **read-only**. Contract changes go through the integrator only.
- Every check returns a `Finding` with one of: `pass | fail | needs_review | not_evaluable | error`. Never return `pass` for a check that could not run ([ADR-0005](docs/adr/0005-finding-status-semantics.md)).
- Every finding carries evidence: page, bbox, observed values, expected values, rule/model version.
- No network calls in tests. LLM adapters must support `replay` mode from `data/recordings/` ([ADR-0008](docs/adr/0008-evaluation-gated-replay.md)).
- Stay inside the files your worktree owns ([plan](.docs/adhoc/flyercheck-poc/flyercheck-poc-plan.md#file-ownership-merge-conflict-free-by-construction)).

## Stack
Python 3.12 · uv · pydantic v2 · PyMuPDF · Pillow · google-genai (`GEMINI_API_KEY`, default `gemini-3.5-flash`) · tenacity · typer · Jinja2 · pytest · ruff

## Commands
```
uv sync
uv run pytest -q
uv run flyercheck run data/samples/Designer.pdf --mode replay --out out/   # record|live need GEMINI_API_KEY
uv run flyercheck eval out/<run>/findings.json data/golden/designer.json
```
