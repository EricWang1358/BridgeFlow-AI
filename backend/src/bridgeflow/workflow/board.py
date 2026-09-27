"""The status board: one read model projected from events, never written to directly.

Each row says where a business object is, who it waits on, and what happens next, in
words built from the declarations (#144): "Production material received, still missing:
Actual volume" rather than a status code. Like every sentence the backend writes, it is
English, with a clause per fact joined by "; "; the Chinese interface reads it in Chinese
(plugins/src/client/zh-messages.ts), and the declared names stay as the catalogue wrote them. It keeps the distinctions the lifecycle keeps — received is not ready,
ready is not notified, notified is not done — and a partial set of inputs is shown as
partial, never as "data ready".
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from bridgeflow.workflow.lifecycle import ArtifactState, HandoffState, NotificationState
from bridgeflow.workflow.service import ArtifactSnapshot, HandoffSnapshot, WorkflowService


class ArtifactRow(BaseModel):
    kind: str = "artifact"
    id: str
    template: str
    title: str
    department: str
    business_key: list[str]
    version: int
    state: str
    waiting_on: str
    summary: str
    blocking: list[str] = Field(default_factory=list)
    attention: list[str] = Field(default_factory=list)
    seq: int
    updated_at: str


class HandoffRow(BaseModel):
    kind: str = "handoff"
    id: str
    stage: str
    title: str
    department: str
    owner_role: str
    business_key: list[str]
    inputs: dict[str, int]
    state: str
    stale: bool
    notification: str
    summary: str
    seq: int
    updated_at: str
    #: Templates this stage produces that are not recorded yet for the key; it cannot complete until they are.
    awaiting_outputs: list[str] = []
    #: When the handoff opened, and — if its stage declares a time limit — when it is due and
    #: by how many hours it is late (negative: hours left). Unfinished work only; nothing is flagged without an
    #: agreed limit (the same rule the adoption signal uses).
    opened_at: str = ""
    due_at: str = ""
    overdue_hours: float | None = None


class PartialRow(BaseModel):
    kind: str = "partial"
    stage: str
    title: str
    department: str
    business_key: list[str]
    received: list[str]
    awaiting: list[str]
    summary: str


class Board(BaseModel):
    rows: list[ArtifactRow | HandoffRow | PartialRow]


def _artifact_row(snapshot: ArtifactSnapshot) -> ArtifactRow:
    spec = snapshot.spec
    blocking = [spec.fields[i.field].label for i in snapshot.draft.issues if i.blocking and i.field]
    attention = [c.title for c in snapshot.draft.checks if c.attention]
    state = snapshot.view.state
    who = spec.department
    if state is ArtifactState.NEEDS_INPUT:
        summary = f"{spec.department} material received, still missing: {', '.join(blocking)}"
    elif state is ArtifactState.READY_FOR_REVIEW:
        summary = f"{spec.department} standard record ready for review"
    elif state is ArtifactState.REVIEWED:
        summary = f"{spec.department} standard record reviewed, awaiting submission"
    elif state is ArtifactState.SUBMITTING:
        summary, who = f"{spec.department} standard record being submitted", "system"
    elif state is ArtifactState.SUBMIT_FAILED:
        summary = f"{spec.department} standard record failed to submit, data not ready yet, can retry"
    else:
        summary, who = f'{spec.department} "{spec.title}" v{snapshot.view.version} data ready', ""
    if attention:
        summary += f"; needs attention: {', '.join(attention)}"
    return ArtifactRow(id=snapshot.id, template=snapshot.template, title=spec.title, department=spec.department,
                       business_key=list(snapshot.key), version=snapshot.view.version, state=str(state),
                       waiting_on=who, summary=summary, blocking=blocking, attention=attention,
                       seq=snapshot.seq, updated_at=snapshot.updated_at)


def _handoff_row(service: WorkflowService, snapshot: HandoffSnapshot, notices: dict[str, NotificationState]) -> HandoffRow:
    stage = service.catalogue.stages[snapshot.stage]
    upstream = ", ".join(service.catalogue.templates[t].department for t in snapshot.view.inputs)
    notification = notices.get(f"handoff:{snapshot.id}")
    state = snapshot.view.state
    if state is HandoffState.WAITING:
        summary = f"{upstream} standard data ready, waiting on {stage.department}"
    elif state is HandoffState.IN_PROGRESS:
        summary = f"{stage.department} working on it"
    elif state is HandoffState.RETURNED:
        summary = f"{stage.department} returned it: {snapshot.view.reason}"
    else:
        summary = f"{stage.department} done"
    owed = service.missing_outputs(snapshot.stage, snapshot.key) if state in (HandoffState.WAITING, HandoffState.IN_PROGRESS) else []
    if owed:
        templates = service.catalogue.templates
        summary += "; can finish once recorded: " + ", ".join(f'{templates[t].department} "{templates[t].title}"'
                                                              for t in owed)
    if snapshot.view.stale:
        summary += "; upstream was revised, review against the new version"
    if notification in (NotificationState.FAILED, NotificationState.ABANDONED):
        summary += "; notification failed, " + ("will retry" if notification is NotificationState.FAILED
                                                else "needs manual follow-up")
    return HandoffRow(id=snapshot.id, stage=snapshot.stage, title=stage.title, department=stage.department,
                      owner_role=stage.owner_role, business_key=list(snapshot.key), inputs=snapshot.view.inputs,
                      state=str(state), stale=snapshot.view.stale,
                      notification=str(notification) if notification else "none",
                      summary=summary, seq=snapshot.seq, updated_at=snapshot.updated_at, awaiting_outputs=owed,
                      **_timing(service, snapshot, stage))


def _timing(service: WorkflowService, snapshot: HandoffSnapshot, stage) -> dict:
    opened = snapshot.events[0].at if snapshot.events else ""
    if not opened or stage.sla_hours is None:
        return {"opened_at": opened}
    due = datetime.fromisoformat(opened) + timedelta(hours=stage.sla_hours)
    late = None
    if snapshot.view.state in (HandoffState.WAITING, HandoffState.IN_PROGRESS, HandoffState.RETURNED):
        late = round((service.clock() - due).total_seconds() / 3600, 1)
    return {"opened_at": opened, "due_at": due.isoformat(), "overdue_hours": late}


def project(service: WorkflowService) -> Board:
    artifacts = service.artifacts()
    handoffs = service.handoffs()
    # The newest attempt per stream decides what the board says about notification.
    notices: dict[str, NotificationState] = {}
    for notice in service.store.notifications():
        notices[notice.stream] = notice.state

    rows: list[ArtifactRow | HandoffRow | PartialRow] = [_artifact_row(a) for a in artifacts]
    rows += [_handoff_row(service, h, notices) for h in handoffs]

    opened = {(h.stage, h.key) for h in handoffs}
    ready = {(a.template, a.key) for a in artifacts if a.view.state is ArtifactState.DATA_READY}
    for name, stage in service.catalogue.stages.items():
        if not stage.inputs:
            continue
        for key in sorted({k for (_, k) in ready}):
            received = [t for t in stage.inputs if (t, key) in ready]
            if not received or len(received) == len(stage.inputs) or (name, key) in opened:
                continue
            awaiting = [t for t in stage.inputs if t not in received]
            titles = service.catalogue.templates
            rows.append(PartialRow(
                stage=name, title=stage.title, department=stage.department, business_key=list(key),
                received=received, awaiting=awaiting,
                summary=f"{stage.department} has part of its inputs, still waiting on: "
                        + ", ".join(f'{titles[t].department} "{titles[t].title}"' for t in awaiting)))
    return Board(rows=rows)
