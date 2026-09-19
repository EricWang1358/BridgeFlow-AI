"""Confirming or replacing a convention the business side has not signed off (E13-UC05).

Three surfaces, by who may see what:

- `GET /conventions/batches/{id}` — the authenticated browser: every declared convention, its
  state, and (for a requested replacement) the declaration change a dictionary owner must apply.
- `POST /tools/convention-*` — the captain: the same list and a dry-run impact, but counts and
  field names only, never the cells that would change.
- `POST /tools/convention-decide` — a write, so it needs a DSH approval receipt and names the
  approver as the decider. A decision without a source is refused.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from bridgeflow import integration as integration_module
from bridgeflow.api.batches import BatchRef, _visible, load_batch
from bridgeflow.api.integration import sheets_of
from bridgeflow.conclusions import conventions
from bridgeflow.config import settings
from bridgeflow.identity import UserIdentity, require_user
from bridgeflow.security import consume_approval

router = APIRouter(tags=["conventions"])


def _spec_of(batch_id: str, user: UserIdentity | None = None) -> tuple[dict, object]:
    batch = _visible(load_batch(batch_id), user) if user is not None else load_batch(batch_id)
    if batch.integration_snapshot is None:
        raise HTTPException(409, "Batch has no frozen integration declaration; import a new batch")
    return batch.integration_snapshot, batch


def _writes_allowed() -> None:
    if not settings.bridgeflow_allow_mapping_write:
        raise HTTPException(403, "Convention decisions disabled by deployment policy")


@router.get("/conventions/batches/{batch_id}")
async def list_for_batch(batch_id: str,
                         user: Annotated[UserIdentity | None, Depends(require_user)]) -> dict:
    spec, _batch = _spec_of(batch_id, user)
    views = conventions.views(spec)
    return {"batch_id": batch_id, "declaration": spec.get("version", ""),
            "conventions": [view.model_dump(mode="json") for view in views],
            "unconfirmed": sum(1 for view in views if view.state == "unconfirmed")}


@router.post("/tools/convention-list")
async def convention_list(request: BatchRef) -> dict:
    """Declaration text and decision states. No sheet data."""
    spec, _batch = _spec_of(request.batch_id)
    views = conventions.views(spec)
    return {"batch_id": request.batch_id,
            "conventions": [view.model_dump(mode="json", exclude={"affected_fields"}) |
                            {"affected_field_count": len(view.affected_fields)} for view in views],
            "next_step": ("Say which figures rest on an unconfirmed convention and who must decide. "
                          "A decision needs the source it comes from; confirming raises the evidence "
                          "grade, replacing a formula or rule means the dictionary owner edits the declaration.")}


class PreviewRequest(BaseModel):
    batch_id: str
    convention: str
    requested_value: str


@router.post("/tools/convention-preview")
async def convention_preview(request: PreviewRequest) -> dict:
    """What a replaced constant would change in this batch. Read-only, and counts only."""
    spec, batch = _spec_of(request.batch_id)
    result = conventions.preview(spec, batch, request.convention, request.requested_value,
                                 integration_module.integrate,
                                 lambda b: sheets_of(request.batch_id, b))
    return {k: v for k, v in result.items() if k != "sample"} | {
        "next_step": "This batch stays frozen either way; applying the value means editing the declaration and importing again."}


@router.get("/conventions/batches/{batch_id}/preview")
async def preview_for_browser(batch_id: str, convention: str, requested_value: str,
                              user: Annotated[UserIdentity | None, Depends(require_user)]) -> dict:
    """The same dry run with its changed cells, for the person who may already see the rows."""
    spec, batch = _spec_of(batch_id, user)
    return conventions.preview(spec, batch, convention, requested_value,
                               integration_module.integrate, lambda b: sheets_of(batch_id, b))


class DecideRequest(BaseModel):
    batch_id: str
    convention: str
    action: Literal["confirm", "replace"]
    source: str = Field(min_length=1, max_length=400)
    note: str = Field(default="", max_length=400)
    requested_value: str = ""
    #: The version the decider read. Omitted only for a first decision; a mismatch is a conflict.
    expected_version: int | None = None
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/tools/convention-decide")
async def convention_decide(request: DecideRequest, http_request: Request) -> dict:
    _writes_allowed()
    spec, _batch = _spec_of(request.batch_id)
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""),
                             await http_request.body(), "convention_decide")
    view = conventions.decide(spec=spec, convention=request.convention, action=request.action,
                              source=request.source, note=request.note,
                              requested_value=request.requested_value,
                              expected_version=request.expected_version, actor=actor)
    step = ("Figures resting on this convention now grade G2; say so when citing them."
            if view.state == "confirmed" else
            f"Nothing is recomputed: the dictionary owner must apply {view.declaration_change} and import again.")
    return {"convention": view.id, "state": view.state, "version": view.version,
            "decided_by": view.decided_by, "declaration_change": view.declaration_change,
            "next_step": step + " This batch stays frozen."}
