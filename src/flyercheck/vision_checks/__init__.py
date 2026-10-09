"""AI-assisted visual checks (V-01 image<->text) and deterministic claims register (V-02)."""
from flyercheck.domain.models import DocumentContext, Finding
from flyercheck.llm.port import LLMPort
from flyercheck.vision_checks.v01_image_text import run_v01
from flyercheck.vision_checks.v02_claims import run_v02


def run_vision_checks(ctx: DocumentContext, llm: LLMPort) -> list[Finding]:
    return run_v01(ctx, llm) + run_v02(ctx)
