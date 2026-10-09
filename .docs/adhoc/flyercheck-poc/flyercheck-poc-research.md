# FlyerCheck PoC — Research & Working Notes

← [plan](flyercheck-poc-plan.md)

## Initial Understanding
The case study asks for an AI solution approach for checking flyer consistency (Azure/GCP LLMs allowed), presented in about 15 minutes. The user wants a working PoC in a 30-minute coding session, built as fast as possible with multiple agents in parallel git worktrees: finalize first, enhance later.

## Research Process
| Step | Finding |
|---|---|
| Repo scan | Greenfield: `docs/` (architecture layer done earlier), `CLAUDE.md`, `.env` with `GEMINI_API_KEY`, `data/samples/Designer.pdf`. **Not a git repo.** |
| PDF inspection (PyMuPDF) | 1 page, 768×1152 pt, **0 text chars**, one embedded 1024×1536 RGB image, producer jsPDF 4.2.1, creationDate 2026-10-07 |
| Visual check of the embedded raster | All small print legible at native resolution ("(1 kg = 5,59)", "zzgl. 1,50 Pfand", "Rezept auf Seite 6.") |
| `models.list()` with the key | Gemini 2.5/3/3.1/3.5/3.6/3.7/3.8 families listed |
| Live extraction spike (same prompt, 4 models in parallel) | `gemini-3.5-flash`: 16.4 s, 1280 in / 1956 out / 2406 thinking tokens, **9/9 offers correct on every raw field**, boxes consistent with the 3×3 grid, image_description for chocolate = "An eggplant…". `gemini-3.8-flash`: 503 overloaded. `gemini-3.1-pro-preview`: 429 quota. `gemini-2.5-pro`: 404 retired. |
| Spike miss | `page_references: []`: the model ignored "Rezept auf Seite 6" when asked for it in a generic field |
| Arithmetic (python) | Pizza 1.69/0.32 = 5.28125 vs printed 5.59 (≈ 1.79/0.32); discounts: tomatoes 25.13, yoghurt 33.90, pizza 41.52, chocolate 23.26; weekday: Mo 07.10 / Sa 12.10 holds only in 2024 and 2030; in 2026 = Wed/Mon |

## Questions Asked & Answers
| Q | A |
|---|---|
| Which provider? | **Gemini**, key in `.env` as `GEMINI_API_KEY` (Developer API) |
| Where is the flyer? | `data/samples/Designer.pdf`. Extract the image from it ourselves |
| Strategy | Fastest path: finalize first, enhance later, parallel agents in worktrees |

## Key Discoveries
1. **Use the embedded raster, not a render**: native 1024×1536; a 200-dpi render just upscales it to 2134×3200 (more tokens, no information).
2. **Model availability is volatile** → fallback chain + retries + record/replay are requirements, not nice-to-haves.
3. **Thinking tokens dominate output** (2.4k thinking vs 2k answer) → tune `thinking_level` later (E6).
4. **Free-form "references" fields get skipped** → ask for *all* non-offer text blocks and find references by regex (deterministic, P-01).
5. **PDF metadata provides a campaign-year hint (2026)** → turns R-05 from `needs_review` into a defensible `fail`.
6. The extraction's blind `image_description` already exposes the aubergine, giving a cheap redundancy signal for V-01.

## Design Decisions
| Decision | Options | Chosen | Why |
|---|---|---|---|
| Extraction model | 3.8-flash / 3.1-pro / 3.5-flash | **3.5-flash**, chain → 3.8-flash → flash-latest | Only one verified working; exact output |
| Gemini API surface | Vertex AI / Developer API | **Developer API** for the PoC; Vertex EU for prod | The key we have; ADR-0003 updated |
| V-01 calls | two-step / one-step blind-first | **one call**, blind fields first | Halves latency; the two-step version moves to E1 |
| Parallelism | 3 bigger tracks / 5 tracks / 7 tracks | **5 tracks + integrator** | Disjoint ownership; each fits ~13 min; more tracks → integration overhead |
| Unblocking downstream tracks | wait for extract / fixtures | **Hand-normalized fixture from the spike** | T3–T5 independent of T2 |
| Module name for eval | `eval` / `evaluation` | `evaluation` | Avoids shadowing the builtin |
| Recording key | model+prompt / purpose+prompt | **purpose**+prompt+images+schema | The fallback model must not invalidate recordings |

## Open Questions
None blocking. Assumptions recorded in [docs/vision](../../../docs/vision/README.md) (A-01…A-05).
