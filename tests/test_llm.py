"""T1: LLM adapter + record/replay. No network."""
from __future__ import annotations

import json
import threading
from types import SimpleNamespace

import pytest
from google.genai import errors

from flyercheck.llm import gemini as gemini_mod
from flyercheck.llm.factory import make_llm
from flyercheck.llm.gemini import GeminiLLM
from flyercheck.llm.port import FakeLLM, LLMError, request_key
from flyercheck.llm.recording import RecordingLLM

SCHEMA = {"type": "object", "properties": {"a": {"type": "integer"}}}
IMG = b"\x89PNG fake"


def api_error(code: int, status: str = "UNAVAILABLE", message: str = "overloaded") -> errors.APIError:
    return errors.APIError(code, {"error": {"code": code, "status": status, "message": message}})


def resp(text: str, prompt_tokens=10, out_tokens=5, thoughts=None):
    meta = SimpleNamespace(
        prompt_token_count=prompt_tokens, candidates_token_count=out_tokens, thoughts_token_count=thoughts
    )
    return SimpleNamespace(text=text, usage_metadata=meta)


class FakeModels:
    """Scripted client.models: script maps model -> list of responses/exceptions consumed in order."""

    def __init__(self, script: dict[str, list]):
        self.script = script
        self.calls: list[tuple[str, object]] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append((model, config))
        item = self.script[model].pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def make_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("FLYERCHECK_MODELS_EXTRACT", "m1,m2")
    sleeps: list[float] = []

    def _make(script):
        llm = GeminiLLM(sleep=sleeps.append)
        llm.client = SimpleNamespace(models=FakeModels(script))
        return llm, sleeps

    return _make


# ---- RecordingLLM ------------------------------------------------------------------------------


def test_record_then_replay_roundtrip(tmp_path):
    inner = FakeLLM({"extract": {"a": 1, "text": "Ä"}})
    rec = RecordingLLM(inner, "record", str(tmp_path))
    out = rec.generate_json("p", [IMG], SCHEMA, purpose="extract")
    assert out == {"a": 1, "text": "Ä"}
    key = request_key("extract", "p", [IMG], SCHEMA)
    data = json.loads((tmp_path / f"{key}.json").read_text(encoding="utf-8"))
    assert data["purpose"] == "extract" and data["model_id"] == "fake" and data["response"] == out
    assert {"usage", "recorded_at"} <= data.keys()
    assert "Ä" in (tmp_path / f"{key}.json").read_text(encoding="utf-8")  # ensure_ascii=False

    replay = RecordingLLM(None, "replay", str(tmp_path))
    assert replay.generate_json("p", [IMG], SCHEMA, purpose="extract") == out
    assert replay.model_id == "fake"
    assert replay.usage["calls"] == 1


def test_replay_miss_raises_with_key_and_hint(tmp_path):
    replay = RecordingLLM(None, "replay", str(tmp_path))
    with pytest.raises(LLMError) as ei:
        replay.generate_json("p", [], SCHEMA, purpose="vision")
    msg = str(ei.value)
    assert request_key("vision", "p", [], SCHEMA) in msg and "--mode record" in msg


def test_key_independent_of_serving_model(tmp_path):
    a, b = FakeLLM({"extract": {"a": 1}}), FakeLLM({"extract": {"a": 1}})
    b.model_id = "other-model"
    RecordingLLM(a, "record", str(tmp_path)).generate_json("p", [IMG], SCHEMA, purpose="extract")
    RecordingLLM(b, "record", str(tmp_path)).generate_json("p", [IMG], SCHEMA, purpose="extract")
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1  # same key regardless of model
    assert json.loads(files[0].read_text())["model_id"] == "other-model"


def test_live_mode_does_not_write(tmp_path):
    rec = RecordingLLM(FakeLLM({"extract": {"a": 2}}), "live", str(tmp_path))
    assert rec.generate_json("p", [], SCHEMA, purpose="extract") == {"a": 2}
    assert not list(tmp_path.glob("*.json"))
    assert rec.usage["calls"] == 1 and rec.model_id == "fake"


def test_recording_usage_sums_inner_usage_and_is_thread_safe(tmp_path):
    class UsageFake(FakeLLM):
        def __init__(self):
            super().__init__({"extract": {"a": 1}})
            self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0}

        def generate_json(self, prompt, images, schema, *, purpose):
            self.usage["calls"] += 1
            self.usage["input_tokens"] += 7
            return super().generate_json(prompt, images, schema, purpose=purpose)

    rec = RecordingLLM(UsageFake(), "live", str(tmp_path))
    rec.generate_json("p", [], SCHEMA, purpose="extract")
    rec.generate_json("q", [], SCHEMA, purpose="extract")
    assert rec.usage["calls"] == 2 and rec.usage["input_tokens"] == 14

    rec2 = RecordingLLM(FakeLLM({"extract": {"a": 1}}), "live", str(tmp_path))
    threads = [
        threading.Thread(target=rec2.generate_json, args=("p", [], SCHEMA), kwargs={"purpose": "extract"})
        for _ in range(20)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert rec2.usage["calls"] == 20


def test_make_llm_modes(tmp_path):
    assert isinstance(make_llm("replay", str(tmp_path)), RecordingLLM)
    with pytest.raises(ValueError):
        make_llm("bogus", str(tmp_path))


# ---- GeminiLLM ---------------------------------------------------------------------------------


def test_gemini_falls_back_to_next_model_on_503(make_gemini):
    llm, sleeps = make_gemini({"m1": [api_error(503)] * 3, "m2": [resp('{"a": 1}')]})
    assert llm.generate_json("p", [IMG], SCHEMA, purpose="extract") == {"a": 1}
    assert llm.model_id == "m2"
    assert sleeps == [2, 4]  # backoff injected, never actually waited
    assert [m for m, _ in llm.client.models.calls] == ["m1", "m1", "m1", "m2"]


def test_gemini_404_skips_model_without_retry(make_gemini):
    llm, sleeps = make_gemini({"m1": [api_error(404, "NOT_FOUND", "retired")], "m2": [resp('{"a": 2}')]})
    assert llm.generate_json("p", [], SCHEMA, purpose="extract") == {"a": 2}
    assert llm.model_id == "m2" and sleeps == []


def test_gemini_transient_then_success_same_model(make_gemini):
    llm, sleeps = make_gemini({"m1": [api_error(429, "RESOURCE_EXHAUSTED"), resp('{"a": 3}')], "m2": []})
    assert llm.generate_json("p", [], SCHEMA, purpose="extract") == {"a": 3}
    assert llm.model_id == "m1" and sleeps == [2]


def test_gemini_all_models_fail_raises(make_gemini):
    llm, _ = make_gemini({"m1": [api_error(503)] * 3, "m2": [api_error(404, "NOT_FOUND")]})
    with pytest.raises(LLMError):
        llm.generate_json("p", [], SCHEMA, purpose="extract")


def test_gemini_invalid_json_then_valid_on_retry(make_gemini):
    llm, _ = make_gemini({"m1": [resp("not json"), resp('{"a": 4}')], "m2": []})
    assert llm.generate_json("p", [], SCHEMA, purpose="extract") == {"a": 4}
    assert llm.usage["calls"] == 2


def test_gemini_invalid_json_twice_raises(make_gemini):
    llm, _ = make_gemini({"m1": [resp("nope"), resp("still nope")], "m2": []})
    with pytest.raises(LLMError):
        llm.generate_json("p", [], SCHEMA, purpose="extract")


def test_gemini_schema_rejection_falls_back_to_mime_only(make_gemini):
    rejected = api_error(400, "INVALID_ARGUMENT", "Invalid response_json_schema")
    llm, _ = make_gemini({"m1": [rejected, resp('{"a": 5}')], "m2": []})
    assert llm.generate_json("p", [], SCHEMA, purpose="extract") == {"a": 5}
    configs = [c for _, c in llm.client.models.calls]
    assert configs[0].response_json_schema == SCHEMA
    assert configs[1].response_json_schema is None
    assert configs[1].response_mime_type == "application/json"


def test_gemini_usage_accumulation(make_gemini):
    llm, _ = make_gemini(
        {"m1": [resp('{"a": 1}', 10, 5, 3), resp('{"a": 1}', 20, None, None)], "m2": []}
    )
    llm.generate_json("p", [], SCHEMA, purpose="extract")
    llm.generate_json("q", [], SCHEMA, purpose="extract")
    assert llm.usage == {"calls": 2, "input_tokens": 30, "output_tokens": 5, "thinking_tokens": 3}


def test_model_chain_defaults_and_env(monkeypatch):
    monkeypatch.delenv("FLYERCHECK_MODELS_VISION", raising=False)
    assert gemini_mod.model_chain("vision")[0] == "gemini-3.5-flash"
    monkeypatch.setenv("FLYERCHECK_MODELS_VISION", " a , b ")
    assert gemini_mod.model_chain("vision") == ["a", "b"]
