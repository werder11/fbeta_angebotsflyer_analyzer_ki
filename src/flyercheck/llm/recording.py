"""Record/replay wrapper around any LLMPort (ADR-0008)."""
from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from flyercheck.llm.port import LLMError, LLMPort, request_key

MODES = ("live", "record", "replay")
USAGE_KEYS = ("calls", "input_tokens", "output_tokens", "thinking_tokens")


class RecordingLLM:
    """mode: live (pass-through) | record (live + write file) | replay (read file; miss -> LLMError)."""

    def __init__(self, inner: LLMPort | None, mode: str, recordings_dir: str) -> None:
        if mode not in MODES:
            raise ValueError(f"invalid mode {mode!r}; expected one of {MODES}")
        if mode != "replay" and inner is None:
            raise ValueError(f"mode {mode!r} requires an inner LLM")
        self.inner = inner
        self.mode = mode
        self.recordings_dir = Path(recordings_dir)
        self.model_id = getattr(inner, "model_id", "") if inner is not None else "replay"
        self.usage = dict.fromkeys(USAGE_KEYS, 0)
        self._lock = threading.Lock()

    def path_for(self, key: str) -> Path:
        return self.recordings_dir / f"{key}.json"

    def generate_json(self, prompt: str, images: list[bytes], schema: dict, *, purpose: str) -> dict:
        key = request_key(purpose, prompt, images, schema)
        if self.mode == "replay":
            return self._replay(key, purpose)
        return self._call_inner(key, prompt, images, schema, purpose)

    def _replay(self, key: str, purpose: str) -> dict:
        path = self.path_for(key)
        if not path.exists():
            raise LLMError(
                f"no recording for purpose={purpose!r} key={key} at {path}; "
                "run with --mode record (needs GEMINI_API_KEY) to create it"
            )
        rec = json.loads(path.read_text(encoding="utf-8"))
        with self._lock:
            self.model_id = rec.get("model_id") or self.model_id
            self.usage["calls"] += 1
        return rec["response"]

    def _call_inner(self, key: str, prompt: str, images: list[bytes], schema: dict, purpose: str) -> dict:
        assert self.inner is not None
        # Note: under concurrency the inner-usage delta is approximate; totals stay correct for
        # sequential calls, and calls are always counted once per request.
        inner_usage = getattr(self.inner, "usage", None)
        before = dict(inner_usage) if isinstance(inner_usage, dict) else {}
        response = self.inner.generate_json(prompt, images, schema, purpose=purpose)
        after = getattr(self.inner, "usage", None)
        after = after if isinstance(after, dict) else {}
        delta = {k: max(after.get(k, 0) - before.get(k, 0), 0) for k in USAGE_KEYS}
        delta["calls"] = 1
        model_id = getattr(self.inner, "model_id", "")
        with self._lock:
            self.model_id = model_id
            for k in USAGE_KEYS:
                self.usage[k] += delta[k]
        if self.mode == "record":
            self.recordings_dir.mkdir(parents=True, exist_ok=True)
            rec = {
                "purpose": purpose,
                "model_id": model_id,
                "response": response,
                "usage": delta,
                "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
            self.path_for(key).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        return response
