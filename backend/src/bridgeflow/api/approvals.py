"""The two ends of one decision: the answerer asks here, the operator answers here.

`plugins/src/approval/operator-answerer.ts` is a `approval/request` listener inside
the dsh runtime. It publishes the pending question through `POST /approvals/ask`,
waits on `GET /approvals/{id}`, and withdraws with `DELETE /approvals/{id}` if it
gives up. The console at `GET /console` is what a person looks at.

Route order matters: `/approvals/log` is declared before `/approvals/{question_id}`,
or FastAPI would match the literal path as an id.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from bridgeflow import approvals

router = APIRouter(tags=["approvals"])

#: Longest a single wait call may block. Bounded so a client that dies mid-wait
#: releases the connection, and so the answerer re-checks its own deadline and its
#: abort signal regularly rather than sleeping through both.
MAX_WAIT_SECONDS = 30.0


class AskRequest(BaseModel):
    tool_name: str
    call_id: str | None = None
    reason: str = ""
    detail: list[approvals.ApprovalDetail] = Field(default_factory=list)


class DecideRequest(BaseModel):
    outcome: approvals.ApprovalOutcome
    by: str = ""
    #: Optional, and only meaningful with a rejection: the reason handed back to the
    #: agent. A denial with no stated reason is the one #86 narrates as "done".
    note: str = ""


# --- the answerer's side ------------------------------------------------------


@router.post("/approvals/ask", response_model=approvals.ApprovalQuestion)
async def ask(request: AskRequest) -> approvals.ApprovalQuestion:
    """Publish one pending decision. 409 when the queue is full, which denies."""
    try:
        return approvals.queue.ask(
            tool_name=request.tool_name,
            call_id=request.call_id,
            reason=request.reason,
            detail=request.detail,
        )
    except approvals.QueueFull as exc:
        raise HTTPException(409, str(exc)) from exc


@router.delete("/approvals/{question_id}", response_model=approvals.ApprovalQuestion)
async def release(question_id: str) -> approvals.ApprovalQuestion:
    """The caller is done — the question leaves the console whether or not it was answered."""
    try:
        return approvals.queue.release(question_id)
    except approvals.UnknownQuestion as exc:
        raise HTTPException(404, f"no approval {question_id}") from exc


# --- the operator's side ------------------------------------------------------


@router.get("/approvals", response_model=list[approvals.ApprovalQuestion])
async def pending() -> list[approvals.ApprovalQuestion]:
    """What is waiting on a person right now, oldest first."""
    return approvals.queue.pending()


@router.get("/approvals/log", response_model=list[approvals.ApprovalQuestion])
async def decision_log() -> list[approvals.ApprovalQuestion]:
    """Every decision on file — who allowed what, and when."""
    return approvals.read_log()


@router.get("/approvals/{question_id}", response_model=approvals.ApprovalQuestion)
async def poll(question_id: str, wait_ms: int = 0) -> approvals.ApprovalQuestion:
    """Read one question, optionally waiting up to `wait_ms` for it to be decided.

    Returning on timeout is deliberate: the answerer, not this endpoint, owns the
    decision to give up, and giving up must withdraw rather than proceed.
    """
    try:
        return await approvals.queue.wait(question_id, min(max(wait_ms, 0) / 1000, MAX_WAIT_SECONDS))
    except approvals.UnknownQuestion as exc:
        raise HTTPException(404, f"no approval {question_id}") from exc


@router.post("/approvals/{question_id}/decide", response_model=approvals.ApprovalQuestion)
async def decide(question_id: str, request: DecideRequest) -> approvals.ApprovalQuestion:
    """Record a person's decision. The only path in the system that produces a grant."""
    try:
        return approvals.queue.decide(
            question_id, outcome=request.outcome, by=request.by, note=request.note
        )
    except approvals.UnknownQuestion as exc:
        raise HTTPException(404, f"no approval {question_id}") from exc
    except approvals.AlreadySettled as exc:
        raise HTTPException(409, str(exc)) from exc


# --- the console --------------------------------------------------------------

CONSOLE = Path(__file__).parent / "console.html"


@router.get("/console", response_class=HTMLResponse)
async def console() -> HTMLResponse:
    """The page an operator keeps open during a run.

    Served from the backend rather than built as a separate app because it has to
    reach `127.0.0.1:8000` while a tool call is blocked on it: a page hosted anywhere
    else could not, and a decision that arrives after the call gave up is worse than
    no decision at all.
    """
    return HTMLResponse(CONSOLE.read_text(encoding="utf-8"))
