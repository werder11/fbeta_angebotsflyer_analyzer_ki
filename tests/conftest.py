import json
import pathlib

import pytest

from flyercheck.domain.models import DocumentContext, GoldenSet
from flyercheck.llm.port import FakeLLM

FIX = pathlib.Path(__file__).parent / "fixtures"
ROOT = pathlib.Path(__file__).parent.parent


@pytest.fixture
def designer_ctx() -> DocumentContext:
    return DocumentContext.model_validate_json((FIX / "designer_context.json").read_text())


@pytest.fixture
def golden() -> GoldenSet:
    return GoldenSet.model_validate_json((ROOT / "data/golden/designer.json").read_text())


@pytest.fixture
def page_png() -> bytes:
    return (FIX / "page1.png").read_bytes()


@pytest.fixture
def extract_response() -> dict:
    return json.loads((FIX / "llm_extract_designer.json").read_text())


@pytest.fixture
def sample_pdf() -> pathlib.Path:
    return ROOT / "data/samples/Designer.pdf"


@pytest.fixture
def fake_llm() -> type[FakeLLM]:
    return FakeLLM
