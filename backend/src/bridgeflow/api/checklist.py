"""This month's close checklist (E14-UC01): what is done, what is missing and from whom.

A read-only projection over the batch, the master and the saved review. Two surfaces: the
authenticated browser gets the steps with their outstanding names; the captain gets the same
steps with counts, because "who still owes what" is exactly what it should be able to say.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from bridgeflow.api.batches import _visible, load_batch
from bridgeflow.conclusions import periods
from bridgeflow.identity import UserIdentity, require_user
from bridgeflow.monthly import checklist as checklist_module

router = APIRouter(tags=["checklist"])


def _context(period: str, user: UserIdentity | None) -> tuple[checklist_module.Context, dict | None, str]:
    """Gather what the steps read. Every read that can fail is caught and reported as such."""
    ctx = checklist_module.Context(period=period)
    entry = periods.latest_for(period, _visibility(user))
    if entry is None:
        return ctx, None, ""
    batch_id = entry["batch_id"]
    batch = _visible(load_batch(batch_id), user)
    ctx.batch_id, ctx.batch = batch_id, batch
    if batch.integration_snapshot is not None:
        from bridgeflow.api.integration import _result
        try:
            ctx.master = _result(batch_id, user)
        except HTTPException as exc:
            ctx.master_error = str(exc.detail)
    from bridgeflow.api.reviews import saved_review
    try:
        ctx.report = saved_review(batch_id)
    except HTTPException as exc:
        # 404 means the step is simply not done yet; anything else means it could not be read.
        ctx.report_error = "" if exc.status_code == 404 else str(exc.detail)
    declaration = ""
    if batch.integration_snapshot is not None:
        declaration = str(batch.integration_snapshot.get("version", ""))
    return ctx, batch.dictionary_snapshot, declaration


def _visibility(user: UserIdentity | None):
    def allowed(entry: dict) -> bool:
        try:
            _visible(load_batch(entry["batch_id"]), user)
        except HTTPException:
            return False
        return True
    return allowed


def _build(period: str, user: UserIdentity | None) -> checklist_module.Checklist:
    ctx, dictionary, declaration = _context(period, user)
    if ctx.batch is None:
        from bridgeflow.api.batches import _load_dictionary
        from bridgeflow.metrics import dictionary_path
        dictionary, _, _ = _load_dictionary(dictionary_path())
    return checklist_module.build(dictionary, ctx, declaration)


@router.get("/monthly/checklist", response_model=checklist_module.Checklist)
async def monthly_checklist(user: Annotated[UserIdentity | None, Depends(require_user)],
                            period: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
                            ) -> checklist_module.Checklist:
    return _build(period, user)


@router.post("/tools/monthly-checklist")
async def monthly_checklist_tool(request: dict) -> dict:
    """For the captain: step states, counts and who owns each. No rows, no cell values."""
    period = str(request.get("period", ""))
    if not period:
        raise HTTPException(422, "Give the period as YYYY-MM")
    result = _build(period, None)
    open_steps = [s for s in result.steps if s.state != "done"]
    return {
        "period": result.period, "batch_id": result.batch_id, "ready_to_close": result.ready_to_close,
        "refusal": result.refusal,
        "steps": [s.model_dump(mode="json") for s in result.steps],
        "next_step": (result.refusal or
                      ("Every declared step is done; say what the close is bound to (batch and report) rather than "
                       "declaring the month closed yourself." if result.ready_to_close else
                       "Name each outstanding step, who owns it and what it is waiting for. A step whose state is "
                       "unknown was not read — say so instead of treating it as done.")),
        "outstanding": len(open_steps),
    }
