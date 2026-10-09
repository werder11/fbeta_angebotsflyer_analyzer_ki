"""LLM port (ADR-0003) and test double. FROZEN during parallel work."""
from __future__ import annotations

import hashlib
import json
from typing import Protocol


class LLMError(RuntimeError):
    """Raised when all retries/fallback models fail or output is not valid JSON."""


class LLMPort(Protocol):
    model_id: str

    def generate_json(self, prompt: str, images: list[bytes], schema: dict, *, purpose: str) -> dict:
        """Return a JSON object conforming to `schema`. `purpose` in {"extract","vision"} selects the model."""
        ...


def request_key(purpose: str, prompt: str, images: list[bytes], schema: dict) -> str:
    """Stable recording key. Uses purpose (not model) so fallback models don't invalidate recordings."""
    h = hashlib.sha256()
    for part in (purpose, prompt, json.dumps(schema, sort_keys=True)):
        h.update(part.encode())
    for img in images:
        h.update(hashlib.sha256(img).digest())
    return h.hexdigest()[:32]


class FakeLLM:
    """Test double: returns canned responses by purpose (a dict, or a list consumed in order); records calls."""

    model_id = "fake"

    def __init__(self, by_purpose: dict[str, dict | list[dict | Exception]] | None = None):
        self.by_purpose = by_purpose or {}
        self.calls: list[tuple[str, str]] = []

    def generate_json(self, prompt: str, images: list[bytes], schema: dict, *, purpose: str) -> dict:
        self.calls.append((purpose, prompt))
        resp = self.by_purpose[purpose]
        if isinstance(resp, list):
            resp = resp.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp
