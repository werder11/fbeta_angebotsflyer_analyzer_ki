"""LLM factory. Owned by track T1."""
from flyercheck.llm.port import LLMPort
from flyercheck.llm.recording import MODES, RecordingLLM


def make_llm(mode: str = "replay", recordings_dir: str = "data/recordings") -> LLMPort:
    if mode not in MODES:
        raise ValueError(f"invalid mode {mode!r}; expected one of {MODES}")
    inner: LLMPort | None = None
    if mode in ("live", "record"):
        from flyercheck.llm.gemini import GeminiLLM  # lazy: replay never needs the SDK or a key

        inner = GeminiLLM()
    return RecordingLLM(inner, mode, recordings_dir)
