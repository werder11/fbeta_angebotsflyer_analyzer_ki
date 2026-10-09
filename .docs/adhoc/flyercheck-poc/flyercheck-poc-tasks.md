# FlyerCheck PoC — Task Checklist

← [plan](flyercheck-poc-plan.md) · Effort: S ≤ 3 min · M ≤ 8 min · L ≤ 13 min (agent wall-clock)

## Phase 0: Foundation (integrator, sequential) ⏱ 0:00–0:07
- [ ] 0.1 `git init -b main`, extend `.gitignore` · S · —
- [ ] 0.2 `uv init --package`, add **all** deps, scripts entry, pytest/ruff config · S · 0.1
- [ ] 0.3 Paste `domain/models.py` from the plan · S · 0.2
- [ ] 0.4 Paste `llm/port.py`, `rules/base.py`; create every stage stub with its final signature · S · 0.3
- [ ] 0.5 Fixtures: copy page1.png + spike JSON (+ the Seite-6 text block); write `designer_context.json` · M · 0.3
- [ ] 0.6 `data/golden/designer.json`, `tests/conftest.py`, `tests/test_contract.py` · S · 0.5
- [ ] 0.7 `pytest` + `ruff` green → commit `phase0` · S · 0.6

**Verify:** `uv run pytest -q` ✓ · `git ls-files | grep '^.env$'` empty ✓

## Phase 1: Parallel tracks ⏱ 0:07–0:20 (launch all 5 agents in ONE message)
| ✓ | Task | Branch | Effort | Acceptance |
|---|---|---|---|---|
| [ ] | T1 Gemini adapter + fallback chain + RecordingLLM + factory | feat/llm | M | record→replay round-trip, miss → LLMError, fallback on 503 (offline tests) |
| [ ] | T2 ingest (embedded raster, year hint) + extract prompt/schema + normalize | feat/extract | L | normalize table test; FakeLLM extract == fixture; Designer.pdf → 1 page 1024×1536, year 2026 |
| [ ] | T3 rules R-01…R-08, R-02b + aggregate | feat/rules | M | reproduces all R-* golden labels + expected passes |
| [ ] | T4 V-01 crop + prompt + mapping, concurrency 3 | feat/vision | S–M | mapping matrix tests with FakeLLM |
| [ ] | T5 report.html (SVG overlay, table, toggle) + evaluate/format_eval | feat/report | M | HTML rects == findings with bbox; metric math tests |
| [ ] | I  pipeline.py + cli.py + test_pipeline (monkeypatched) on main | main | M | `flyercheck --help` works; wiring test green |

**Verify per branch:** own tests green · ruff clean · `git diff --name-only main` ⊆ owned paths

## Phase 2: Integrate & demo (integrator) ⏱ 0:20–0:27
- [ ] 2.1 Merge rules → report → vision → llm → extract; `pytest -q` after each · S
- [ ] 2.2 `--mode record` on Designer.pdf; commit `data/recordings/` · S
- [ ] 2.3 `--mode replay` (offline, < 2 s) · S
- [ ] 2.4 `flyercheck eval` → table into `docs/plan/presentation.md` · S
- [ ] 2.5 Open the report, screenshot it, `git tag v0.1-poc` · S
- [ ] **Decision at 0:22:** if T2 is not merged → demo with `--from-context tests/fixtures/designer_context.json`

## Final Verification (MVP)
### Automated
- [ ] `uv run pytest -q` green on main
- [ ] `uv run ruff check .` clean
- [ ] Replay run exit 0; eval recall = 1.0 on R-* labels; status agreement ≥ 0.9
### Manual
- [ ] The report shows all 7 fails / 2 needs_review / 1 not_evaluable from the golden set
- [ ] Clicking a finding highlights the correct box
- [ ] No secrets in git history

## Phase 3: Enhancements (later, parallel worktrees)
- [ ] E1 two-step blind vision + V-02 · [ ] E2 mutation golden set · [ ] E3 FastAPI + review decisions
- [ ] E4 Azure OpenAI adapter · [ ] E5 geometry/tiling/multi-page · [ ] E6 Docker/Cloud Run/CI gate/cost

## Notes
- Time stamps assume one integrator plus 5 background agents; the integrator writes pipeline/cli while the agents run.
- Any contract change: integrator → main → agents `git rebase main`.
