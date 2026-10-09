# Deployment (target)

← [operations](README.md) · ADR: [0007](../adr/0007-modular-monolith-serverless.md), [0003](../adr/0003-provider-agnostic-llm-port.md)

| Concern | GCP (default) | Azure (equivalent) |
|---|---|---|
| Compute | Cloud Run (API) + Cloud Run Jobs (worker) | Container Apps + Container Apps Jobs |
| Queue / trigger | Pub/Sub, GCS upload trigger (Eventarc) | Service Bus, Blob trigger (Event Grid) |
| LLM | Vertex AI Gemini, `europe-west3` | Azure OpenAI, Germany West Central / Sweden Central |
| OCR cross-check | Document AI OCR | Document Intelligence Read |
| Storage | GCS (source, renders, evidence) | Blob Storage |
| DB | Cloud SQL Postgres (runs, findings, decisions, audit) | Azure DB for PostgreSQL |
| Secrets / IAM | Secret Manager, Workload Identity, no keys | Key Vault, Managed Identity |
| Observability | Cloud Logging/Trace + OpenTelemetry; Langfuse for LLM traces | App Insights + Langfuse |
| IaC / CI | Terraform; GitHub Actions: lint → unit → replay → eval gate → deploy | same |

**Security & privacy:** EU region only; enterprise terms (no training on prompts); VPC-SC / private endpoints; source flyers retained per policy (e.g. 90 days), findings and decisions retained for audit; role-based access (reviewer, admin).

**Cost (estimate, to be validated):** ~2 LLM calls per page for extraction plus 1 small call per offer for V-01 → order of a few cents per page with Flash-class models, < €0.50 per flyer with Pro-class extraction. Measured per run and shown in the report footer.

**Integration:** trigger from the DTP export folder or campaign tool (webhook). Results go back as a PDF/HTML report plus a ticket/comment in the existing approval workflow.
