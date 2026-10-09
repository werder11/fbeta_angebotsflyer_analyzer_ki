# Review UI — Plan & Specification

← [design](README.md) · [docs index](../README.md) · ADR: [0009 UI technology](../adr/0009-review-ui-server-rendered.md), [0006 human-in-the-loop](../adr/0006-human-in-the-loop.md) · API: [openapi.json](../api/openapi.json)

**Status:** Proposed, ready for implementation. **Goal:** a secure web UI where QA reviewers upload flyers, work through findings with visual evidence, record decisions, and hand a documented result to the existing approval workflow.

## 1. Users & jobs to be done

| Role | Job | Frequency |
|---|---|---|
| **Reviewer** (QA, Marketing) | Check this week's flyers: see what is wrong, where, and why; confirm/reject/escalate quickly | weekly, under deadline |
| **Approver** (team lead) | See whether all critical findings are resolved before sign-off | weekly |
| **Admin** (AI/IT) | Watch quality metrics, model/rule versions, failures, cost | ongoing |

Primary success metric: **time per flyer for review** (baseline vs. with UI) and **share of findings with a decision**.

## 2. Confidentiality requirements ("vertraulich") → design constraints

| ID | Requirement | Consequence |
|---|---|---|
| S-01 | No data leaves the trust boundary via the browser | **No CDNs, web fonts, analytics or third-party scripts**; all assets self-hosted and served same-origin |
| S-02 | Strict Content-Security-Policy | `default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; frame-ancestors 'none'`; no inline scripts → JS in static files |
| S-03 | Authenticated access only | Prod: SSO in front (Google IAP or Entra ID / Easy Auth); app reads the verified identity header. PoC: dev identity via env `FLYERCHECK_DEV_USER` |
| S-04 | Least privilege | Roles reviewer / approver / admin; decisions only by reviewer+; evaluation/settings only admin |
| S-05 | Auditability | Every decision is append-only (who, when, what, why) — already in `decisions.jsonl`; UI shows the history and never edits/deletes |
| S-06 | No residue on clients | No localStorage of business data; `Cache-Control: no-store` on data responses; session timeout; downloads only via explicit export |
| S-07 | Visible classification | Header banner "VERTRAULICH – nur für den internen Gebrauch"; exported files carry the same label |
| S-08 | Secure transport & headers | HTTPS only (platform), `X-Content-Type-Options`, `Referrer-Policy: no-referrer`, `Permissions-Policy` minimal |
| S-09 | Upload safety | PDF/PNG/JPG only, size limit (e.g. 25 MB), content-type sniffing, random server-side filenames (already in API) |
| S-10 | Data residency & retention | Runs stored in EU storage; retention policy (e.g. 90 days for sources, longer for findings/decisions) |

## 3. Information architecture & screens

```mermaid
flowchart LR
  L[Login via SSO] --> D[Läufe-Übersicht]
  D --> U[Flyer hochladen]
  U --> R[Review-Arbeitsplatz]
  D --> R
  R --> S[Freigabe-Zusammenfassung]
  S --> X[Export: PDF/JSON Audit]
  D --> E[Qualität & Modelle\n(Admin)]
  D --> K[Prüfkatalog\n(read-only)]
```

### 3.1 Läufe-Übersicht (`/ui/`)
Table of runs: document, uploaded at/by, status chips (fail / needs_review / not_evaluable / pass), **review progress** (decided/open), "Bereit zur Freigabe?" indicator. Filter by week and status. Primary button "Flyer prüfen".

### 3.2 Flyer hochladen (`/ui/upload`)
Drag & drop file, optional campaign year, option "Stammdaten-Abgleich" (reference data source), mode (admin only: live/record/replay). Shows a progress state while the pipeline runs (~40 s live), then redirects to the review workspace.

### 3.3 Review-Arbeitsplatz (`/ui/runs/{run_id}`) — the core screen
```
┌ VERTRAULICH ─────────────────────────────────────────────── user ▾ ┐
│ Designer.pdf · KW41 · 7 fail · 2 review · 10 nicht prüfbar · 35 ok │  progress ▓▓▓░░ 3/9 entschieden
├──────────────────────────────┬──────────────────────────────────────┤
│  Flyer (zoom / pan)          │ Filter: [fail][review][n.p.][ok]     │
│  ┌──────────────┐            │ ▸ R-01 Pizza  Grundpreis 5,59≠5,28   │
│  │   ┌─────┐    │            │ ▸ V-01 Schola Bild zeigt Aubergine   │
│  │   │ ▓▓▓ │◀── selected box │ ▸ R-02 Pizza  Rabatt −42 % > 41,52 % │
│  │   └─────┘    │            ├──────────────────────────────────────┤
│  └──────────────┘            │ Detail: beobachtet → erwartet,       │
│                              │ Formel, Evidenz-Ausschnitt, Regel-/  │
│                              │ Modellversion, Konfidenz             │
│                              │ [✓ Bestätigen] [✗ Verwerfen] [↑ Esk.] │
│                              │ Begründung: ________                 │
│                              │ Historie: E. Doe bestätigt 10:42     │
└──────────────────────────────┴──────────────────────────────────────┘
```
- Selecting a finding highlights its box (and vice versa); evidence crop shown enlarged.
- Keyboard: `J/K` next/prev, `C` confirm, `R` reject, `E` escalate, `/` filter.
- Findings grouped by severity; `pass` collapsed by default; `not_evaluable` shown with the missing dependency ("Stammdaten fehlen").
- Decision form posts to the existing API endpoint; list updates without full reload.

### 3.4 Freigabe-Zusammenfassung (`/ui/runs/{run_id}/summary`)
Checklist: all critical/high `fail` decided? Escalations open? Not-evaluable checks listed explicitly ("nicht geprüft"). Recommendation only ("Empfehlung: Korrektur erforderlich") — no publish button (ADR-0006). Export: audit JSON (findings + decisions + versions) and printable HTML/PDF with confidentiality footer.

### 3.5 Qualität & Modelle (`/ui/admin/quality`, admin)
Golden-set metrics per category, mutation-eval per operator, model/prompt/rule versions in use, recent errors, LLM usage per run.

### 3.6 Prüfkatalog (`/ui/checks`)
Read-only list of checks (R-01…R-10, V-01, V-02) with description, legal basis, version — builds trust and explains findings.

## 4. Technical design

| Aspect | Decision |
|---|---|
| Rendering | **Server-rendered Jinja2 templates inside the existing FastAPI app** + **HTMX** (vendored, self-hosted) for partial updates ([ADR-0009](../adr/0009-review-ui-server-rendered.md)) |
| Styling | One self-hosted CSS file with design tokens (no web fonts; system font stack) |
| Flyer viewer | `<img>` + SVG overlay in normalized coordinates (same approach as `report.html`), CSS transform zoom/pan, ~100 lines vanilla JS in a static file |
| Data access | UI routes call the same service layer/store as the REST API (no second data path) |
| New API needs | `GET /v1/validations/{run_id}/pages/{n}` (page image, auth-checked, no-store) · `GET /v1/validations/{run_id}/export` (audit JSON) · `GET /v1/me` (identity + role) |
| Auth | Middleware: identity from trusted header (`X-Goog-Authenticated-User-Email` / `X-MS-CLIENT-PRINCIPAL-NAME`) when `FLYERCHECK_AUTH=proxy`; `FLYERCHECK_DEV_USER` for local; role mapping via env/config |
| Security headers | Middleware sets CSP and headers from §2 on every response; tested |
| Accessibility | Keyboard-only operation, visible focus, status not by colour alone (icons + text), WCAG AA contrast |
| Language | German UI texts (single i18n dict for later EN) |
| Testing | TestClient: page renders, decision round-trip via UI form, CSP header present, no external URLs in HTML (`http(s)://` outside same origin → test fails), role checks |

## 5. Implementation plan (parallel, contract-first — same method as PoC)

| Phase | Track | Owns | Done when |
|---|---|---|---|
| **U0 Foundation** (sequential, ~10 min) | integrator | `ui/__init__.py` (router mount), `ui/templates/base.html`, `ui/static/app.css` + vendored `htmx.min.js`, security-headers + auth middleware stubs, new API endpoints (page image, export, me) as stubs, i18n dict | `/ui/` renders base layout; tests for CSP + no external URLs |
| **U1** | Läufe & Upload | `ui/routes_runs.py`, `templates/runs*.html`, `templates/upload.html` | upload → redirect to workspace; list with progress |
| **U2** | Review-Arbeitsplatz | `ui/routes_review.py`, `templates/review*.html`, `static/viewer.js` | select ↔ highlight, decision via HTMX, keyboard shortcuts |
| **U3** | Freigabe & Export | `ui/routes_summary.py`, `templates/summary.html`, export endpoint impl | checklist + audit JSON + printable view |
| **U4** | Qualität & Prüfkatalog | `ui/routes_admin.py`, `templates/admin*.html`, `templates/checks.html` | metrics from eval/mutate, catalog |
| **U5** | Security & Auth | `ui/security.py`, `ui/auth.py`, `tests/test_ui_security.py` | CSP/headers, proxy+dev auth, role enforcement, no-store, upload limits |

Merge order U5 → U1 → U2 → U3 → U4; then a Playwright-free smoke test via TestClient + one headless Chrome screenshot per screen for the deck.

## 6. Out of scope (UI v1)
Editing flyers, editing findings, bulk auto-approval, multi-tenant setup, mobile-first layout (desktop review workstation is the target; responsive down to tablet).

## 7. Open decisions (need business input)
- Identity provider in the target environment (Google IAP vs. Entra ID) → decides proxy header.
- Role assignment source (IdP groups vs. app config).
- Retention periods for sources vs. findings/decisions.
- Whether approvers sign off inside FlyerCheck or only in the existing workflow (current assumption: existing workflow).
