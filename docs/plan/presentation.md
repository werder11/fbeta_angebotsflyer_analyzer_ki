# Presentation — 10 minutes (+ Q&A)

← [plan](implementation-plan.md) · [docs index](../README.md)

Structured around the three questions in the brief.

| Min | Slide | Message | Source |
|---|---|---|---|
| 0:00 | 1. Problem & assumptions | Weekly flyers, manual review, confidential prices; assumptions A-01…A-05 | [vision](../vision/README.md) |
| 1:00 | 2. **Q1 Target architecture** | Hybrid: the LLM *perceives*, code *verifies*, the human *decides*. Show the pipeline diagram | [ADR-0001](../adr/0001-hybrid-validation-architecture.md), [components](../architecture/components.md) |
| 2:30 | 3. Cloud & model choice | Provider port; Gemini on Vertex EU (grounding) vs. Azure OpenAI; same code | [ADR-0003](../adr/0003-provider-agnostic-llm-port.md), [system-context](../architecture/system-context.md) |
| 3:30 | 4. **Live demo** | `flyercheck run Designer.pdf` → report: aubergine/chocolate, pizza unit price 5.59 vs. 5.28, −42 % overstated, missing Grundpreis ×3, Mo/Sa vs. year, "Seite 6" | [sample analysis](../domain/sample-flyer-analysis.md) |
| 6:00 | 5. **Q2 Implementation, deployment, documentation** | Rules catalog, contract + ADRs, golden-set gate, Cloud Run / Container Apps, docs-as-code | [rules](../design/rules-catalog.md), [deployment](../operations/deployment.md), [eval](../operations/evaluation-and-monitoring.md) |
| 8:00 | 6. **Q3 Risks & limits** | Misreads, grouping, false safety, no master data, data privacy, drift → mitigations | [risks](../operations/risks.md) |
| 9:00 | 7. Roadmap | PoC → shadow pilot (baseline) → assisted production → PIM integration | [vision](../vision/README.md#roadmap) |

**Talking points:** "No findings ≠ defect-free" · "Every finding has evidence you can verify in 5 seconds" · "How the work was built: contract first, 5 agents in parallel worktrees"
