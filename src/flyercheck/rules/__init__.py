"""Deterministic rules R-01..R-08. Owned by track T3. No LLM calls (ADR-0001)."""
from flyercheck.domain.models import Category, DocumentContext, Finding, Severity, Status
from flyercheck.rules import (  # noqa: F401  (importing registers the rules)
    r_01_unit_price,
    r_02_discount,
    r_02b_discount_rounding,
    r_03_deposit,
    r_04_grundpreis_present,
    r_05_validity_weekday,
    r_06_required_fields,
    r_07_page_refs,
    r_08_master_data,
)
from flyercheck.rules.base import REGISTRY

RULES_VERSION = "rules@1.0"


def run_rules(ctx: DocumentContext) -> list[Finding]:
    findings: list[Finding] = []
    for check_id, fn in REGISTRY.items():
        try:
            findings.extend(fn(ctx))
        except Exception as exc:  # noqa: BLE001  (a crashing rule must never kill the run)
            findings.append(Finding(
                id=f"{check_id}:doc",
                check_id=check_id,
                category=Category.E08_COMPLETENESS,
                severity=Severity.MEDIUM,
                status=Status.ERROR,
                summary=f"Rule {check_id} raised {type(exc).__name__}: {exc}",
                confidence=0.0,
                rule_version=f"{check_id}@1.0",
            ))
    return findings
