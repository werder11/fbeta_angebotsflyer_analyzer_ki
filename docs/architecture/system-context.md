# System Context & Containers

← [architecture](README.md) · [docs index](../README.md)

## C4 Level 1 — System context

```mermaid
flowchart LR
    DTP["Flyer production<br/>(DTP / agency)"] -->|flyer PDF + campaign metadata| FC
    REV["QA reviewer"] <-->|findings, decisions| FC
    FC["FlyerCheck<br/>AI consistency validation"]
    FC -->|multimodal prompts| LLM["Cloud LLM<br/>Gemini (Vertex AI) / Azure OpenAI"]
    FC -.->|lookup (target)| PIM["PIM / price & campaign DB"]
    FC -.->|optional OCR cross-check| OCR["Document AI / Azure Document Intelligence"]
    FC -->|approved report| PUB["Existing publication approval"]
```

## C4 Level 2 — Containers

### PoC (this sprint)
One Python package with a CLI. Everything runs in-process; output is files.

```mermaid
flowchart TB
    CLI["CLI: flyercheck run"] --> PIPE["Pipeline (modular monolith)"]
    PIPE --> FS[("Local FS<br/>out/run-id/: pages.png, offers.json,<br/>findings.json, report.html")]
    PIPE --> REC[("data/recordings/<br/>LLM replay cache")]
    PIPE -->|live mode| LLM["Cloud LLM"]
```

### Target (production, same code)
```mermaid
flowchart TB
    UP["Upload / DTP hook"] --> API["FlyerCheck API<br/>(Cloud Run / Azure Container Apps)"]
    API --> BUS["Job queue<br/>(Pub/Sub / Service Bus)"]
    BUS --> WRK["Validation worker<br/>(same pipeline package)"]
    WRK --> BLOB[("Object storage<br/>GCS / Blob: source, renders, evidence")]
    WRK --> DB[("Postgres<br/>runs, findings, decisions, audit")]
    WRK --> LLM["LLM endpoint (EU region,<br/>no training on data)"]
    WRK -.-> PIM["PIM / price adapter"]
    UI["Review UI"] --> API
    OBS["Monitoring: traces, cost,<br/>quality dashboards"] --- WRK
```
Rationale: [ADR-0007](../adr/0007-modular-monolith-serverless.md). Deployment details: [operations/deployment.md](../operations/deployment.md).
