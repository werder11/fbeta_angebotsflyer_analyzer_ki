"""Deterministic rules (auto-discovered r_*.py modules). No LLM calls (ADR-0001)."""
import importlib
import pkgutil

import flyercheck.rules as _pkg
from flyercheck.domain.models import Category, DocumentContext, Finding, Severity, Status
from flyercheck.rules.base import REGISTRY

# Auto-discover rule modules (r_*.py); importing registers them. New rules need no edit here.
for _m in sorted(pkgutil.iter_modules(_pkg.__path__), key=lambda m: m.name):
    if _m.name.startswith("r_") and _m.name != "r_common":
        importlib.import_module(f"{_pkg.__name__}.{_m.name}")

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
