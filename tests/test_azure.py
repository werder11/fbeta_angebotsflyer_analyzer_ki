"""Azure OpenAI adapter tests — fully offline, mocked client (no credentials, no network)."""
from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import openai
import pytest

from flyercheck.llm import azure as azure_mod
from flyercheck.llm.azure import AzureOpenAILLM
from flyercheck.llm.factory import make_llm
from flyercheck.llm.port import LLMError
from flyercheck.llm.recording import RecordingLLM

try:  # the openai SDK's HTTP layer (httpx2 in recent versions, httpx before)
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}}


def _err(cls: type[openai.APIStatusError], status: int, msg: str = "err") -> openai.APIStatusError:
    resp = httpx.Response(status, request=httpx.Request("POST", "https://example.invalid/"))
    return cls(msg, response=resp, body=None)


def _resp(content: str, prompt_tokens: int = 10, completion_tokens: int = 5, reasoning: int | None = None):
    details = SimpleNamespace(reasoning_tokens=reasoning) if reasoning is not None else None
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, completion_tokens_details=details
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))], usage=usage)


class StubClient:
    """Mimics `client.chat.completions.create`; returns/raises queued outcomes and records kwargs."""

    def __init__(self, outcomes: list):
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("AZURE_OPENAI_DEPLOYMENTS_EXTRACT", "AZURE_OPENAI_DEPLOYMENTS_VISION"):
        monkeypatch.delenv(var, raising=False)


def _llm(outcomes: list) -> tuple[AzureOpenAILLM, StubClient, list[float]]:
    client = StubClient(outcomes)
    sleeps: list[float] = []
    return AzureOpenAILLM(client=client, sleep=sleeps.append), client, sleeps


def test_success_parses_json_and_tracks_model_and_usage():
    llm, client, _ = _llm([_resp('{"ok": true}', 12, 7, reasoning=3)])
    assert llm.generate_json("p", [], SCHEMA, purpose="extract") == {"ok": True}
    assert llm.model_id == "gpt-4.1"
    assert llm.usage == {"calls": 1, "input_tokens": 12, "output_tokens": 7, "thinking_tokens": 3}
    call = client.calls[0]
    assert call["model"] == "gpt-4.1"
    assert call["temperature"] == 0
    assert call["messages"][0]["role"] == "system"
    assert call["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "result", "schema": SCHEMA, "strict": False},
    }


def test_vision_purpose_uses_mini_and_no_reasoning_tokens_is_zero():
    llm, client, _ = _llm([_resp('{"ok": false}')])
    llm.generate_json("p", [], SCHEMA, purpose="vision")
    assert client.calls[0]["model"] == "gpt-4.1-mini"
    assert llm.usage["thinking_tokens"] == 0


def test_images_encoded_as_data_uris():
    llm, client, _ = _llm([_resp('{"ok": true}')])
    llm.generate_json("prompt", [b"img1", b"img2"], SCHEMA, purpose="extract")
    content = client.calls[0]["messages"][1]["content"]
    assert content[0] == {"type": "text", "text": "prompt"}
    for part, raw in zip(content[1:], (b"img1", b"img2"), strict=True):
        assert part["type"] == "image_url"
        assert part["image_url"]["detail"] == "high"
        assert part["image_url"]["url"] == "data:image/png;base64," + base64.b64encode(raw).decode()


def test_retry_on_429_then_success():
    llm, client, sleeps = _llm([_err(openai.RateLimitError, 429), _resp('{"ok": true}')])
    assert llm.generate_json("p", [], SCHEMA, purpose="extract") == {"ok": True}
    assert sleeps == [2]
    assert len(client.calls) == 2


def test_retry_exhaustion_moves_to_next_deployment(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENTS_EXTRACT", "a, b")
    busy = [_err(openai.InternalServerError, 503) for _ in range(3)]
    llm, client, sleeps = _llm([*busy, _resp('{"ok": true}')])
    llm.generate_json("p", [], SCHEMA, purpose="extract")
    assert [c["model"] for c in client.calls] == ["a", "a", "a", "b"]
    assert sleeps == [2, 4]
    assert llm.model_id == "b"


def test_deployment_fallback_on_404(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENTS_EXTRACT", "missing,gpt-4o")
    llm, client, sleeps = _llm([_err(openai.NotFoundError, 404, "DeploymentNotFound"), _resp('{"ok": true}')])
    assert llm.generate_json("p", [], SCHEMA, purpose="extract") == {"ok": True}
    assert [c["model"] for c in client.calls] == ["missing", "gpt-4o"]
    assert sleeps == []
    assert llm.model_id == "gpt-4o"


def test_all_deployments_fail_raises():
    llm, _, _ = _llm([_err(openai.NotFoundError, 404)])
    with pytest.raises(LLMError, match="all deployments failed"):
        llm.generate_json("p", [], SCHEMA, purpose="extract")


def test_schema_rejection_falls_back_to_json_object():
    rejection = _err(openai.BadRequestError, 400, "Invalid parameter: 'response_format' json_schema not supported")
    llm, client, _ = _llm([rejection, _resp('{"ok": true}'), _resp('{"ok": true}')])
    assert llm.generate_json("prompt", [], SCHEMA, purpose="extract") == {"ok": True}
    retry = client.calls[1]
    assert retry["response_format"] == {"type": "json_object"}
    text = retry["messages"][1]["content"][0]["text"]
    assert text.startswith("prompt") and json.dumps(SCHEMA) in text
    # sticky: subsequent calls skip json_schema
    llm.generate_json("prompt", [], SCHEMA, purpose="extract")
    assert client.calls[2]["response_format"] == {"type": "json_object"}


def test_invalid_json_retries_once_then_raises():
    llm, client, _ = _llm([_resp("not json"), _resp("[1, 2]")])
    with pytest.raises(LLMError, match="invalid JSON twice"):
        llm.generate_json("p", [], SCHEMA, purpose="extract")
    assert len(client.calls) == 2
    assert client.calls[1]["messages"][1]["content"][0]["text"].endswith("Return ONLY valid JSON.")


def test_invalid_json_then_valid_succeeds():
    llm, _, _ = _llm([_resp(""), _resp('{"ok": true}')])
    assert llm.generate_json("p", [], SCHEMA, purpose="extract") == {"ok": True}
    assert llm.usage["calls"] == 2


@pytest.mark.parametrize("missing", ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"])
def test_missing_env_raises(monkeypatch, missing):
    monkeypatch.setattr(azure_mod, "load_dotenv", lambda: None)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.invalid/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "dummy")
    monkeypatch.delenv(missing)
    with pytest.raises(LLMError, match="AZURE_OPENAI"):
        AzureOpenAILLM()


def test_constructs_azure_client_from_env(monkeypatch):
    monkeypatch.setattr(azure_mod, "load_dotenv", lambda: None)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.invalid/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "dummy")
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
    seen: dict = {}
    monkeypatch.setattr(azure_mod.openai, "AzureOpenAI", lambda **kw: seen.update(kw) or object())
    AzureOpenAILLM()
    assert seen == {"azure_endpoint": "https://example.invalid/", "api_key": "dummy", "api_version": "2024-10-21"}


def test_factory_azure_replay_uses_subdir_and_no_client(tmp_path, monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("client must not be constructed in replay")

    monkeypatch.setattr(azure_mod, "AzureOpenAILLM", boom)
    llm = make_llm("replay", str(tmp_path), provider="azure")
    assert isinstance(llm, RecordingLLM)
    assert llm.inner is None
    assert llm.recordings_dir == tmp_path / "azure"


def test_factory_azure_live_builds_inner(tmp_path, monkeypatch):
    sentinel = SimpleNamespace(model_id="", generate_json=None)
    monkeypatch.setattr(azure_mod, "AzureOpenAILLM", lambda: sentinel)
    llm = make_llm("record", str(tmp_path), provider="azure")
    assert llm.inner is sentinel
    assert llm.recordings_dir == tmp_path / "azure"


def test_factory_gemini_unchanged(tmp_path):
    llm = make_llm("replay", str(tmp_path))
    assert isinstance(llm, RecordingLLM)
    assert llm.recordings_dir == tmp_path
    assert make_llm("replay", str(tmp_path), provider="gemini").recordings_dir == tmp_path


def test_factory_unknown_provider(tmp_path):
    with pytest.raises(ValueError, match="unknown provider"):
        make_llm("replay", str(tmp_path), provider="bedrock")
