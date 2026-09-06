"""Private host endpoints for bounded review inputs and validated role reports."""
from __future__ import annotations

import json
import re
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from bridgeflow import business, profiling
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


class ReviewSubmission(BaseModel):
    batch_id: str
    parent_session_id: str
    runs: list[RoleRun] = Field(min_length=4, max_length=4)


@router.post("/review-finalize")
async def review_finalize(request: ReviewSubmission) -> dict:
    context = business.context(request.batch_id, load_batch(request.batch_id))
    if {run.role for run in request.runs} != set(business.ROLES):
        raise HTTPException(422, "Exactly one result per department is required")
    packets = {packet["role"]: packet for packet in context["roles"]}
    roles = []
    for run in request.runs:
        try:
            if run.status != "completed" or run.judgement is None:
                raise ValueError(f"Child did not complete: {run.status}; {run.error[:300]}")
            verified = business.validate_role(packets[run.role], run.judgement)
            roles.append({**verified, "session_id": run.session_id, "status": "validated"})
        except (HTTPException, ValidationError, ValueError) as exc:
            roles.append({"role": run.role, "session_id": run.session_id, "status": "unvalidated",
                "error": str(exc)[:500], "checks": [], "responsibility": packets[run.role]["responsibility"],
                "decision_owner": packets[run.role]["decision_owner"]})
    complete = all(role["status"] == "validated" for role in roles)
    report = {"report_id": uuid.uuid4().hex, "batch_id": request.batch_id, "period": context["period"],
        "parent_session_id": request.parent_session_id, "status": "validated" if complete else "partial",
        "case": context["case"], "roles": roles, "limitations": [*context["limitations"],
            "本报告直接汇总声明列，不消费待确认的跨部门映射；判断通过不代表主表已签发"],
        "manager_decision": context["manager_decision"] if complete else "Review incomplete; do not authorize a business decision",
        "execution_status": "analysis_only_no_business_action_executed"}
    folder = batch_path(request.batch_id).parent / "reviews" / request.batch_id
    _write(folder / f"{report['report_id']}.json", report)
    return report


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
