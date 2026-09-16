"""The one-page monthly brief for a batch (E13-UC01), for the authenticated browser."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from bridgeflow import column_matches
from bridgeflow.api.batches import _visible, load_batch
from bridgeflow.api.reviews import saved_review
from bridgeflow.conclusions.brief import BriefBuilder, ConclusionBrief
from bridgeflow.identity import UserIdentity, require_user

router = APIRouter(tags=["conclusions"])


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
    return BriefBuilder(batch_id=batch_id, report=report, latest_report_id=latest["report_id"],
                        dictionary=batch.dictionary_snapshot or {}, batch_counts=counts, master=master).build()
