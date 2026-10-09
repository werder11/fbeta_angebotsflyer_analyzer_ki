"""REST API + review decisions (docs/api/README.md, ADR-0006). Owned by Phase 3 track E3.

PoC: validations run synchronously inside the request (201 instead of the target 202).
"""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from flyercheck import pipeline
from flyercheck.api.store import FileStore, InvalidRunId, validate_run_id
from flyercheck.domain.models import (
    Decision,
    DocumentContext,
    Finding,
    ReviewDecision,
    RunResult,
    Status,
)
from flyercheck.llm.port import LLMError

ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg"}


# ---- response / request models -------------------------------------------------------------
class ValidationCreated(BaseModel):
    run_id: str
    status_counts: dict[str, int]
    offers: int
    report_url: str
    findings_url: str


class ValidationListItem(BaseModel):
    run_id: str
    filename: str
    started_at: datetime
    status_counts: dict[str, int]


class ValidationSummary(BaseModel):
    run_id: str
    contract_version: str
    started_at: datetime
    duration_s: float
    mode: str
    context: DocumentContext
    versions: dict[str, str]
    llm_usage: dict[str, int]
    status_counts: dict[str, int]
    decision_counts: dict[str, int]
    report_url: str
    findings_url: str


class FindingWithDecision(Finding):
    decision: ReviewDecision | None = None


class DecisionRequest(BaseModel):
    decision: Decision
    reviewer: str = Field(default="anonymous", min_length=1)
    reason: str = ""


# ---- helpers -------------------------------------------------------------------------------
def _status_counts(findings: list[Finding]) -> dict[str, int]:
    c = Counter(str(f.status) for f in findings)
    return {s.value: c.get(s.value, 0) for s in Status}


def _urls(run_id: str) -> tuple[str, str]:
    base = f"/v1/validations/{run_id}"
    return f"{base}/report", f"{base}/findings"


def create_app(out_dir: str = "out", recordings_dir: str = "data/recordings") -> FastAPI:
    app = FastAPI(title="FlyerCheck API", version="0.1.0")
    store = FileStore(out_dir)
    app.state.store = store

    def load_run(run_id: str) -> RunResult:
        try:
            validate_run_id(run_id)
        except InvalidRunId as e:
            raise HTTPException(400, str(e)) from e
        run = store.get_run(run_id)
        if run is None:
            raise HTTPException(404, f"run {run_id!r} not found")
        return run

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/validations", status_code=201, response_model=ValidationCreated)
    def create_validation(
        file: Annotated[UploadFile, File()],
        mode: Annotated[Literal["replay", "record", "live"], Form()] = "replay",
        year: Annotated[int | None, Form()] = None,
        provider: Annotated[Literal["gemini", "azure"], Form()] = "gemini",
    ) -> ValidationCreated:
        name = Path(file.filename or "").name
        if Path(name).suffix.lower() not in ALLOWED_EXT:
            raise HTTPException(400, "unsupported file type: expected .pdf, .png or .jpg")
        uploads = Path(out_dir) / "_uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        target = uploads / f"{uuid.uuid4().hex}-{name}"
        with target.open("wb") as fh:
            while chunk := file.file.read(1 << 20):
                fh.write(chunk)
        try:
            result = pipeline.run(
                str(target), out=out_dir, mode=mode, year=year,
                recordings_dir=recordings_dir, provider=provider,
            )
        except LLMError as e:
            raise HTTPException(422, f"LLM error: {e}") from e
        except ValueError as e:  # e.g. unreadable/unsupported document
            raise HTTPException(422, str(e)) from e
        report_url, findings_url = _urls(result.run_id)
        return ValidationCreated(
            run_id=result.run_id,
            status_counts=_status_counts(result.findings),
            offers=len(result.context.offers),
            report_url=report_url,
            findings_url=findings_url,
        )

    @app.get("/v1/validations", response_model=list[ValidationListItem])
    def list_validations() -> list[ValidationListItem]:
        items = []
        for rid in store.run_ids():
            try:
                run = store.get_run(rid)
            except ValueError:  # unreadable/foreign findings.json — skip
                continue
            if run is None:
                continue
            items.append(ValidationListItem(
                run_id=run.run_id, filename=run.context.document.filename,
                started_at=run.started_at, status_counts=_status_counts(run.findings),
            ))
        return sorted(items, key=lambda i: i.started_at, reverse=True)

    @app.get("/v1/validations/{run_id}", response_model=ValidationSummary)
    def get_validation(run_id: str) -> ValidationSummary:
        run = load_run(run_id)
        latest = store.latest_decisions(run_id)
        dc = Counter(str(d.decision) for d in latest.values())
        report_url, findings_url = _urls(run_id)
        return ValidationSummary(
            **run.model_dump(exclude={"findings"}),
            status_counts=_status_counts(run.findings),
            decision_counts={d.value: dc.get(d.value, 0) for d in Decision},
            report_url=report_url,
            findings_url=findings_url,
        )

    @app.get("/v1/validations/{run_id}/findings", response_model=list[FindingWithDecision])
    def get_findings(run_id: str, status: Annotated[Status | None, Query()] = None) -> list[FindingWithDecision]:
        run = load_run(run_id)
        latest = store.latest_decisions(run_id)
        return [
            FindingWithDecision(**f.model_dump(), decision=latest.get(f.id))
            for f in run.findings
            if status is None or f.status == status
        ]

    @app.get("/v1/validations/{run_id}/report")
    def get_report(run_id: str) -> FileResponse:
        load_run(run_id)
        path = store.report_path(run_id)
        if path is None:
            raise HTTPException(404, "report not found")
        return FileResponse(path, media_type="text/html")

    @app.get("/v1/validations/{run_id}/decisions", response_model=list[ReviewDecision])
    def get_decisions(run_id: str) -> list[ReviewDecision]:
        load_run(run_id)
        return store.decisions(run_id)

    @app.post(
        "/v1/validations/{run_id}/findings/{finding_id:path}/decision",
        status_code=201, response_model=ReviewDecision,
    )
    def post_decision(run_id: str, finding_id: str, body: DecisionRequest) -> ReviewDecision:
        run = load_run(run_id)
        if not any(f.id == finding_id for f in run.findings):
            raise HTTPException(404, f"finding {finding_id!r} not found in run {run_id!r}")
        return store.add_decision(ReviewDecision(
            run_id=run_id, finding_id=finding_id, decision=body.decision,
            reviewer=body.reviewer, reason=body.reason, decided_at=datetime.now(UTC),
        ))

    return app
