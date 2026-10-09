"""Extract offers via multimodal LLM. Owned by track T2."""
from flyercheck.domain.models import Document, DocumentContext, PageImage
from flyercheck.llm.port import LLMPort

PROMPT_VERSION = "extract-v1"


def extract_document(doc: Document, pages: list[PageImage], llm: LLMPort) -> DocumentContext:
    raise NotImplementedError
