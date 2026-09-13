"""Private host endpoints for bounded review inputs and validated role reports."""
from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from bridgeflow import business, profiling, review_runs
from bridgeflow.api.batches import BatchRef, batch_path, load_batch, summary
from bridgeflow.store import _write

router = APIRouter(prefix="/tools", tags=["reviews"])


@router.post("/review-context")
async def review_context(request: BatchRef) -> dict:
    return business.context(request.batch_id, load_batch(request.batch_id))


@router.post("/profile-batch", response_model=profiling.BatchProfile)
async def profile_batch(request: BatchRef) -> profiling.BatchProfile:
    """What the columns look like, so a blocked batch has a way forward.

    Called when a batch cannot be joined. It answers the question the refusal
    raises and cannot answer itself — *which column should have been declared* —
    without putting a single cell in front of the model: counts, ratios, and
    cross-department overlap computed over hashes.
    """
    batch = load_batch(request.batch_id)
    return profiling.profile(
        request.batch_id, batch.period, batch.clean_tables,
        declared=summary(request.batch_id, batch).declared_entities,
    )


class RoleRun(BaseModel):
    role: str
    session_id: str
    status: str
    judgement: dict[str, Any] | None = None
    error: str = ""
    started_at: str = ""
    ended_at: str = ""


class ReviewOpen(BaseModel):
    review_id: str
    batch_id: str
    parent_session_id: str
    deadline_seconds: int = Field(180, ge=10, le=3600)


@router.post("/review-open")
async def review_open(request: ReviewOpen) -> dict:
    """Register a review before any department is dispatched, with its deadline."""
    load_batch(request.batch_id)
    try:
        return review_runs.open_run(request.review_id, request.batch_id, request.parent_session_id,
                                    request.deadline_seconds).model_dump()
    except review_runs.RunError as exc:
        raise HTTPException(409, str(exc)) from exc


class ReviewSubmission(BaseModel):
    batch_id: str
    parent_session_id: str
    runs: list[RoleRun] = Field(min_length=4, max_length=4)
    review_id: str = ""
    terminal_reason: review_runs.TerminalReason = "completed"


@router.post("/review-finalize")
async def review_finalize(request: ReviewSubmission) -> dict:
    run = None
    if request.review_id:
        try:
            run = review_runs.get(request.review_id)
        except review_runs.RunError as exc:
            raise HTTPException(422, str(exc)) from exc
        if run is None:
            raise HTTPException(409, "Unknown review; open it before finalizing")
        if (run.batch_id, run.parent_session_id) != (request.batch_id, request.parent_session_id):
            raise HTTPException(409, "Review belongs to another batch or session")
        if run.status == "finalized":
            # Idempotent: a retry, a lost response or a late finalize after a timeout
            # gets the report that already ended this review, never a second one.
            return saved_review(run.batch_id, run.report_id)
    reason = request.terminal_reason
    if run is not None and reason == "completed" and review_runs.expired(run):
        reason = "deadline_exceeded"
    context = business.context(request.batch_id, load_batch(request.batch_id))
    if {r.role for r in request.runs} != set(business.ROLES):
        raise HTTPException(422, "Exactly one result per department is required")
    report = _report(request, context, reason)
    folder = batch_path(request.batch_id).parent / "reviews" / request.batch_id
    _write(folder / f"{report['report_id']}.json", report)
    if run is not None:
        review_runs.close(run, report["report_id"], reason)
    return report


def _report(request: ReviewSubmission, context: dict, reason: str) -> dict:
    packets = {packet["role"]: packet for packet in context["roles"]}
    roles = []
    for role_run in request.runs:
        timing = {"started_at": role_run.started_at, "ended_at": role_run.ended_at}
        try:
            if reason != "completed":
                raise ValueError(f"Review ended before this department was accepted: {reason}")
            if role_run.status != "completed" or role_run.judgement is None:
                raise ValueError(f"Child did not complete: {role_run.status}; {role_run.error[:300]}")
            verified = business.validate_role(packets[role_run.role], role_run.judgement)
            roles.append({**verified, "session_id": role_run.session_id, "status": "validated", **timing})
        except (HTTPException, ValidationError, ValueError) as exc:
            roles.append({"role": role_run.role, "session_id": role_run.session_id, "status": "unvalidated",
                "error": str(exc)[:500], "checks": [], "responsibility": packets[role_run.role]["responsibility"],
                "decision_owner": packets[role_run.role]["decision_owner"], **timing})
    complete = reason == "completed" and all(role["status"] == "validated" for role in roles)
    return {"report_id": uuid.uuid4().hex, "batch_id": request.batch_id, "period": context["period"],
        "review_id": request.review_id, "terminal_reason": reason,
        "parent_session_id": request.parent_session_id, "status": "validated" if complete else "partial",
        "case": context["case"], "roles": roles, "limitations": [*context["limitations"],
            "本报告直接汇总声明列，不消费待确认的跨部门映射；判断通过不代表主表已签发"],
        "manager_decision": context["manager_decision"] if complete else "Review incomplete; do not authorize a business decision",
        "execution_status": "analysis_only_no_business_action_executed",
        "finalized_at": datetime.now(UTC).isoformat()}


@router.post("/review-recover")
async def review_recover() -> dict:
    """End every review a restarted host can no longer finish, with a readable terminal report."""
    ended = []
    for run in review_runs.open_runs():
        runs = [RoleRun(role=role, session_id="", status="aborted", error="Host restarted before finalization")
                for role in business.ROLES]
        submission = ReviewSubmission(batch_id=run.batch_id, parent_session_id=run.parent_session_id, runs=runs,
                                      review_id=run.review_id, terminal_reason="host_restarted")
        try:
            report = await review_finalize(submission)
            ended.append({"review_id": run.review_id, "report_id": report["report_id"]})
        except HTTPException as exc:
            # A batch that can no longer build its context still must not stay open.
            review_runs.close(run, "", f"host_restarted: {exc.detail}")
            ended.append({"review_id": run.review_id, "report_id": ""})
    return {"ended": ended}


class NoteRequest(BaseModel):
    batch_id: str
    report_id: str
    parent_session_id: str
    note_id: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$")
    note: str = Field(min_length=1, max_length=500)


@router.post("/review-note")
async def review_note(request: NoteRequest) -> dict:
    """Record a person's note on a saved report. It never changes the report's status."""
    saved_review(request.batch_id, request.report_id)
    note = review_runs.HumanNote(**request.model_dump(), recorded_at=datetime.now(UTC).isoformat())
    stored, added = review_runs.add_note(note)
    return {"recorded": added, "notes": len(stored)}


def saved_review(batch_id: str, report_id: str | None = None) -> dict:
    folder = batch_path(batch_id).parent / "reviews" / batch_id
    if report_id is not None:
        if not re.fullmatch(r"[a-f0-9]{32}", report_id):
            raise HTTPException(422, "Invalid report ID")
        path = folder / f"{report_id}.json"
        if not path.is_file():
            raise HTTPException(404, "Report not found in this batch")
        return json.loads(path.read_text(encoding="utf-8"))
    paths = sorted(folder.glob("*.json"), key=lambda path: path.stat().st_mtime_ns) if folder.exists() else []
    if not paths:
        raise HTTPException(404, "This batch has no saved review")
    return json.loads(paths[-1].read_text(encoding="utf-8"))


def review_notes(batch_id: str, report_id: str) -> dict:
    """Notes are kept beside the report, not in it: the report is what the review produced."""
    saved_review(batch_id, report_id)
    return {"report_id": report_id, "notes": [n.model_dump() for n in review_runs.notes(batch_id, report_id)]}
