"""AI-assisted visual checks (V-01 image<->text). Owned by track T4."""
from flyercheck.domain.models import DocumentContext, Finding
from flyercheck.llm.port import LLMPort


def run_vision_checks(ctx: DocumentContext, llm: LLMPort) -> list[Finding]:
    raise NotImplementedError
