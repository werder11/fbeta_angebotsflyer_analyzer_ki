"""LLM factory. Owned by track T1."""
from flyercheck.llm.port import LLMPort


def make_llm(mode: str = "replay", recordings_dir: str = "data/recordings") -> LLMPort:
    raise NotImplementedError
