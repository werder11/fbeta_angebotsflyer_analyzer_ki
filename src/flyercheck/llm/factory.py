"""LLM factory. Owned by track E4 in Phase 3."""
from flyercheck.llm.port import LLMPort
from flyercheck.llm.recording import MODES, RecordingLLM

PROVIDERS = ("gemini", "azure")


def make_llm(mode: str = "replay", recordings_dir: str = "data/recordings", provider: str = "gemini") -> LLMPort:
    if mode not in MODES:
        raise ValueError(f"invalid mode {mode!r}; expected one of {MODES}")
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider!r}; expected one of {PROVIDERS}")
    if provider == "azure":
        raise NotImplementedError("azure provider: Phase 3 track E4")
    inner: LLMPort | None = None
    if mode in ("live", "record"):
        from flyercheck.llm.gemini import GeminiLLM  # lazy: replay never needs the SDK or a key

        inner = GeminiLLM()
    return RecordingLLM(inner, mode, recordings_dir)
