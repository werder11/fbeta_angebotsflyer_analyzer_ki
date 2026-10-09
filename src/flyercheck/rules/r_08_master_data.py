"""R-08: prices vs. master data (no reference source configured in the PoC)."""
from __future__ import annotations

from flyercheck.domain.models import Category, DocumentContext, Finding, Severity, Status
from flyercheck.rules.base import register
from flyercheck.rules.r_common import make_finding

CHECK_ID = "R-08"
RULE_VERSION = "R-08@1.0"


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    return [make_finding(
        CHECK_ID, category=Category.E02_MASTER_DATA, severity=Severity.MEDIUM, status=Status.NOT_EVALUABLE,
        summary="No reference data source (PIM/price DB) configured.",
        observed={"offers": str(len(ctx.offers))}, expected={"reference": "PIM/price DB lookup"},
        rule_version=RULE_VERSION)]
