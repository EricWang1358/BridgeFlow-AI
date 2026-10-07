"""Long-term memory: searching is a read, saving and retiring need approval (#303).

The captain searches before working a problem out again, and offers to save a solution once
the person has one; the memory is written only when the approval goes through, and the
approver is who the record names. The browser reads the same list, read-only.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from bridgeflow import memory
from bridgeflow.config import settings
from bridgeflow.identity import UserIdentity, require_user
from bridgeflow.security import consume_approval

router = APIRouter(tags=["memory"])


def _writes_allowed() -> None:
    if not settings.bridgeflow_allow_workflow_write:
        raise HTTPException(403, "Long-term memory writes disabled by deployment policy")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    department: str | None = None
    limit: int = Field(default=5, ge=1, le=10)


@router.post("/tools/memory-search")
async def search_tool(request: SearchRequest) -> dict:
    found = memory.search(request.query, department=request.department, limit=request.limit)
    items = [m.model_dump(mode="json", exclude={"status", "retired_reason"}) | {"score": score}
             for m, score in found]
    return {"query": request.query, "memories": items,
            "next_step": ("Name the memory id when you use one, say where its solution came from, and check it "
                          "still fits this case; a memory is a past decision, not a figure for this batch."
                          if items else
                          "No saved memory matches. Work the problem out from the tools; if the person settles "
                          "on a solution worth keeping, offer to save it.")}


class SaveRequest(memory.Content):
    memory_id: str | None = None
    expected_version: int | None = None
    note: str = Field(default="", max_length=200)
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/tools/memory-save")
async def save_tool(request: SaveRequest, http_request: Request) -> dict:
    _writes_allowed()
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""),
                             await http_request.body(), "memory_save")
    saved = memory.save(memory.Content(**request.model_dump(include=set(memory.Content.model_fields))),
                        actor=actor, memory_id=request.memory_id, expected_version=request.expected_version,
                        note=request.note)
    return saved.model_dump(mode="json") | {
        "next_step": f"Saved as {saved.id} v{saved.version}; later conversations find it with memory_search."}


class RetireRequest(BaseModel):
    memory_id: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=200)
    expected_version: int | None = None
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/tools/memory-retire")
async def retire_tool(request: RetireRequest, http_request: Request) -> dict:
    _writes_allowed()
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""),
                             await http_request.body(), "memory_retire")
    retired = memory.retire(request.memory_id, reason=request.reason,
                            expected_version=request.expected_version, actor=actor)
    return retired.model_dump(mode="json") | {
        "next_step": f"{retired.id} is retired and no longer found by search; its history stays readable."}


@router.get("/memories")
async def list_memories(user: Annotated[UserIdentity | None, Depends(require_user)],
                        include_retired: bool = False) -> dict:
    """Every memory for the browser, read-only. Changing one goes through the captain and approval."""
    items = memory.current(include_retired=include_retired)
    return {"memories": [m.model_dump(mode="json") for m in items],
            "active": sum(1 for m in items if m.status == "active")}
