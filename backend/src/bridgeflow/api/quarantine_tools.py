"""Tool bodies for quarantine dispositions (#88). Deciding and applying need a DSH approval."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from bridgeflow import quarantine
from bridgeflow.api.batches import BatchRef, assemble, batch_path, load_batch, summary
from bridgeflow.config import settings
from bridgeflow.security import consume_approval

router = APIRouter(prefix="/tools", tags=["quarantine"])


def _writes_allowed() -> None:
    if not settings.bridgeflow_allow_mapping_write:
        raise HTTPException(403, "Quarantine decisions disabled by deployment policy")


@router.post("/quarantine-list")
async def quarantine_list(request: BatchRef) -> dict:
    """Which rows are held and which checks they fail, by column name. No cell values."""
    return quarantine.entries(request.batch_id, load_batch(request.batch_id))


class DecideRequest(BaseModel):
    batch_id: str
    department: str
    index: int = Field(ge=0)
    action: Literal["release", "discard"]
    reason: str = Field(min_length=1, max_length=300)
    fixes: list[quarantine.Fix] = Field(default_factory=list, max_length=10)
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/quarantine-decide")
async def quarantine_decide(request: DecideRequest, http_request: Request) -> dict:
    _writes_allowed()
    batch = load_batch(request.batch_id)
    consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body())
    book = quarantine.decide(request.batch_id, batch, quarantine.Disposition(
        department=request.department, index=request.index, action=request.action, reason=request.reason,
        fixes=request.fixes, decided_by=request.confirmed_by, authorised_by="dsh-authenticated-session"))
    return {"batch_id": request.batch_id, "decisions": len(book.decisions),
            "next_step": "Decide the remaining rows, then apply to create a new batch; this batch stays frozen."}


class ApplyRequest(BaseModel):
    batch_id: str
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/quarantine-apply")
async def quarantine_apply(request: ApplyRequest, http_request: Request) -> dict:
    _writes_allowed()
    batch = load_batch(request.batch_id)
    consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body())
    return await quarantine.apply(request.batch_id, batch, batch_path=batch_path, load_batch=load_batch,
                                  assemble=assemble, summary=summary)
