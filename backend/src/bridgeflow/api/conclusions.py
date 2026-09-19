"""The one-page monthly brief for a batch (E13-UC01), for the authenticated browser."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from bridgeflow import column_matches
from bridgeflow.api.batches import _visible, load_batch
from bridgeflow.api.reviews import saved_review
from bridgeflow.conclusions import comparison as comparison_module
from bridgeflow.conclusions.brief import BriefBuilder, ConclusionBrief, declaration
from bridgeflow.identity import UserIdentity, require_user

router = APIRouter(tags=["conclusions"])


def _master_or_none(batch_id: str, user: UserIdentity | None):
    from bridgeflow.api.integration import _result
    try:
        return _result(batch_id, user)
    except HTTPException as exc:
        if exc.status_code in (409, 404):
            return None
        raise


def _visibility(user: UserIdentity | None):
    """Whether this caller may compare against that batch, by the same rule as reading it."""
    def allowed(entry: dict) -> bool:
        try:
            _visible(load_batch(entry["batch_id"]), user)
        except HTTPException:
            return False
        return True
    return allowed


@router.get("/conclusions/batches/{batch_id}/comparison", response_model=comparison_module.Comparison)
async def period_comparison(batch_id: str, user: Annotated[UserIdentity | None, Depends(require_user)],
                            base: Annotated[str, Query(pattern=r"^(prior_month|last_year|plan)$")] = "prior_month",
                            ) -> comparison_module.Comparison:
    """This batch against a base period. Read-only; refusals say which kind they are."""
    batch = _visible(load_batch(batch_id), user)
    declared = declaration(batch.dictionary_snapshot or {})
    return comparison_module.build(
        batch_id=batch_id, batch=batch, base_kind=base, metrics=declared.key_metrics,
        master=_master_or_none(batch_id, user), load_batch=load_batch,
        master_for=lambda other: _master_or_none(other, user), visible=_visibility(user))


@router.get("/conclusions/batches/{batch_id}", response_model=ConclusionBrief)
async def monthly_brief(batch_id: str, user: Annotated[UserIdentity | None, Depends(require_user)],
                        report_id: Annotated[str | None, Query(pattern=r"^[a-f0-9]{32}$")] = None) -> ConclusionBrief:
    batch = _visible(load_batch(batch_id), user)
    try:
        latest = saved_review(batch_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            raise HTTPException(409, "Complete the review before building the brief") from exc
        raise
    report = saved_review(batch_id, report_id) if report_id else latest
    master = None
    if batch.integration_snapshot is not None:
        from bridgeflow.api.integration import _result
        try:
            master = _result(batch_id, user)
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
    counts = {"quarantined_rows": sum(len(t.quarantine) for t in batch.clean_tables),
              "column_questions": column_matches.count_questions(batch.dictionary_snapshot, batch.clean_tables)}
    try:
        change = comparison_module.build(
            batch_id=batch_id, batch=batch, base_kind="prior_month",
            metrics=declaration(batch.dictionary_snapshot or {}).key_metrics, master=master,
            load_batch=load_batch, master_for=lambda other: _master_or_none(other, user),
            visible=_visibility(user))
    except HTTPException:
        # The brief still stands without a comparison; the page says the base is unavailable.
        change = comparison_module.Comparison(base_kind="prior_month", status="base_unusable",
                                              reason="The current period could not be compared")
    return BriefBuilder(batch_id=batch_id, report=report, latest_report_id=latest["report_id"],
                        dictionary=batch.dictionary_snapshot or {}, batch_counts=counts, master=master,
                        comparison=change).build()
