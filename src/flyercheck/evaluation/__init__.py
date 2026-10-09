"""Golden-set evaluation. Owned by track T5."""
from flyercheck.domain.models import Finding, GoldenSet


def evaluate(findings: list[Finding], golden: GoldenSet) -> dict:
    raise NotImplementedError


def format_eval(result: dict) -> str:
    raise NotImplementedError
