"""Azure OpenAI adapter (ADR-0003 parity). Owned by Phase 3 track E4."""
from flyercheck.llm.port import LLMError  # noqa: F401


class AzureOpenAILLM:
    model_id = "azure-openai"

    def generate_json(self, prompt: str, images: list[bytes], schema: dict, *, purpose: str) -> dict:
        raise NotImplementedError
