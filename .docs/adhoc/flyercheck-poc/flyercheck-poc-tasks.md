# FlyerCheck PoC — Task Checklist

← [plan](flyercheck-poc-plan.md) · Effort: S ≤ 3 min · M ≤ 8 min · L ≤ 13 min (agent wall-clock)

## Phase 0: Foundation (integrator, sequential) ⏱ 0:00–0:07
- [x] 0.1 `git init -b main`, extend `.gitignore` · S · —
- [x] 0.2 `uv init --package`, add **all** deps, scripts entry, pytest/ruff config · S · 0.1
- [x] 0.3 Paste `domain/models.py` from the plan · S · 0.2
- [x] 0.4 Paste `llm/port.py`, `rules/base.py`; create every stage stub with its final signature · S · 0.3
- [x] 0.5 Fixtures: copy page1.png + spike JSON (+ the Seite-6 text block); write `designer_context.json` · M · 0.3
- [x] 0.6 `data/golden/designer.json`, `tests/conftest.py`, `tests/test_contract.py` · S · 0.5
- [x] 0.7 `pytest` + `ruff` green → commit `phase0` · S · 0.6

**Verify:** `uv run pytest -q` ✓ · `git ls-files | grep '^.env$'` empty ✓

## Phase 1: Parallel tracks ⏱ 0:07–0:20 (launch all 5 agents in ONE message)
| ✓ | Task | Branch | Effort | Acceptance |
|---|---|---|---|---|
| [x] | T1 Gemini adapter + fallback chain + RecordingLLM + factory | feat/llm | M | record→replay round-trip, miss → LLMError, fallback on 503 (offline tests) |
| [x] | T2 ingest (embedded raster, year hint) + extract prompt/schema + normalize | feat/extract | L | normalize table test; FakeLLM extract == fixture; Designer.pdf → 1 page 1024×1536, year 2026 |
| [x] | T3 rules R-01…R-08, R-02b + aggregate | feat/rules | M | reproduces all R-* golden labels + expected passes |
| [x] | T4 V-01 crop + prompt + mapping, concurrency 3 | feat/vision | S–M | mapping matrix tests with FakeLLM |
| [x] | T5 report.html (SVG overlay, table, toggle) + evaluate/format_eval | feat/report | M | HTML rects == findings with bbox; metric math tests |
| [x] | I  pipeline.py + cli.py + test_pipeline (monkeypatched) on main | main | M | `flyercheck --help` works; wiring test green |

**Verify per branch:** own tests green · ruff clean · `git diff --name-only main` ⊆ owned paths

## Phase 2: Integrate & demo (integrator) ⏱ 0:20–0:27
- [x] 2.1 Merge rules → report → vision → llm → extract; `pytest -q` after each · S
- [x] 2.2 `--mode record` on Designer.pdf; commit `data/recordings/` · S
- [x] 2.3 `--mode replay` (offline, < 2 s) · S
- [x] 2.4 `flyercheck eval` → table into `docs/plan/presentation.md` · S
- [x] 2.5 Open the report, screenshot it, `git tag v0.1-poc` · S
- [x] **Decision at 0:22:** if T2 is not merged → demo with `--from-context tests/fixtures/designer_context.json`

## Final Verification (MVP)
### Automated
- [x] `uv run pytest -q` green on main
- [x] `uv run ruff check .` clean
- [x] Replay run exit 0; eval recall = 1.0 on R-* labels; status agreement ≥ 0.9
### Manual
- [x] The report shows all 7 fails / 2 needs_review / 1 not_evaluable from the golden set
- [x] Clicking a finding highlights the correct box
- [x] No secrets in git history

## Phase 3: Enhancements (later, parallel worktrees)
- [ ] E1 two-step blind vision + V-02 · [ ] E2 mutation golden set · [ ] E3 FastAPI + review decisions
- [ ] E4 Azure OpenAI adapter · [ ] E5 geometry/tiling/multi-page · [ ] E6 Docker/Cloud Run/CI gate/cost

## Notes
- Time stamps assume one integrator plus 5 background agents; the integrator writes pipeline/cli while the agents run.
- Any contract change: integrator → main → agents `git rebase main`.
