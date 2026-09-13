"""The 跨部门业务整合总表 for an imported batch (browser views) and its summary (captain tool)."""

from __future__ import annotations

import base64
import json

from fastapi import APIRouter, HTTPException

from bridgeflow import integration
from bridgeflow.api.batches import BatchRef, batch_path, load_batch

router = APIRouter(tags=["integration"])


def _result(batch_id: str) -> integration.MasterResult:
    batch = load_batch(batch_id)
    spec = integration.load_spec()
    folder = batch_path(batch_id).parent / "sources" / batch_id
    sheets = []
    for table in batch.clean_tables:
        path = folder / f"{table.department}.json"
        if not path.is_file():
            raise HTTPException(409, "This batch kept no original sheets; import the department templates again")
        sheets.append(integration.sheet_from_preview(table.department, json.loads(path.read_text(encoding="utf-8"))))
    return integration.integrate(spec, sheets)


@router.get("/integration/batches/{batch_id}")
async def master_for_batch(batch_id: str) -> integration.MasterResult:
    """Browser view: every row, value and source. Rows stay in the authenticated browser."""
    return _result(batch_id)


@router.get("/integration/batches/{batch_id}/xlsx")
async def master_workbook(batch_id: str) -> dict:
    result = _result(batch_id)
    return {"filename": f"跨部门业务整合总表-{batch_id[:8]}.xlsx",
            "base64": base64.b64encode(integration.to_xlsx(result)).decode()}


@router.post("/tools/integration-summary")
async def integration_summary(request: BatchRef) -> dict:
    """For the captain: counts and open items only, never a value from a sheet."""
    result = _result(request.batch_id)
    counts: dict[str, int] = {}
    for issue in result.issues:
        counts[issue.kind] = counts.get(issue.kind, 0) + 1
    return {
        "batch_id": request.batch_id, "declaration": result.version,
        "rows": len(result.rows), "complete_rows": sum(1 for r in result.rows if r.complete),
        "columns": len(result.columns), "issues_by_kind": counts,
        # Declaration text, not sheet data: which gaps rest on a convention rather than the business side's word.
        "assumptions": result.assumptions,
        "open_items": [{"kind": i.kind, "field": i.field, "departments": i.departments, "message": i.message}
                       for i in result.issues[:20]],
        "next_step": ("Explain the open items to the person and who must decide each; "
                      "undeclared constants and roll-up rules belong to the dictionary owner. "
                      "When citing a figure that rests on an assumption, say it follows a convention the business side has not confirmed."),
    }
