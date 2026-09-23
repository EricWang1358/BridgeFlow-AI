"""Risk disposition: taking a declared action on a finding, with approval (E07-UC07).

Reading is a projection over the review's own findings; writing is a decision, so it needs a
DSH approval receipt and records the approver as the actor. The machine is the company's
declaration — this layer only carries requests to it and enforces who may see the batch.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from bridgeflow.api.batches import BatchRef, _visible, load_batch
from bridgeflow.api.reviews import saved_review
from bridgeflow.config import settings
from bridgeflow.identity import UserIdentity, require_user
from bridgeflow.monthly import dispositions
from bridgeflow.security import consume_approval

router = APIRouter(tags=["dispositions"])


def _findings(report: dict) -> list[str]:
    """Every check the review reported as needing attention, in the report's own order."""
    return [check["check_id"] for role in report.get("roles", []) for check in role.get("checks", [])
            if check.get("status") == "attention" or check.get("expected_status") == "attention"]


def _report(batch_id: str, report_id: str | None, user: UserIdentity | None) -> tuple[dict, dict]:
    batch = _visible(load_batch(batch_id), user)
    return batch.dictionary_snapshot or {}, saved_review(batch_id, report_id)


@router.get("/reviews/{batch_id}/dispositions")
async def list_dispositions(batch_id: str, user: Annotated[UserIdentity | None, Depends(require_user)],
                            report_id: str | None = None) -> dict:
    dictionary, report = _report(batch_id, report_id, user)
    result = dispositions.current(dictionary, batch_id, report["report_id"], _findings(report))
    # A person reads the finding's title, not its check id; both come from the same report.
    titles = {check["check_id"]: check.get("title", "") for role in report.get("roles", [])
              for check in role.get("checks", [])}
    for item in result.get("dispositions", []):
        item.setdefault("title", titles.get(item.get("check_id", ""), ""))
    return result


@router.post("/tools/risk-dispositions")
async def dispositions_tool(request: BatchRef) -> dict:
    """For the captain: each attention finding's state and which actions the declaration allows."""
    dictionary, report = _report(request.batch_id, None, None)
    result = dispositions.current(dictionary, request.batch_id, report["report_id"], _findings(report))
    return result | {"next_step": (result.get("refusal") or
                                   "Say which findings are still open and what the declaration allows next; "
                                   "a disposition is the person's decision and needs their approval.")}


class RecordRequest(BaseModel):
    batch_id: str
    check_id: str
    action: str = Field(min_length=1, max_length=40)
    note: str = Field(default="", max_length=400)
    report_id: str | None = None
    expected_version: int | None = None
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/tools/risk-disposition-record")
async def record_disposition(request: RecordRequest, http_request: Request) -> dict:
    if not settings.bridgeflow_allow_mapping_write:
        raise HTTPException(403, "Risk dispositions disabled by deployment policy")
    dictionary, report = _report(request.batch_id, request.report_id, None)
    if request.check_id not in _findings(report):
        raise HTTPException(404, "That finding is not in this report's attention items")
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""),
                             await http_request.body(), "risk_disposition")
    state = dispositions.record(dictionary=dictionary, batch_id=request.batch_id, report_id=report["report_id"],
                                check_id=request.check_id, action=request.action, note=request.note,
                                expected_version=request.expected_version, actor=actor)
    return {**state.model_dump(mode="json"), "report_id": report["report_id"],
            "next_step": ("This finding is closed; the report and its figures are unchanged."
                          if state.closed else
                          f"Next actions allowed by the declaration: {', '.join(state.available) or 'none'}.")}
