"""This month's close checklist (E14-UC01) and the open-item inbox (E14-UC05).

Both are read-only projections over the same batch, master and review, so they are served
side by side: the checklist answers "which step is outstanding", the inbox "which thing".

A read-only projection over the batch, the master and the saved review. Two surfaces: the
authenticated browser gets the steps with their outstanding names; the captain gets the same
steps with counts, because "who still owes what" is exactly what it should be able to say.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from bridgeflow import integration as integration_module
from bridgeflow.api.batches import _integration_spec, _visible, load_batch
from bridgeflow.conclusions import comparison as comparison_module
from bridgeflow.conclusions import periods
from bridgeflow.identity import UserIdentity, require_user
from bridgeflow.monthly import checklist as checklist_module
from bridgeflow.monthly import inbox as inbox_module

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


def _inbox_context(period: str, user: UserIdentity | None) -> inbox_module.Context:
    ctx, _dictionary, _declaration = _context(period, user)
    return inbox_module.Context(batch_id=ctx.batch_id, period=period, batch=ctx.batch, master=ctx.master,
                                has_report=ctx.report is not None,
                                earlier_reported=_reported_earlier(period, ctx.batch_id, user))


def _reported_earlier(period: str, batch_id: str, user: UserIdentity | None) -> list[str]:
    """Other batches of this month that carry a saved review."""
    from bridgeflow.api.reviews import saved_review

    found = []
    for entry in periods.batches_for(period):
        other = entry["batch_id"]
        if other == batch_id or not _visibility(user)(entry):
            continue
        try:
            saved_review(other)
        except HTTPException:
            continue
        found.append(other)
    return found


def _scope(user: UserIdentity | None) -> inbox_module.Scope:
    """An item whose departments the viewer may not see is neither shown nor counted."""
    if user is None:
        return inbox_module.Scope(all=True)
    from bridgeflow.access import departments_for

    return inbox_module.Scope(departments=departments_for(user.sub))


@router.get("/monthly/inbox")
async def open_item_inbox(user: Annotated[UserIdentity | None, Depends(require_user)],
                          period: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
                          department: str = "", kind: str = "") -> dict:
    """What is still waiting on someone, across modules (E14-UC05).

    Every item carries where to settle it and nothing else: the inbox never decides for the
    module that owns the evidence and the approval path.
    """
    return inbox_module.collect(_inbox_context(period, user), _scope(user), department=department, kind=kind)


@router.post("/tools/monthly-inbox")
async def open_item_inbox_tool(request: dict) -> dict:
    """For the captain: counts by kind and department, and each item's handle. No cell values."""
    period = str(request.get("period", ""))
    if not period:
        raise HTTPException(422, "Give the period as YYYY-MM")
    result = inbox_module.collect(_inbox_context(period, None), inbox_module.Scope(all=True),
                                  department=str(request.get("department", "")), kind=str(request.get("kind", "")))
    return result | {"next_step": ("Say what is waiting, on whom, and where it is settled. The inbox itself decides "
                                   "nothing: each item is handled in its own module, with its own approval.")}


@router.get("/batches/templates/{department}")
async def department_template(department: str, user: Annotated[UserIdentity | None, Depends(require_user)],
                              period: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
                              ) -> dict:
    """The approved template for a month, prefilled from the declared carry-over (E14-UC02).

    The header is the approved template's own, so what comes back can be imported by the same
    declaration that produced it. Prior-period values are read through the reader's own
    visibility, and every prefilled cell says which period it came from.
    """
    from bridgeflow.api.integration import _result
    from bridgeflow.monthly import templates

    spec_model = _integration_spec()
    if spec_model is None:
        raise HTTPException(503, "No integration declaration is configured; its owner declares the templates")
    spec = spec_model.model_dump(mode="json")
    if department not in (spec.get("departments") or {}):
        raise HTTPException(404, "That department is not declared")
    relative = (spec["departments"][department] or {}).get("template") or ""
    path = (integration_module.spec_path().parent / relative) if relative else None
    if path is None or not path.is_file():
        raise HTTPException(409, "This department has no approved template file; the dictionary owner publishes one")

    rules = templates.declared(spec, department)
    prior_period = comparison_module.shift(period, rules[0].offset if rules else -1)
    prior, reason = None, ""
    if not rules:
        reason = "本部门没有声明任何沿用字段，本模板不预填。/ No carry-over is declared for this department."
    else:
        entry = periods.latest_for(prior_period, _visibility(user))
        if entry is None:
            reason = (f"没有 {prior_period} 的批次，本次不预填沿用字段。/ No batch for {prior_period}; nothing was prefilled.")
        else:
            try:
                prior = _result(entry["batch_id"], user)
            except HTTPException as exc:
                reason = f"{prior_period} 的总表读不出来（{exc.detail}），本次不预填。"
    payload = templates.build(
        spec=spec, department=department, period=period, template=path.read_bytes(),
        prior=prior, prior_period=prior_period,
        axis=comparison_module.entity_axis(spec), reason=reason)
    label = (spec["departments"][department] or {}).get("label", department)
    import base64

    return {"filename": f"{label}-{period}-{spec.get('version', '')}.xlsx".replace("/", "-"),
            "base64": base64.b64encode(payload).decode(),
            "declaration": spec.get("version", ""), "prefilled_from": prior_period if prior is not None else "",
            "reason": reason, "template": relative}
