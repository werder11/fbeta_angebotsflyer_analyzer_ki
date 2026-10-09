"""Deterministic rules R-01..R-08. Owned by track T3."""
from flyercheck.domain.models import DocumentContext, Finding


def run_rules(ctx: DocumentContext) -> list[Finding]:
    raise NotImplementedError
