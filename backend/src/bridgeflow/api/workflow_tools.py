"""The bodies behind the workflow tools a DSH agent calls (#144).

The same use cases as `/workflow/*`, shaped for a model and guarded for one:

- **Bounded, question-first returns.** A draft comes back as its state, the questions
  still open and the values of that one record; the board comes back as summaries,
  capped. Nothing grows with the size of the company's data.
- **The model cannot supply provenance.** Whatever it claims, a value it submits is
  recorded as coming from this conversation, identified by the tool call. Values read
  from files belong to extraction on the host side, not to the model's say-so.
- **Every write is a person's decision.** Recording what an employee said, and
  approving a draft for submission, each require a fresh DSH approval receipt bound
  to the exact request, like every other write in this service.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from bridgeflow.api.workflow import _domain_errors, _handoff, service
from bridgeflow.config import settings
from bridgeflow.security import consume_approval
from bridgeflow.workflow import board
from bridgeflow.workflow.intake import Observation, Source
from bridgeflow.workflow.service import ArtifactSnapshot

router = APIRouter(prefix="/tools", tags=["workflow-tools"])

MAX_BOARD_ROWS = 30
MAX_CANDIDATES = 4


class Said(BaseModel):
    """One thing the person said, as the model relays it."""

    label: str = Field(min_length=1, max_length=80)
    value: str = Field(max_length=200)
    evidence: str = Field("", max_length=120)


def _observations(said: list[Said], call_id: str | None) -> list[Observation]:
    source = Source(kind="reply", ref=f"dsh-call:{call_id or 'unknown'}")
    return [Observation(label=s.label, value=s.value, evidence=s.evidence, source=source) for s in said]


def _require_writes() -> None:
    if not settings.bridgeflow_allow_workflow_write:
        raise HTTPException(403, "Workflow writes disabled by deployment policy")


def _next_step(snapshot: ArtifactSnapshot) -> str:
    state = str(snapshot.view.state)
    return {
        "needs_input": "Ask the person the open questions, one field at a time; never fill a value in yourself.",
        "ready_for_review": "Show the person the values and checks, then call workflow_approve_submit if they confirm.",
        "reviewed": "Call workflow_approve_submit to submit the reviewed values.",
        "submitting": "Submission is in progress; calling workflow_approve_submit again resumes it safely.",
        "submit_failed": "The target system refused; say so plainly. The draft is kept and can be retried.",
        "data_ready": "Data is ready. Downstream is told only when every input it needs is ready; see workflow_board.",
    }.get(state, "")


def _draft(snapshot: ArtifactSnapshot) -> dict[str, Any]:
    fields = snapshot.spec.fields
    return {
        "artifact_id": snapshot.id, "template": snapshot.template, "title": snapshot.spec.title,
        "department": snapshot.spec.department, "state": str(snapshot.view.state),
        "version": snapshot.view.version, "seq": snapshot.seq, "digest": snapshot.draft.digest,
        "values": {fields[k].label: v.value + (f" ({fields[k].unit})" if fields[k].unit else "")
                   for k, v in snapshot.draft.values.items()},
        "open_questions": [
            {"kind": i.kind, "field": fields[i.field].label if i.field else "", "question": i.question,
             "why": i.message,
             "candidates": [{"value": c.value, "from": c.source.ref} for c in i.candidates[:MAX_CANDIDATES]]}
            for i in snapshot.draft.issues if i.blocking],
        "notices": [i.message for i in snapshot.draft.issues if not i.blocking][:10],
        "checks": [{"title": c.title, "value": c.value, "unit": c.unit, "attention": c.attention}
                   for c in snapshot.draft.checks],
        "next_step": _next_step(snapshot),
        # Omitted rather than null until the target system has accepted the record.
        **({"receipt": snapshot.view.receipt} if snapshot.view.receipt else {}),
    }


@router.post("/workflow-catalogue")
async def workflow_catalogue() -> dict[str, Any]:
    declared = service().catalogue
    return {
        "templates": [
            {"template": name, "title": t.title, "department": t.department, "status": str(t.status),
             "fields": [{"label": f.label, "required": f.required, "type": f.dtype, "unit": f.unit,
                         "needs_evidence": f.evidence_required} for f in t.fields.values()]}
            for name, t in declared.templates.items()],
        "stages": [{"stage": name, "title": s.title, "department": s.department, "owner_role": s.owner_role,
                    "inputs": list(s.inputs)} for name, s in declared.stages.items()],
    }


class DraftRef(BaseModel):
    artifact_id: str = Field(pattern=r"^[a-f0-9]{32}$")


@router.post("/workflow-draft")
async def workflow_draft(request: DraftRef) -> dict[str, Any]:
    workflow = service()
    with _domain_errors():
        return _draft(workflow.artifact(request.artifact_id))


@router.post("/workflow-board")
async def workflow_board() -> dict[str, Any]:
    workflow = service()
    with _domain_errors():
        rows = board.project(workflow).rows
    return {"total": len(rows), "truncated": len(rows) > MAX_BOARD_ROWS,
            "rows": [{"kind": r.kind, "summary": r.summary, "business_key": r.business_key,
                      **({"id": r.id, "state": r.state, "seq": r.seq} if hasattr(r, "id") else {}),
                      **({"stale": r.stale, "inputs": r.inputs, "notification": r.notification}
                         if isinstance(r, board.HandoffRow) else {})}
                     for r in rows[-MAX_BOARD_ROWS:]]}


class HandoffCall(BaseModel):
    handoff_id: str = Field(min_length=1, max_length=200)
    action: Literal["start", "return", "complete", "acknowledge"]
    expected_seq: int = Field(ge=1)
    reason: str = Field("", max_length=500)
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/workflow-handoff")
async def workflow_handoff(request: HandoffCall, http_request: Request) -> dict[str, Any]:
    _require_writes()
    workflow = service()
    consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body(), "workflow_handoff")
    with _domain_errors():
        return _handoff(workflow.act(request.handoff_id, request.action, request.reason,
                                     request.expected_seq)).model_dump()


class ReceiveCall(BaseModel):
    template: str
    said: list[Said] = Field(min_length=1, max_length=60)
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/workflow-receive")
async def workflow_receive(request: ReceiveCall, http_request: Request) -> dict[str, Any]:
    _require_writes()
    workflow = service()
    consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body(), "workflow_record")
    with _domain_errors():
        return _draft(workflow.receive(request.template, _observations(request.said, request.call_id)))


class AnswerCall(BaseModel):
    artifact_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    expected_seq: int
    said: list[Said] = Field(min_length=1, max_length=20)
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/workflow-answer")
async def workflow_answer(request: AnswerCall, http_request: Request) -> dict[str, Any]:
    _require_writes()
    workflow = service()
    consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body(), "workflow_record")
    with _domain_errors():
        return _draft(workflow.answer(request.artifact_id, _observations(request.said, request.call_id),
                                      request.expected_seq))


class ApproveCall(BaseModel):
    artifact_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_seq: int
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/workflow-approve-submit")
async def workflow_approve_submit(request: ApproveCall, http_request: Request) -> dict[str, Any]:
    """One human decision: these exact values are right, submit them.

    Resuming a submission that was interrupted needs no second review — the reviewed
    digest is already on record — so an artifact in `reviewed`, `submitting` or
    `submit_failed` goes straight to submit.
    """
    _require_writes()
    workflow = service()
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body(), "workflow_approve_submit")
    with _domain_errors():
        current = workflow.artifact(request.artifact_id)
        if str(current.view.state) == "ready_for_review":
            workflow.review(request.artifact_id, request.digest, actor, request.expected_seq)
        elif current.draft.digest != request.digest:
            raise HTTPException(409, "The values changed since they were shown; read the draft again")
        return _draft(workflow.submit(request.artifact_id))


class GuidanceCall(BaseModel):
    stage: str = Field(min_length=1, max_length=200)


@router.post("/workflow-guidance")
async def workflow_guidance(request: GuidanceCall) -> dict[str, Any]:
    from bridgeflow.workflow.guidance import for_stage

    declared = service().catalogue
    if request.stage not in declared.stages:
        raise HTTPException(404, "Stage is not declared")
    result = for_stage(declared, request.stage)
    for key in ("inputs", "outputs"):
        result[f"{key}_total"] = len(result[key])
        result[f"{key}_truncated"] = len(result[key]) > MAX_BOARD_ROWS
        result[key] = result[key][:MAX_BOARD_ROWS]
    return result
