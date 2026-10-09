"""Rule registry. FROZEN during parallel work."""
from collections.abc import Callable

from flyercheck.domain.models import DocumentContext, Finding

RuleFn = Callable[[DocumentContext], list[Finding]]
REGISTRY: dict[str, RuleFn] = {}


def register(check_id: str) -> Callable[[RuleFn], RuleFn]:
    def deco(fn: RuleFn) -> RuleFn:
        REGISTRY[check_id] = fn
        return fn

    return deco
