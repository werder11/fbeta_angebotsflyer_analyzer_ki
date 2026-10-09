"""Mutation-based synthetic defects for rule-level evaluation (risk R10). Owned by Phase 3 track E2."""
from flyercheck.domain.models import DocumentContext


def run_mutation_eval(ctx: DocumentContext) -> dict:
    """Apply each mutation operator to ctx, run rules, check the seeded defect is detected."""
    raise NotImplementedError


def format_mutation_eval(result: dict) -> str:
    raise NotImplementedError
