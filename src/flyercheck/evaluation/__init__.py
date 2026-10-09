"""Golden-set evaluation. Owned by track T5."""
from __future__ import annotations

from collections import defaultdict

from flyercheck.domain.models import Finding, GoldenLabel, GoldenSet, Status

POSITIVE = {Status.FAIL, Status.NEEDS_REVIEW}


def _matches(label: GoldenLabel, f: Finding) -> bool:
    if f.check_id != label.check_id:
        return False
    if label.offer_name is None:
        return f.offer_id is None
    return f.offer_name is not None and f.offer_name.casefold().startswith(label.offer_name.casefold())


def _match(label: GoldenLabel, findings: list[Finding]) -> Finding | None:
    """First matching finding, preferring one with the label's exact status."""
    cands = [f for f in findings if _matches(label, f)]
    for f in cands:
        if f.status == label.status:
            return f
    return cands[0] if cands else None


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def _scores(tp: int, fp: int, fn: int) -> dict:
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": _ratio(tp, tp + fp), "recall": _ratio(tp, tp + fn)}


def evaluate(findings: list[Finding], golden: GoldenSet) -> dict:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # tp, fp, fn
    matched_positive: set[int] = set()  # id() of positive findings matched by a positive label

    for label in golden.labels:
        if label.status not in POSITIVE:
            continue  # e.g. not_evaluable: status_agreement only
        hits = [f for f in findings if _matches(label, f) and f.status in POSITIVE]
        if hits:
            matched_positive.update(id(f) for f in hits)
            counts[hits[0].category.value][0] += 1
        else:
            any_match = _match(label, findings)
            counts[any_match.category.value if any_match else "unmatched"][2] += 1

    for f in findings:
        if f.status in POSITIVE and id(f) not in matched_positive:
            counts[f.category.value][1] += 1

    missing: list[str] = []
    mismatched: list[dict] = []
    agreed: dict[str, bool] = {}
    for label in golden.labels + golden.expected_passes:
        m = _match(label, findings)
        agreed[label.id] = m is not None and m.status == label.status
        if m is None:
            missing.append(label.id)
        elif m.status != label.status:
            mismatched.append({"id": label.id, "expected": label.status.value, "got": m.status.value})

    def agreement(labels: list[GoldenLabel]) -> float | None:
        return _ratio(sum(agreed[lb.id] for lb in labels), len(labels))

    tot = [sum(c[i] for c in counts.values()) for i in range(3)]
    return {
        "per_category": {cat: _scores(*c) for cat, c in sorted(counts.items())},
        "overall": _scores(*tot),
        "status_agreement": agreement(golden.labels + golden.expected_passes),
        "expected_pass_agreement": agreement(golden.expected_passes),
        "missing": missing,
        "mismatched": mismatched,
    }


def _fmt(v: float | None) -> str:
    return "—" if v is None else f"{v:.2f}"


def format_eval(result: dict) -> str:
    head = f"{'category':<22} {'TP':>4} {'FP':>4} {'FN':>4} {'precision':>9} {'recall':>7}"
    rule = "-" * len(head)

    def row(name: str, s: dict) -> str:
        return (f"{name:<22} {s['tp']:>4} {s['fp']:>4} {s['fn']:>4} "
                f"{_fmt(s['precision']):>9} {_fmt(s['recall']):>7}")

    lines = [head, rule]
    lines += [row(cat, s) for cat, s in result["per_category"].items()]
    lines += [rule, row("overall", result["overall"]), ""]
    lines.append(f"status_agreement:        {_fmt(result['status_agreement'])}")
    lines.append(f"expected_pass_agreement: {_fmt(result['expected_pass_agreement'])}")
    lines.append(f"missing:    {', '.join(result['missing']) or '—'}")
    mm = ", ".join(f"{m['id']} (expected {m['expected']}, got {m['got']})" for m in result["mismatched"])
    lines.append(f"mismatched: {mm or '—'}")
    return "\n".join(lines)
