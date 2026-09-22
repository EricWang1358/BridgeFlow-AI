"""Tool bodies for the dictionary draft lifecycle (#205, E05-UC07/UC08).

Draft → decide entry by entry → publish as a new version. Every write spends a fresh
DSH approval (`dictionary_draft` for drafting and deciding, `dictionary_publish` for
publishing), and the publish path re-runs the import side's own validation so a
version can never ship a guaranteed `needs_configuration`. Reads stay free.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from bridgeflow import dictionary_draft, feishu, profiling
from bridgeflow.agents.dictionary_drafter import DictionaryDraftAgent
from bridgeflow.api.batches import _declared_entities, load_batch
from bridgeflow.api.feishu_tools import _client
from bridgeflow.config import settings
from bridgeflow.dictionary_draft import DictionaryPublishError
from bridgeflow.metrics import dictionary_path
from bridgeflow.security import consume_approval

router = APIRouter(prefix="/tools", tags=["dictionary"])

Decision = Literal["accepted", "modified", "rejected"]


class DraftResult(BaseModel):
    """What the person needs to steer the review; the entries live in the view."""

    draft_id: str
    source: str
    basis: str
    departments: list[str]
    missing_departments: list[str]
    entries: int
    pending: int
    unmapped: int
    notes: list[str]
    model_call: dictionary_draft.ModelCall | None = None
    next_step: str


class DecideRequest(BaseModel):
    draft_id: str
    entry_id: str
    decision: Decision
    reason: str = Field("", max_length=500)
    #: For `modified`: replacement column / role; for measures, the rollup to record.
    column: str = ""
    role: str = ""
    rollup: Literal["", "sum", "average", "period_end"] = ""
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


class DecideResult(BaseModel):
    entry_id: str
    decision: str
    decided_by: str
    pending: int
    next_step: str


class PublishResult(BaseModel):
    draft_id: str
    version: str
    dictionary: str
    next_step: str


def _result(draft: dictionary_draft.Draft, next_step: str) -> DraftResult:
    covered = sorted({entry.department for entry in draft.entries})
    return DraftResult(
        draft_id=draft.draft_id, source=draft.source, basis=draft.basis,
        departments=covered, missing_departments=sorted(set(dictionary_draft.DEPARTMENT_LABELS) - set(covered)),
        entries=len(draft.entries), pending=len(draft.pending), unmapped=len(draft.unmapped),
        notes=draft.notes, model_call=draft.model_call, next_step=next_step,
    )


def _load_or_404(draft_id: str) -> dictionary_draft.Draft:
    try:
        return dictionary_draft.load(draft_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, "Draft not found") from exc


class BatchProfileRequest(BaseModel):
    batch_id: str


@router.post("/dictionary-profiles", response_model=profiling.BatchProfile,
             response_model_exclude_none=True)
async def dictionary_profiles(request: BatchProfileRequest) -> profiling.BatchProfile:
    """Per-department column statistics for the batch: type, fill rate, uniqueness,
    cross-department overlap. No cell contents — the drafting input, by construction."""
    batch = load_batch(request.batch_id)
    return profiling.profile(request.batch_id, batch.period, batch.clean_tables,
                             declared=_declared_entities(batch.dictionary_snapshot))


class ImportRequest(BaseModel):
    file_token: str
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/dictionary-import", response_model=DraftResult)
async def dictionary_import(request: ImportRequest, http_request: Request) -> DraftResult:
    """Transcribe the business's OA dictionary spreadsheet (a Feishu file token) into a draft.

    Deterministic and free: no model runs. What the format cannot state — the report
    period, a measure's rollup — stays undecided for the person, never guessed.
    """
    _require_mapping_write()
    drive = _client()
    try:
        name, payload = await drive.download(request.file_token)
    except feishu.FeishuError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        await drive.close()
    # Parse before the approval is spent: a malformed spreadsheet must cost the
    # person a corrected file, not a fresh approval.
    try:
        entries, unmapped, notes, covered = dictionary_draft.parse_oa_bytes(payload, name)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not entries:
        raise HTTPException(422, f"{name} produced no declarable entries; {notes or 'check the format'}")
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""),
                             await http_request.body(), "dictionary_draft")
    draft = dictionary_draft.new_draft(
        source="import", created_by=actor, basis=name, entries=entries, unmapped=unmapped, notes=notes)
    return _result(draft, (
        f"Transcribed {len(entries)} entries from {name}. Decide every entry (a measure needs its "
        "rollup named), then publish — publishing writes a new dictionary version that only "
        "affects later imports."))


class DraftRequest(BaseModel):
    batch_id: str
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/dictionary-draft", response_model=DraftResult)
async def dictionary_draft_from_batch(request: DraftRequest, http_request: Request) -> DraftResult:
    """Propose declarations from one batch's column statistics: the model drafts,
    the host filters, nothing is decided. A billed call, recorded either way."""
    _require_mapping_write()
    batch = load_batch(request.batch_id)
    if not batch.clean_tables:
        raise HTTPException(422, "This batch has no cleaned tables to profile")
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""),
                             await http_request.body(), "dictionary_draft")
    profile = profiling.profile(request.batch_id, batch.period, batch.clean_tables,
                                declared=_declared_entities(batch.dictionary_snapshot))
    agent = DictionaryDraftAgent()
    started = datetime.now(UTC).isoformat()
    proposal = await agent.run(profile)
    model_call = dictionary_draft.ModelCall(
        provider=agent.llm.name, model=getattr(agent.llm, "model", "") or agent.llm.name,
        started_at=started, finished_at=datetime.now(UTC).isoformat(),
    )
    departments = {table.department: [spec.name for spec in table.columns]
                   for table in batch.clean_tables}
    entries, dropped = dictionary_draft.admit_proposals(
        [entry.model_dump() for entry in proposal.entries], departments)
    notes = [*proposal.notes, *(f"Dropped: {reason}" for reason in dropped)]
    if not entries:
        notes.append("No entry survived the host's evidence check; nothing was drafted.")
    draft = dictionary_draft.new_draft(
        source="model", created_by=actor, basis=f"batch {request.batch_id} column profiles",
        batch_id=request.batch_id, entries=entries, notes=notes, model_call=model_call)
    return _result(draft, (
        f"Drafted {len(entries)} entr(ies) from this batch's column statistics "
        f"({model_call.provider}). Decide every entry, then publish — publishing only "
        "affects later imports."))


class ViewRequest(BaseModel):
    draft_id: str


@router.post("/dictionary-draft-view", response_model=dictionary_draft.Draft)
async def dictionary_draft_view(request: ViewRequest) -> dictionary_draft.Draft:
    """The draft with every entry, its evidence and its decision, for the review."""
    return _load_or_404(request.draft_id)


@router.post("/dictionary-draft-decide", response_model=DecideResult)
async def dictionary_draft_decide(request: DecideRequest, http_request: Request) -> DecideResult:
    """One person's decision on one entry: accept it, modify it (the replacement wins),
    or reject it with a reason. A measure needs its rollup before it can be decided."""
    _require_mapping_write()
    draft = _load_or_404(request.draft_id)
    # Validate before the approval is spent; a refused decision costs a correction.
    try:
        dictionary_draft.check_decision(
            draft, request.entry_id, request.decision,
            column=request.column, role=request.role, rollup=request.rollup)
    except KeyError as exc:
        raise HTTPException(404, "Entry not found in this draft") from exc
    except DictionaryPublishError as exc:
        raise HTTPException(409, str(exc)) from exc
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""),
                             await http_request.body(), "dictionary_draft")
    draft = dictionary_draft.decide(
        draft, request.entry_id, request.decision, by=actor, reason=request.reason,
        column=request.column, role=request.role, rollup=request.rollup)
    pending = len(draft.pending)
    if pending:
        step = f"{pending} entry(ies) still undecided."
    elif draft.published:
        step = "Already published; draft a new one for further changes."
    else:
        step = "Every entry has a decision. Publish to write the new dictionary version."
    return DecideResult(entry_id=request.entry_id, decision=request.decision,
                        decided_by=actor, pending=pending, next_step=step)


class PublishRequest(BaseModel):
    draft_id: str
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/dictionary-draft-publish", response_model=PublishResult)
async def dictionary_draft_publish(request: PublishRequest, http_request: Request) -> PublishResult:
    """Write the decided draft as a new dictionary version and point the active file at it.

    Refused — writing nothing — when entries remain undecided, the merged dictionary
    fails the import side's own validation, or the dictionary moved since the draft.
    """
    _require_mapping_write()
    draft = _load_or_404(request.draft_id)
    # Validate before the approval is spent: `dictionary_publish` is the widest grant
    # in the system — it must never be burned on a draft that could not ship.
    try:
        dictionary_draft.check_publish(draft)
    except DictionaryPublishError as exc:
        raise HTTPException(409, str(exc)) from exc
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""),
                             await http_request.body(), "dictionary_publish")
    try:
        dictionary_draft.publish(draft, by=actor)
    except DictionaryPublishError as exc:
        raise HTTPException(409, str(exc)) from exc
    return PublishResult(
        draft_id=draft.draft_id, version=draft.published_version,
        dictionary=str(dictionary_path()),
        next_step=("Published. Import the files again — this and every earlier batch keep the "
                   "dictionary they were frozen against."),
    )


def _require_mapping_write() -> None:
    if not settings.bridgeflow_allow_mapping_write:
        raise HTTPException(403, "Mapping writes disabled by deployment policy")
