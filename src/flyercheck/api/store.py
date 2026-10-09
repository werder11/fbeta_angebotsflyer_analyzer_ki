"""File-based run/decision store (PoC). Replaceable by a DB-backed store (ADR-0007).

Layout: {out_dir}/{run_id}/findings.json (RunResult), report.html, decisions.jsonl (append-only).
"""
from __future__ import annotations

import re
import threading
from pathlib import Path

from flyercheck.domain.models import ReviewDecision, RunResult

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class InvalidRunId(ValueError):
    pass


def validate_run_id(run_id: str) -> str:
    if not _RUN_ID_RE.fullmatch(run_id or ""):
        raise InvalidRunId(f"invalid run_id {run_id!r}")
    return run_id


class FileStore:
    def __init__(self, out_dir: str | Path) -> None:
        self.root = Path(out_dir)
        self._lock = threading.Lock()

    def run_dir(self, run_id: str) -> Path:
        return self.root / validate_run_id(run_id)

    def run_ids(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(
            p.name
            for p in self.root.iterdir()
            if p.is_dir() and _RUN_ID_RE.fullmatch(p.name) and (p / "findings.json").is_file()
        )

    def get_run(self, run_id: str) -> RunResult | None:
        path = self.run_dir(run_id) / "findings.json"
        if not path.is_file():
            return None
        return RunResult.model_validate_json(path.read_text(encoding="utf-8"))

    def report_path(self, run_id: str) -> Path | None:
        path = self.run_dir(run_id) / "report.html"
        return path if path.is_file() else None

    def add_decision(self, decision: ReviewDecision) -> ReviewDecision:
        path = self.run_dir(decision.run_id) / "decisions.jsonl"
        line = decision.model_dump_json() + "\n"
        with self._lock, path.open("a", encoding="utf-8") as fh:
            fh.write(line)
        return decision

    def decisions(self, run_id: str) -> list[ReviewDecision]:
        path = self.run_dir(run_id) / "decisions.jsonl"
        if not path.is_file():
            return []
        with self._lock:
            lines = path.read_text(encoding="utf-8").splitlines()
        return [ReviewDecision.model_validate_json(ln) for ln in lines if ln.strip()]

    def latest_decisions(self, run_id: str) -> dict[str, ReviewDecision]:
        latest: dict[str, ReviewDecision] = {}
        for d in self.decisions(run_id):  # append order == chronological order
            latest[d.finding_id] = d
        return latest
