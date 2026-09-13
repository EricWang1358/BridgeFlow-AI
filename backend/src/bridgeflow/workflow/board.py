"""The status board: one read model projected from events, never written to directly.

Each row says where a business object is, who it waits on, and what happens next, in
words built from the declarations (#144): "生产部材料已收到，待补实际量" rather than a
status code. It keeps the distinctions the lifecycle keeps — received is not ready,
ready is not notified, notified is not done — and a partial set of inputs is shown as
partial, never as "data ready".
"""

from __future__ import annotations

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
        summary = f"{spec.department}材料已收到，待补：{'、'.join(blocking)}"
    elif state is ArtifactState.READY_FOR_REVIEW:
        summary = f"{spec.department}标准记录已形成，待复核"
    elif state is ArtifactState.REVIEWED:
        summary = f"{spec.department}标准记录已复核，待提交"
    elif state is ArtifactState.SUBMITTING:
        summary, who = f"{spec.department}标准记录提交中", "system"
    elif state is ArtifactState.SUBMIT_FAILED:
        summary = f"{spec.department}标准记录提交失败，数据尚未就绪，可重试"
    else:
        summary, who = f"{spec.department}「{spec.title}」v{snapshot.view.version} 数据已就绪", ""
    if attention:
        summary += f"；需关注：{'、'.join(attention)}"
    return ArtifactRow(id=snapshot.id, template=snapshot.template, title=spec.title, department=spec.department,
                       business_key=list(snapshot.key), version=snapshot.view.version, state=str(state),
                       waiting_on=who, summary=summary, blocking=blocking, attention=attention,
                       seq=snapshot.seq, updated_at=snapshot.updated_at)


def _handoff_row(service: WorkflowService, snapshot: HandoffSnapshot, notices: dict[str, NotificationState]) -> HandoffRow:
    stage = service.catalogue.stages[snapshot.stage]
    upstream = "、".join(service.catalogue.templates[t].department for t in snapshot.view.inputs)
    notification = notices.get(f"handoff:{snapshot.id}")
    state = snapshot.view.state
    if state is HandoffState.WAITING:
        summary = f"{upstream}标准数据已就绪，待{stage.department}处理"
    elif state is HandoffState.IN_PROGRESS:
        summary = f"{stage.department}处理中"
    elif state is HandoffState.RETURNED:
        summary = f"{stage.department}已退回：{snapshot.view.reason}"
    else:
        summary = f"{stage.department}已完成"
    if snapshot.view.stale:
        summary += "；上游已修订，请按新版本复核"
    if notification in (NotificationState.FAILED, NotificationState.ABANDONED):
        summary += "；通知发送失败" + ("，待重试" if notification is NotificationState.FAILED else "，需人工跟进")
    return HandoffRow(id=snapshot.id, stage=snapshot.stage, title=stage.title, department=stage.department,
                      owner_role=stage.owner_role, business_key=list(snapshot.key), inputs=snapshot.view.inputs,
                      state=str(state), stale=snapshot.view.stale,
                      notification=str(notification) if notification else "none",
                      summary=summary, seq=snapshot.seq, updated_at=snapshot.updated_at)


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
                summary=f"{stage.department}已收到部分输入，仍待："
                        + "、".join(f"{titles[t].department}「{titles[t].title}」" for t in awaiting)))
    return Board(rows=rows)
