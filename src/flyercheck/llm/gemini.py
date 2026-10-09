"""Gemini adapter (ADR-0003): per-purpose model fallback chain, retry/backoff, JSON-mode output."""
from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from flyercheck.llm.port import LLMError

log = logging.getLogger(__name__)

MODELS: dict[str, list[str]] = {
    "extract": ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest"],
    "vision": ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"],
}
RETRYABLE_CODES = {429, 500, 503}
BACKOFF_SECONDS = (2, 4, 8)
MAX_ATTEMPTS = 3
JSON_RETRY_SUFFIX = "\nReturn ONLY valid JSON."


def model_chain(purpose: str) -> list[str]:
    """Model chain for a purpose; env FLYERCHECK_MODELS_<PURPOSE> (comma-separated) overrides."""
    env = os.environ.get(f"FLYERCHECK_MODELS_{purpose.upper()}")
    if env:
        chain = [m.strip() for m in env.split(",") if m.strip()]
        if chain:
            return chain
    if purpose not in MODELS:
        raise ValueError(f"unknown purpose {purpose!r}; expected one of {sorted(MODELS)}")
    return list(MODELS[purpose])


def _is_schema_rejection(exc: errors.APIError) -> bool:
    text = f"{exc.status} {exc.message} {exc}".lower()
    return (exc.code == 400 or "invalid_argument" in text) and "schema" in text


class GeminiLLM:
    """google-genai client with a per-purpose model fallback chain.

    `sleep` is injectable so tests don't actually wait during backoff.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: object | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        load_dotenv()
        if client is None:
            api_key = api_key or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise LLMError("GEMINI_API_KEY is not set (needed for --mode live/record)")
            client = genai.Client(api_key=api_key)
        self.client = client
        self.sleep = sleep
        self.model_id = ""
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0}
        self._schema_supported = True

    def generate_json(self, prompt: str, images: list[bytes], schema: dict, *, purpose: str) -> dict:
        text = self._generate(prompt, images, schema, purpose)
        try:
            return self._parse(text)
        except ValueError:
            log.warning("invalid JSON from %s; retrying once with stricter prompt", self.model_id)
        text = self._generate(prompt + JSON_RETRY_SUFFIX, images, schema, purpose)
        try:
            return self._parse(text)
        except ValueError as exc:
            raise LLMError(f"model {self.model_id} returned invalid JSON twice: {exc}") from exc

    @staticmethod
    def _parse(text: str | None) -> dict:
        if not text:
            raise ValueError("empty response")
        data = json.loads(text)  # JSONDecodeError is a ValueError
        if not isinstance(data, dict):
            raise ValueError(f"expected a JSON object, got {type(data).__name__}")  # noqa: TRY004
        return data

    def _config(self, schema: dict) -> types.GenerateContentConfig:
        if self._schema_supported:
            return types.GenerateContentConfig(
                response_mime_type="application/json", response_json_schema=schema, temperature=0
            )
        return types.GenerateContentConfig(response_mime_type="application/json", temperature=0)

    def _generate(self, prompt: str, images: list[bytes], schema: dict, purpose: str) -> str | None:
        contents: list = [types.Part.from_bytes(data=img, mime_type="image/png") for img in images]
        contents.append(prompt)
        last_exc: Exception | None = None
        for model in model_chain(purpose):
            attempt = 0
            schema_fallback_used = False
            while attempt < MAX_ATTEMPTS:
                try:
                    response = self.client.models.generate_content(
                        model=model, contents=contents, config=self._config(schema)
                    )
                except errors.APIError as exc:
                    last_exc = exc
                    if self._schema_supported and not schema_fallback_used and _is_schema_rejection(exc):
                        log.warning("%s rejected response_json_schema; falling back to mime-only", model)
                        self._schema_supported = False
                        schema_fallback_used = True
                        continue
                    if exc.code in RETRYABLE_CODES:
                        delay = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
                        attempt += 1
                        if attempt < MAX_ATTEMPTS:
                            log.warning("%s -> %s; retry %d in %ss", model, exc.code, attempt, delay)
                            self.sleep(delay)
                        continue
                    log.warning("%s -> %s; trying next model", model, exc.code)
                    break  # 404 and other non-retryable errors: next model
                self.model_id = model
                self._add_usage(response)
                return response.text
        raise LLMError(f"all models failed for purpose={purpose!r}: {last_exc}")

    def _add_usage(self, response: object) -> None:
        meta = getattr(response, "usage_metadata", None)
        self.usage["calls"] += 1
        if meta is None:
            return
        self.usage["input_tokens"] += getattr(meta, "prompt_token_count", None) or 0
        self.usage["output_tokens"] += getattr(meta, "candidates_token_count", None) or 0
        self.usage["thinking_tokens"] += getattr(meta, "thoughts_token_count", None) or 0
