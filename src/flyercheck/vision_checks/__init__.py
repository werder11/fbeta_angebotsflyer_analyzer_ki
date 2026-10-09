"""AI-assisted visual checks (V-01 image<->text). Owned by track T4."""
from flyercheck.domain.models import DocumentContext, Finding
from flyercheck.llm.port import LLMPort
from flyercheck.vision_checks.v01_image_text import run_v01


def run_vision_checks(ctx: DocumentContext, llm: LLMPort) -> list[Finding]:
    return run_v01(ctx, llm)
