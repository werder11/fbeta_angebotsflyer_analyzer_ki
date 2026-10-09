# FlyerCheck

AI-assisted consistency validation for retail promotional flyers (Angebotsflyer). FlyerCheck takes a flyer PDF,
extracts every offer with its position on the page, runs deterministic rules (unit price, discount, deposit,
mandatory Grundpreis, validity dates, page references, master data) plus targeted multimodal-LLM checks
(does the image match the text?), and produces a report in which every finding carries evidence: page, bounding
box, observed and expected values, and the rule or model version.

**Findings are decision support, not a verdict.** A human reviewer confirms, rejects or escalates each finding;
nothing is auto-published ([ADR-0006](docs/adr/0006-human-in-the-loop.md)). "No findings" does not mean
"defect-free".

## Architecture at a glance

**The LLM perceives, code verifies, the human decides.**

```
PDF ─▶ ingest ─▶ extract (multimodal LLM: offers + bboxes) ─▶ normalize ─┬─▶ rules R-01..R-08 (pure Python) ─┐
                                                                        └─▶ vision checks V-01 (LLM)        ─┴─▶ aggregate ─▶ findings.json + report.html ─▶ reviewer
```

- Arithmetic, date and required-field logic never calls an LLM ([ADR-0001](docs/adr/0001-hybrid-validation-architecture.md)).
- The LLM sits behind a provider-agnostic port: Gemini by default, Azure OpenAI as an alternative
  ([ADR-0003](docs/adr/0003-provider-agnostic-llm-port.md)).
- All modules share one canonical `Offer`/`Finding` contract ([ADR-0004](docs/adr/0004-canonical-contract.md)).
- Five finding states: `pass | fail | needs_review | not_evaluable | error`. A check that cannot run never
  reports `pass` ([ADR-0005](docs/adr/0005-finding-status-semantics.md)).
- Modular monolith, deployed as one serverless container ([ADR-0007](docs/adr/0007-modular-monolith-serverless.md)).
- LLM calls are recorded and replayed; a golden set gates every change ([ADR-0008](docs/adr/0008-evaluation-gated-replay.md)).

Full documentation: [docs/README.md](docs/README.md).

## Quickstart

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync

# Validate the sample flyer offline, using recorded LLM responses
uv run flyercheck run data/samples/Designer.pdf --mode replay --out out
# ✔ 9 offers · 7 fail · 2 needs_review · 10 not_evaluable · 35 pass   (replay, 0.6s)
# → out/<run>/findings.json
# → out/<run>/report.html

# Score the run against the golden labels
uv run flyercheck eval out/<run>/findings.json data/golden/designer.json
```

Live LLM calls (`--mode record` stores responses in `data/recordings/`, `--mode live` does not) need a key:

```bash
cp .env.sample .env          # then set GEMINI_API_KEY
uv run flyercheck run data/samples/Designer.pdf --mode record --out out
```

REST API (validations, findings, review decisions; see [docs/api](docs/api/README.md)):

```bash
uv run flyercheck serve --host 127.0.0.1 --port 8000
```

Container:

```bash
docker build -t flyercheck .
docker run --rm -p 8080:8080 flyercheck                                   # API on :8080 ($PORT respected)
docker run --rm flyercheck flyercheck run data/samples/Designer.pdf --mode replay
```

## What it finds on the sample flyer

`data/samples/Designer.pdf` is a one-page synthetic flyer. The hand-verified golden findings
([sample-flyer-analysis.md](docs/domain/sample-flyer-analysis.md), [data/golden/designer.json](data/golden/designer.json)):

| ID | Offer | Check | Status | Evidence |
|---|---|---|---|---|
| G-01 | Schola Schokolade | V-01 image ↔ text | fail | Image shows an aubergine; text says milk chocolate |
| G-02 | Steinofen Pizza | R-01 unit price | fail | 1.69 € / 0.32 kg = 5.28 €/kg, printed 5.59 €/kg |
| G-03 | Steinofen Pizza | R-02 discount | fail | −42 % advertised, actual 41.52 % (overstated) |
| G-04 | Document | R-02b rounding consistency | needs_review | Bergtal rounds down (33.90 → −33 %), Pizza rounds up (41.52 → −42 %) |
| G-05 | Nordmeer Lachsfilet | R-04 Grundpreis | fail | No €/kg shown; expected 29.90 €/kg |
| G-06 | Schola Schokolade | R-04 Grundpreis | fail | No €/kg shown; expected 9.90 €/kg |
| G-07 | Softina Toilettenpapier | R-04 Grundpreis | needs_review | No unit price; basis (sheet/roll) is a policy decision |
| G-08 | Campaign | R-05 weekday ↔ date | fail | "Mo. 07.10." is a Wednesday in 2026 (year from PDF metadata) |
| G-09 | Recipe teaser | R-07 page reference | fail | "Rezept auf Seite 6", document has 1 page |
| G-10 | All offers | R-08 master-data price | not_evaluable | No PIM reference data supplied |

Plus 10 expected passes (correct unit prices, discounts, deposit, matching images) that guard against false
positives. PoC result in replay: overall precision 1.00, recall 1.00, status agreement 1.00
([presentation.md](docs/plan/presentation.md#poc-results-2026-10-09-v01-poc)). One synthetic flyer is a functional
test, not an accuracy claim.

## CLI reference

| Command | Purpose |
|---|---|
| `flyercheck run PDF [--mode replay\|record\|live] [--out DIR] [--year N] [--provider gemini\|azure] [--reference CSV] [--from-context JSON]` | Validate a flyer; writes `findings.json` and `report.html` to `DIR/<run>/` |
| `flyercheck eval FINDINGS [GOLDEN]` | Per-category precision/recall, status agreement, missing and mismatched labels |
| `flyercheck mutate-eval [CONTEXT]` | Seed synthetic defects into a normalized context and measure rule detection per operator |
| `flyercheck serve [--host H] [--port P] [--out DIR]` | Run the REST API |

`uv run flyercheck <command> --help` lists every option.

## Project layout

```
src/flyercheck/
  domain/          canonical contract: Offer, Finding, RunResult, GoldenSet (ADR-0004)
  ingest/          PDF → page images, document metadata
  llm/             provider port, Gemini / Azure adapters, record/replay
  extract/         multimodal extraction of offers with bounding boxes
  normalize/       raw strings → typed prices, quantities, validity
  rules/           deterministic checks R-01..R-08 (no LLM)
  vision_checks/   targeted LLM checks (V-01 image ↔ text)
  aggregate/       merge and order findings
  reference/       master-data reference prices (R-08)
  report/          self-contained HTML report
  evaluation/      golden-set scoring, mutation testing
  api/             REST API and review decisions
  pipeline.py      end-to-end orchestration
  cli.py           Typer CLI
data/
  samples/         sample flyer
  golden/          golden labels
  recordings/      recorded LLM responses for replay
tests/             offline unit and pipeline tests
scripts/           eval_gate.py (CI evaluation gate)
deploy/cloudrun/   Cloud Run / Container Apps deployment notes (target state)
docs/              architecture, domain, design, ADRs, operations
```

## Testing

All tests run offline; LLM calls are served from `data/recordings/`.

```bash
uv run ruff check .
uv run pytest -q

# Evaluation gate as run in CI: fails if overall recall < 1.0 or status agreement < 0.9
uv run flyercheck run data/samples/Designer.pdf --mode replay --out out
uv run python scripts/eval_gate.py out/*/findings.json data/golden/designer.json --min-recall 1.0 --min-agreement 0.9
```

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs lint → tests → replay → evaluation gate on every
push and pull request to `dev` and `main`, and uploads the HTML report as an artifact. A prompt or model change
requires a fresh `record` run and a reviewed eval diff.

## Documentation

| Topic | Entry |
|---|---|
| Index and navigation | [docs/README.md](docs/README.md) |
| Architecture decisions | [docs/adr/](docs/adr/README.md) |
| Rules catalog | [docs/design/rules-catalog.md](docs/design/rules-catalog.md) |
| Deployment (target) | [docs/operations/deployment.md](docs/operations/deployment.md), [deploy/cloudrun/](deploy/cloudrun/README.md) |
| Evaluation and monitoring | [docs/operations/evaluation-and-monitoring.md](docs/operations/evaluation-and-monitoring.md) |
| Risks and limits | [docs/operations/risks.md](docs/operations/risks.md) |

## Status and roadmap

**Current: proof of concept (`v0.1-poc`).** Single synthetic flyer, replayable end to end, golden-set gate in CI.
Cloud deployment is documented but not provisioned.

1. **PoC:** one flyer, replayable, findings report.
2. **Shadow pilot (4–6 weeks):** run alongside the manual review on ~20 real flyers; build a golden set from real
   review logs plus synthetic mutations; measure the baseline.
3. **Assisted production:** DTP/PIM integration, review UI, monitoring, evaluation-gated releases.
4. **Scale-out:** master-data checks against PIM and the price database, regional variants, multi-page cross-checks.

See [docs/vision/README.md](docs/vision/README.md#roadmap).
