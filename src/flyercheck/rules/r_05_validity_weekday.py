"""R-05: validity period weekday labels match the dates."""
from __future__ import annotations

from datetime import date

from flyercheck.domain.models import Category, DocumentContext, Finding, Severity, Status, Validity
from flyercheck.rules.base import register
from flyercheck.rules.r_common import make_finding

CHECK_ID = "R-05"
RULE_VERSION = "R-05@1.0"
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
YEAR_RANGE = range(2024, 2031)


def _date(year: int, month: int | None, day: int | None) -> date | None:
    if month is None or day is None:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _ends(v: Validity) -> list[tuple[str, str | None, int | None, int | None]]:
    return [("from", v.from_weekday, v.from_month, v.from_day),
            ("until", v.until_weekday, v.until_month, v.until_day)]


def _matches(v: Validity, year: int) -> bool:
    for _, wd, m, d in _ends(v):
        if wd is None:
            continue
        dt = _date(year, m, d)
        if dt is None or WEEKDAYS[dt.weekday()] != wd:
            return False
    return True


def _dm(day: int | None, month: int | None) -> str:
    return f"{day:02d}.{month:02d}." if day and month else "?"


@register(CHECK_ID)
def check(ctx: DocumentContext) -> list[Finding]:
    v = ctx.validity
    common = {"category": Category.E06_TEMPORAL, "severity": Severity.HIGH, "rule_version": RULE_VERSION}
    if v is None:
        return [make_finding(CHECK_ID, status=Status.NOT_EVALUABLE,
                             summary="No validity period found; weekday check not possible.", **common)]
    common.update(page=1, bbox=v.bbox, raw=v.raw)
    observed = {"validity": v.raw, "from_weekday": v.from_weekday or "", "until_weekday": v.until_weekday or ""}
    matching = ", ".join(str(y) for y in YEAR_RANGE if _matches(v, y)) or "none"
    year = ctx.document.campaign_year
    if year is None:
        return [make_finding(
            CHECK_ID, status=Status.NEEDS_REVIEW,
            summary=f"Campaign year unknown; weekday labels match in years: {matching}.",
            observed=observed, expected={"matching_years": matching}, **common)]
    problems: list[str] = []
    expected = {"campaign_year": str(year), "matching_years": matching}
    for key, wd, m, d in _ends(v):
        dt = _date(year, m, d)
        if dt is None:
            continue
        actual = WEEKDAYS[dt.weekday()]
        expected[f"{key}_weekday"] = actual
        if wd is not None and wd != actual:
            problems.append(f"{wd} {_dm(d, m)}{year} is a {WEEKDAY_NAMES[dt.weekday()]} ({actual})")
    f_dt = _date(year, v.from_month, v.from_day)
    u_dt = _date(year, v.until_month, v.until_day)
    if f_dt and u_dt and u_dt < f_dt:
        problems.append(f"end {_dm(v.until_day, v.until_month)} is before start {_dm(v.from_day, v.from_month)}")
    if problems:
        conf = 0.95 if ctx.document.campaign_year_source == "cli" else 0.8
        return [make_finding(
            CHECK_ID, status=Status.FAIL,
            summary="Validity mismatch: " + "; ".join(problems) + f". Labels match in: {matching}.",
            observed=observed, expected=expected, confidence=conf, **common)]
    return [make_finding(CHECK_ID, status=Status.PASS, summary=f"Validity weekdays match the dates in {year}.",
                         observed=observed, expected=expected, **common)]
