"""HTTP surface of the workflow foundation (#143–#145).

Thin by design: parse, call one use case in `workflow.service`, render. Domain errors
map to status codes in exactly one place, so a refusal reads the same wherever it
comes from. Reviewing a draft is the human decision in this flow and, like every
other write a person approves, requires a fresh DSH approval receipt bound to the
exact request.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from bridgeflow.config import settings
from bridgeflow.identity import UserIdentity, require_user
from bridgeflow.security import consume_approval
from bridgeflow.store import _root
from bridgeflow.workflow import adoption, board, catalogue, materials
from bridgeflow.workflow.intake import Observation
from bridgeflow.workflow.lifecycle import TransitionError
from bridgeflow.workflow.ports import notifier_for, sink_for
from bridgeflow.workflow.service import (
    ArtifactSnapshot,
    HandoffSnapshot,
    NotFound,
    StaleRead,
    WorkflowService,
)
from bridgeflow.workflow.store import ConcurrencyError, WorkflowStore
from bridgeflow.workflow.visibility import Visibility

BrowserUser = Annotated[UserIdentity | None, Depends(require_user)]

router = APIRouter(prefix="/workflow", tags=["workflow"])


@contextmanager
def _domain_errors() -> Iterator[None]:
    try:
        yield
    except NotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except catalogue.CatalogueError as exc:
        raise HTTPException(503 if "not configured" in str(exc) else 409, str(exc)) from exc
    except (TransitionError, StaleRead, ConcurrencyError) as exc:
        raise HTTPException(409, str(exc)) from exc
    except materials.MaterialError as exc:
        raise HTTPException(422, str(exc)) from exc


def service() -> WorkflowService:
    with _domain_errors():
        declared = catalogue.load()
    root = _root()
    return WorkflowService(declared, WorkflowStore(root / "workflow.sqlite3"),
                           sink_for(declared.sink, root), notifier_for(declared.notifier, root))


# --- views ---------------------------------------------------------------------------


class ArtifactOut(BaseModel):
    id: str
    template: str
    title: str
    department: str
    state: str
    version: int
    seq: int
    digest: str
    business_key: list[str]
    values: dict[str, dict[str, Any]]
    derived: dict[str, str]
    checks: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    receipt: dict[str, Any] | None
    question_rounds: int
    updated_at: str


def _artifact(snapshot: ArtifactSnapshot) -> ArtifactOut:
    fields = snapshot.spec.fields
    return ArtifactOut(
        id=snapshot.id, template=snapshot.template, title=snapshot.spec.title, department=snapshot.spec.department,
        state=str(snapshot.view.state), version=snapshot.view.version, seq=snapshot.seq,
        digest=snapshot.draft.digest, business_key=list(snapshot.key),
        values={k: {"label": fields[k].label, **v.model_dump()} for k, v in snapshot.draft.values.items()},
        derived=snapshot.draft.derived, checks=[c.model_dump() for c in snapshot.draft.checks],
        issues=[{**i.model_dump(), "label": fields[i.field].label if i.field else "", "blocking": i.blocking}
                for i in snapshot.draft.issues],
        receipt=snapshot.view.receipt, question_rounds=snapshot.view.question_rounds, updated_at=snapshot.updated_at)


class HandoffOut(BaseModel):
    id: str
    stage: str
    business_key: list[str]
    state: str
    inputs: dict[str, int]
    stale: bool
    reason: str
    seq: int
    updated_at: str


def _handoff(snapshot: HandoffSnapshot) -> HandoffOut:
    return HandoffOut(id=snapshot.id, stage=snapshot.stage, business_key=list(snapshot.key),
                      state=str(snapshot.view.state), inputs=snapshot.view.inputs, stale=snapshot.view.stale,
                      reason=snapshot.view.reason, seq=snapshot.seq, updated_at=snapshot.updated_at)


# --- declarations (Agent 1) ------------------------------------------------------------


@router.get("/catalogue")
async def get_catalogue(user: BrowserUser) -> dict[str, Any]:
    declared = service().catalogue
    visible = Visibility(declared, user)
    return {
        "version": declared.version, "status": declared.status,
        "case": declared.case if visible.all() else "",
        "mvp": declared.mvp.model_dump() if visible.all() else {"status": "restricted"},
        "templates": {name: {"title": t.title, "department": t.department, "version": t.version, "status": t.status,
                             "business_key": list(t.business_key),
                             "fields": {k: f.model_dump(include={"label", "definition", "dtype", "required", "unit"})
                                        for k, f in t.fields.items()}}
                      for name, t in declared.templates.items() if visible.template(name)},
        "stages": {name: s.model_dump() for name, s in declared.stages.items() if visible.stage(name)},
        "lineage": [e.model_dump() for e in declared.lineage
                    if visible.template(e.source.partition(".")[0])
                    and visible.template(e.target.partition(".")[0])],
        "integrations": {"sink": declared.sink.kind, "notifier": declared.notifier.kind},
    }


@router.get("/lineage/{template}/{field}")
async def get_lineage(template: str, field: str, user: BrowserUser) -> dict[str, Any]:
    declared = service().catalogue
    visible = Visibility(declared, user)
    if not visible.template(template):
        raise HTTPException(404, "Field is not declared")
    spec = declared.templates.get(template)
    if spec is None or (field not in spec.fields and field not in spec.derived):
        raise HTTPException(404, "Field is not declared")
    trace = declared.lineage_of(template, field)
    return {"field": f"{template}.{field}", **{k: [e.model_dump() for e in v
            if visible.template(e.source.partition(".")[0])
            and visible.template(e.target.partition(".")[0])] for k, v in trace.items()}}


@router.post("/materials/inspect", response_model=materials.MaterialShape)
async def inspect_material(file: Annotated[UploadFile, File()]) -> materials.MaterialShape:
    payload = await file.read(settings.bridgeflow_max_upload_bytes + 1)
    if len(payload) > settings.bridgeflow_max_upload_bytes:
        raise HTTPException(413, "File exceeds configured upload size limit")
    with _domain_errors():
        return materials.inspect((file.filename or "").rsplit("/", 1)[-1], payload)


# --- intake and lifecycle (Agent 2) ----------------------------------------------------


class ReceiveRequest(BaseModel):
    template: str
    observations: list[Observation] = Field(max_length=500)


class AnswerRequest(BaseModel):
    observations: list[Observation] = Field(min_length=1, max_length=100)
    expected_seq: int


class ReviewRequest(BaseModel):
    digest: str
    expected_seq: int
    reviewer: str = "dsh-authenticated-session"


class HandoffAction(BaseModel):
    reason: str = Field("", max_length=500)
    expected_seq: int


@router.post("/artifacts", response_model=ArtifactOut, status_code=201)
async def receive(request: ReceiveRequest) -> ArtifactOut:
    workflow = service()
    with _domain_errors():
        return _artifact(workflow.receive(request.template, request.observations))


@router.get("/artifacts/{artifact_id}", response_model=ArtifactOut)
async def get_artifact(artifact_id: str, user: BrowserUser) -> ArtifactOut:
    workflow = service()
    with _domain_errors():
        snapshot = workflow.artifact(artifact_id)
        if not Visibility(workflow.catalogue, user).template(snapshot.template):
            raise HTTPException(404, "Artifact not found")
        return _artifact(snapshot)


@router.post("/artifacts/{artifact_id}/answers", response_model=ArtifactOut)
async def answer(artifact_id: str, request: AnswerRequest) -> ArtifactOut:
    workflow = service()
    with _domain_errors():
        return _artifact(workflow.answer(artifact_id, request.observations, request.expected_seq))


@router.post("/artifacts/{artifact_id}/review", response_model=ArtifactOut)
async def review(artifact_id: str, request: ReviewRequest, http_request: Request) -> ArtifactOut:
    workflow = service()
    consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body())
    with _domain_errors():
        return _artifact(workflow.review(artifact_id, request.digest, request.reviewer, request.expected_seq))


@router.post("/artifacts/{artifact_id}/submit", response_model=ArtifactOut)
async def submit(artifact_id: str) -> ArtifactOut:
    workflow = service()
    with _domain_errors():
        return _artifact(workflow.submit(artifact_id))


@router.post("/handoffs/{handoff_id}/{action}", response_model=HandoffOut)
async def act(handoff_id: str, action: str, request: HandoffAction) -> HandoffOut:
    workflow = service()
    with _domain_errors():
        return _handoff(workflow.act(handoff_id, action, request.reason, request.expected_seq))


@router.post("/notifications/dispatch")
async def dispatch() -> dict[str, Any]:
    workflow = service()
    with _domain_errors():
        sent = workflow.dispatch()
    return {"channel": workflow.notifier.name,
            "notifications": [{"id": n.id, "stream": n.stream, "recipient_role": n.recipient_role,
                               "state": n.state, "attempts": n.attempts, "last_error": n.last_error}
                              for n in sent]}


@router.get("/board", response_model=board.Board)
async def get_board(user: BrowserUser) -> board.Board:
    workflow = service()
    with _domain_errors():
        visible = Visibility(workflow.catalogue, user)
        result = board.project(workflow)
        return board.Board(rows=[r for r in result.rows
            if (visible.template(r.template) if isinstance(r, board.ArtifactRow)
                else visible.stage(r.stage))])


# --- adoption (Agent 3) ----------------------------------------------------------------


@router.get("/adoption", response_model=list[adoption.Finding])
async def get_adoption(user: BrowserUser) -> list[adoption.Finding]:
    workflow = service()
    with _domain_errors():
        visible = Visibility(workflow.catalogue, user)
        return [f for f in adoption.assess(workflow)
                if (visible.stage(f.scope["stage"]) if "stage" in f.scope
                    else visible.department(f.scope["department"]) if "department" in f.scope
                    else visible.all())]
