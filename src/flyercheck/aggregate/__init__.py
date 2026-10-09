"""Dedupe and prioritize findings. Owned by track T3."""
from flyercheck.domain.models import Finding


def aggregate(findings: list[Finding]) -> list[Finding]:
    raise NotImplementedError
