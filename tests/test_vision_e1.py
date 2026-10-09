"""E1: V-02 claims register and opt-in two-step V-01 (offline, FakeLLM)."""
import threading

from flyercheck.domain.models import Category, Severity, Status
from flyercheck.llm.port import FakeLLM
from flyercheck.vision_checks import run_vision_checks
from flyercheck.vision_checks.prompts import (
    V01_BLIND_PROMPT,
    V01_BLIND_SCHEMA,
    V01_COMPARE_SCHEMA,
    V01_PROMPT,
    V01_SCHEMA,
    V01_TWO_STEP_VERSION,
)
from flyercheck.vision_checks.v01_image_text import TWO_STEP_ENV, _description
from flyercheck.vision_checks.v02_claims import find_claims, run_v02


class RecordingLLM(FakeLLM):
    """Thread-safe fake that records (prompt, n_images, schema) and answers per schema."""

    def __init__(self, compare_by_name: dict[str, dict] | None = None):
        super().__init__()
        self.compare_by_name = compare_by_name or {}
        self.requests: list[tuple[str, int, dict]] = []
        self._lock = threading.Lock()

    def generate_json(self, prompt, images, schema, *, purpose):
        assert purpose == "vision"
        with self._lock:
            self.calls.append((purpose, prompt))
            self.requests.append((prompt, len(images), schema))
        if schema is V01_BLIND_SCHEMA:
            return {"depicted_object": "an aubergine", "depicted_category": "vegetable"}
        if schema is V01_COMPARE_SCHEMA:
            for name, resp in self.compare_by_name.items():
                if f'"{name}"' in prompt:
                    return resp
            return {"advertised_category": "x", "matches": "yes", "confidence": 0.9, "reason": "ok"}
        assert schema is V01_SCHEMA
        return {
            "depicted_object": "the product",
            "depicted_category": "food",
            "advertised_category": "food",
            "matches": "yes",
            "confidence": 0.9,
            "reason": "ok",
        }


# --- V-02 -------------------------------------------------------------------


def test_v02_finds_expected_claims(designer_ctx):
    findings = run_v02(designer_ctx)
    assert findings and all(f.status is Status.NOT_EVALUABLE for f in findings)
    assert all(
        f.check_id == "V-02"
        and f.category is Category.E07_SEMANTIC
        and f.severity is Severity.MEDIUM
        and f.rule_version == "V-02@1.0"
        and f.evidence
        and f.evidence[0].bbox is not None
        for f in findings
    )
    claims = {(f.offer_name, f.observed["claim"]) for f in findings}
    for expected in [
        ("Sonnenäpfel", "AUS DER REGION"),
        ("Nordmeer Lachsfilet", "Aus nachhaltiger Aquakultur"),
        ("Goldkrone Röstkaffee", "100 % Arabica"),
        ("Rispentomaten", "aus den Niederlanden"),
    ]:
        assert expected in claims
    apple = next(f for f in findings if f.observed["claim"] == "AUS DER REGION")
    assert apple.offer_id == "o-1" and apple.id.startswith("V-02:o-1:")
    assert "requires a reference source" in apple.summary and "not verified" in apple.summary
    # document-level claim from text blocks; the shop domain "frischfeld-markt.de" is no claim
    doc = [f for f in findings if f.offer_id is None]
    assert [f.observed["claim"] for f in doc] == ["Regional. Vielfältig. Einfach gut."]
    assert doc[0].id == "V-02:doc:1"
    # ids unique
    assert len({f.id for f in findings}) == len(findings)


def test_v02_dedupes_per_offer_and_ignores_plain_text(designer_ctx):
    o = designer_ctx.offers[0].model_copy(
        update={"badges": ["Bio", "BIO"], "description_lines": ["bio", "Sorte: Rubinette"]}
    )
    designer_ctx.offers = [o]
    designer_ctx.text_blocks = []
    findings = run_v02(designer_ctx)
    assert [f.observed["claim"] for f in findings] == ["Bio"]
    assert findings[0].id == "V-02:o-1:1"
    assert find_claims("Tiefgefroren") == [] and find_claims("Biologie") == []


def test_run_vision_checks_returns_v01_and_v02(designer_ctx, monkeypatch):
    monkeypatch.delenv(TWO_STEP_ENV, raising=False)
    findings = run_vision_checks(designer_ctx, RecordingLLM())
    n = len(designer_ctx.offers)
    assert [f.check_id for f in findings[:n]] == ["V-01"] * n
    assert findings[n:] and all(f.check_id == "V-02" for f in findings[n:])


# --- V-01 default vs. two-step -----------------------------------------------


def test_default_mode_single_call_unchanged_prompt(designer_ctx, monkeypatch):
    monkeypatch.delenv(TWO_STEP_ENV, raising=False)
    llm = RecordingLLM()
    run_vision_checks(designer_ctx, llm)
    assert len(llm.requests) == len(designer_ctx.offers)
    expected = {
        V01_PROMPT.format(product_name=o.product_name or "(unnamed offer)", description=_description(o))
        for o in designer_ctx.offers
    }
    assert {p for p, _, _ in llm.requests} == expected
    assert all(n_img == 1 and schema is V01_SCHEMA for _, n_img, schema in llm.requests)


def test_two_step_mode_two_calls_and_fail_mapping(designer_ctx, monkeypatch):
    monkeypatch.setenv(TWO_STEP_ENV, "1")
    no = {"advertised_category": "chocolate", "matches": "no", "confidence": 0.95, "reason": "veg"}
    llm = RecordingLLM({"Schola Schokolade": no})
    findings = [f for f in run_vision_checks(designer_ctx, llm) if f.check_id == "V-01"]
    n = len(designer_ctx.offers)
    assert len(llm.requests) == 2 * n
    blind = [r for r in llm.requests if r[2] is V01_BLIND_SCHEMA]
    compare = [r for r in llm.requests if r[2] is V01_COMPARE_SCHEMA]
    assert len(blind) == n and len(compare) == n
    # step 1 is blind (image, no product text); step 2 is text-only
    assert all(p == V01_BLIND_PROMPT and k == 1 for p, k, _ in blind)
    assert all(k == 0 and "an aubergine" in p for p, k, _ in compare)
    by = {f.offer_name: f for f in findings}
    schola = by["Schola Schokolade"]
    assert schola.status is Status.FAIL
    assert schola.observed["depicted"] == "an aubergine"
    assert schola.expected["advertised_category"] == "chocolate"
    assert schola.rule_version == V01_TWO_STEP_VERSION
    assert all(f.status is Status.PASS for name, f in by.items() if name != "Schola Schokolade")
