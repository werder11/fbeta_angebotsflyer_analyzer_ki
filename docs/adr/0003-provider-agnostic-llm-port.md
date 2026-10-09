# ADR-0003: Provider-agnostic LLM port; default Gemini on Vertex AI (EU)

## Status
Accepted (2026-10-09). PoC uses the **Gemini Developer API** (`GEMINI_API_KEY`); production moves to Vertex AI EU with the same adapter.

## Context
The brief allows LLMs on Azure **or** Google Cloud. The flyer data is confidential (unpublished prices). Models are deprecated on 6–12-month cycles.

## Decision Drivers
Visual grounding (bbox quality) · structured-output support · EU data residency and no training on customer data · cost per page · client's existing cloud

## Considered Options
### A. Gemini (2.5 Pro/Flash or successor) on Vertex AI, europe-west3/-west4
+ native object detection with boxes, `response_schema`, strong document vision, low cost (Flash) · − bbox format 0–1000 needs conversion
### B. GPT-4.1/GPT-5-class on Azure OpenAI (Sweden Central / Germany West Central)
+ strict `json_schema` mode; many German retailers already run on Azure · − less reliable pixel grounding
### C. Hard-wire one vendor
+ less code · − lock-in; violates P-04

## Decision
A `LLMPort` protocol (`generate(prompt, images, schema, *, model, temperature=0) -> dict`) with two adapters: `GeminiVertexAdapter` (default) and `AzureOpenAIAdapter`. Model IDs live in config. Use the cheap model for vision checks and the strong model for extraction.

## Spike evidence (2026-10-09, Designer.pdf)
| Model | Result |
|---|---|
| gemini-3.5-flash | ✅ 16 s, 9/9 offers exact, boxes correct |
| gemini-3.8-flash | ❌ 503 overloaded |
| gemini-3.1-pro-preview | ❌ 429 no quota |
| gemini-2.5-pro | ❌ 404 retired |

→ Default chain `gemini-3.5-flash → gemini-3.8-flash → gemini-flash-latest`, retries with backoff on 429/503, chain env-overridable. Record/replay is mandatory (ADR-0008).

## Consequences
**Positive:** vendor choice is a config flag, and the two can be benchmarked on the golden set (ADR-0008).
**Negative:** we code to the lowest common feature set.
**Risks:** the model behind an ID changes silently → pin versions, and a regression gate runs on every model change.

## Links
[components: llm/](../architecture/components.md) · [deployment](../operations/deployment.md)
