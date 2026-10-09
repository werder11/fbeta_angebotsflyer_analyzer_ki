"""LLM factory: selects mode (live/record/replay) and provider (gemini/azure), ADR-0003/0008."""
from pathlib import Path

from flyercheck.llm.port import LLMPort
from flyercheck.llm.recording import MODES, RecordingLLM

PROVIDERS = ("gemini", "azure")


def make_llm(mode: str = "replay", recordings_dir: str = "data/recordings", provider: str = "gemini") -> LLMPort:
    """Gemini records into `recordings_dir`; Azure into `recordings_dir/azure`, so providers never share recordings."""
    if mode not in MODES:
        raise ValueError(f"invalid mode {mode!r}; expected one of {MODES}")
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider!r}; expected one of {PROVIDERS}")
    inner: LLMPort | None = None
    if provider == "azure":
        if mode in ("live", "record"):
            from flyercheck.llm.azure import AzureOpenAILLM  # lazy: replay never needs the SDK or a key

            inner = AzureOpenAILLM()
        return RecordingLLM(inner, mode, str(Path(recordings_dir) / "azure"))
    if mode in ("live", "record"):
        from flyercheck.llm.gemini import GeminiLLM  # lazy: replay never needs the SDK or a key

        inner = GeminiLLM()
    return RecordingLLM(inner, mode, recordings_dir)
