"""V-01 image<->text check (offline, FakeLLM)."""
import io
import threading

from PIL import Image

from flyercheck.domain.models import BBox, Category, Severity, Status
from flyercheck.llm.port import FakeLLM, LLMError
from flyercheck.vision_checks import run_vision_checks
from flyercheck.vision_checks.prompts import V01_SCHEMA, V01_VERSION
from flyercheck.vision_checks.v01_image_text import crop_png


def _resp(matches: str, conf: float, depicted: str = "the product") -> dict:
    return {
        "depicted_object": depicted,
        "depicted_category": "food",
        "advertised_category": "milk chocolate",
        "matches": matches,
        "confidence": conf,
        "reason": "test",
    }


class PromptFakeLLM(FakeLLM):
    """Thread-safe fake answering by product name found in the prompt."""

    def __init__(self, by_name: dict[str, dict | Exception], default: dict | None = None):
        super().__init__()
        self.by_name = by_name
        self.default = default or _resp("yes", 0.9)
        self.images: list[bytes] = []
        self._lock = threading.Lock()

    def generate_json(self, prompt, images, schema, *, purpose):
        assert purpose == "vision"
        assert schema is V01_SCHEMA
        with self._lock:
            self.calls.append((purpose, prompt))
            self.images.extend(images)
        for name, resp in self.by_name.items():
            if f'"{name}"' in prompt:
                if isinstance(resp, Exception):
                    raise resp
                return resp
        return self.default


def _v01(findings):
    return [f for f in findings if f.check_id == "V-01"]


def _by_offer(findings):
    return {f.offer_name: f for f in _v01(findings)}


def test_schola_fail_others_pass(designer_ctx):
    llm = PromptFakeLLM({"Schola Schokolade": _resp("no", 0.95, "an aubergine")})
    findings = _v01(run_vision_checks(designer_ctx, llm))
    assert [f.offer_id for f in findings] == [o.id for o in designer_ctx.offers]
    assert len(llm.calls) == len(designer_ctx.offers)
    by = _by_offer(findings)
    schola = by["Schola Schokolade"]
    assert schola.status is Status.FAIL
    assert schola.severity is Severity.CRITICAL
    assert schola.category is Category.E01_PRODUCT_IMAGE
    assert schola.id == f"V-01:{schola.offer_id}"
    assert schola.check_id == "V-01"
    assert schola.observed["depicted"] == "an aubergine"
    assert schola.expected["advertised"] == "Schola Schokolade"
    assert "an aubergine" in schola.summary and "Schola Schokolade" in schola.summary
    assert schola.rule_version == V01_VERSION
    assert schola.model_version == "fake"
    assert schola.evidence[0].source == "model" and schola.evidence[0].bbox is not None
    assert schola.confidence == 0.95
    others = [f for f in findings if f.offer_name != "Schola Schokolade"]
    assert others and all(f.status is Status.PASS for f in others)


def test_unclear_and_low_confidence_need_review(designer_ctx):
    llm = PromptFakeLLM(
        {"Rispentomaten": _resp("unclear", 0.9), "Schola Schokolade": _resp("no", 0.5)}
    )
    by = _by_offer(run_vision_checks(designer_ctx, llm))
    assert by["Rispentomaten"].status is Status.NEEDS_REVIEW
    assert by["Schola Schokolade"].status is Status.NEEDS_REVIEW


def test_llm_error_becomes_error_finding(designer_ctx):
    llm = PromptFakeLLM({"Sonnenäpfel": LLMError("boom")})
    by = _by_offer(run_vision_checks(designer_ctx, llm))
    assert by["Sonnenäpfel"].status is Status.ERROR
    assert "boom" in by["Sonnenäpfel"].summary
    assert by["Rispentomaten"].status is Status.PASS


def test_no_bbox_not_evaluable(designer_ctx):
    designer_ctx.offers[0] = designer_ctx.offers[0].model_copy(update={"bbox": None, "image_bbox": None})
    llm = PromptFakeLLM({})
    findings = _v01(run_vision_checks(designer_ctx, llm))
    assert findings[0].status is Status.NOT_EVALUABLE
    assert len(llm.calls) == len(designer_ctx.offers) - 1


def test_crop_dimensions(designer_ctx):
    page = designer_ctx.pages[0]
    for offer in designer_ctx.offers:
        bbox = offer.image_bbox or offer.bbox
        img = Image.open(io.BytesIO(crop_png(page.path, bbox)))
        assert 0 < img.width <= 1024 and 0 < img.height <= 1536
    # edge bbox is clamped to the image
    img = Image.open(io.BytesIO(crop_png(page.path, BBox(x0=0, y0=0, x1=1, y1=1))))
    assert (img.width, img.height) == (1024, 1536)
