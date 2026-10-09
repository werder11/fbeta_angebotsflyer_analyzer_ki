# ADR-0002: Multimodal-LLM extraction with bounding boxes; OCR cross-check in production

## Status
Accepted

## Context
Flyers are image-heavy PDFs with free-form layouts. Offer grouping (which price belongs to which image?) is the hardest step. The sample PDF has no reliable text layer.

## Decision Drivers
Layout robustness · field-level bboxes for evidence · build time (30 min) · cost per page

## Considered Options
### A. OCR/layout service (Document AI, Azure Document Intelligence) + custom grouping heuristics
+ precise word boxes, deterministic · − grouping offers takes significant custom code; weak on creative layouts
### B. Multimodal LLM with structured output (Gemini 2.x/Vertex, GPT-4.1-class/Azure) returning offers + bboxes
+ groups semantically, one call per page, quick to build · − bboxes approximate, numbers can be misread
### C. A + B consensus
+ highest accuracy · − double cost and complexity

## Decision
**PoC: B.** **Production: C.** The OCR word layer validates every numeric field the VLM returns (string match inside its bbox). Disagreement → `needs_review`.

## Consequences
**Positive:** a working pipeline in minutes; generic across layouts.
**Negative:** a PoC price misread can produce false findings. The prompt therefore demands verbatim transcription, and the evidence crop lets the reviewer verify within seconds.
**Risks:** bbox drift on dense pages → tile pages into a 2×2 grid at high resolution if needed.

## Links
[pipeline §2](../design/pipeline.md#2-extract) · [ADR-0003](0003-provider-agnostic-llm-port.md) · [risks](../operations/risks.md)
