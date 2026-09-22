"""Agent-readable issue details and the bounded cell read (#245).

Import leaves a batch with things a person must settle: cells the sanitizer changed,
rows held in quarantine, intake findings, columns dropped as unrepresentable, matches
gone stale, columns asking to be matched. The browser shows all of this; until now the
captain saw only counts, so every disposal was a person reading the screen alone.

Two reads close that gap, under the boundary #245 revised (one sentence, the rest of
the old rule intact): raw cell contents may enter the model's context **bound to one
open item at a time** — never in bulk. Accordingly:

- `batch_issues` projects everything waiting, per item with the tool that settles it.
  Correction changes are listed (the browser shows them too); quarantined rows are
  listed **without** their values — that is what `quarantine_row` is for.
- `quarantine_row` reads exactly one held row: its values, the headers as uploaded,
  the file it came from, and the checks it currently fails. One row per call, cells
  capped, department visibility enforced, every read written to the cell-access log.

Neither read spends an approval (D1); deciding still goes through `quarantine_decide`'s
approval gate. Listing and reading change nothing — `monthly/inbox.py` and the browser
views stay the single sources of truth this module projects from (D8).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from bridgeflow import column_matches, quarantine
from bridgeflow.api.batches import _visible, load_batch
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.identity import UserIdentity, require_user

router = APIRouter(prefix="/tools", tags=["issues"])

MAX_ISSUES = 120
MAX_CELL_CHARS = 4096
MAX_COLUMNS = 120

#: Corrections that record a finished disposition are history, not open work — the
#: same rule the inbox applies (`monthly.inbox`).
_DISPOSITION_RULES = {"quarantine_released", "quarantine_discarded"}


class IssueItem(BaseModel):
    """One thing waiting on somebody, with the tool that settles it."""

    id: str
    kind: Literal["intake_correction", "quarantined_row", "intake_finding",
                  "dropped_column", "stale_match", "column_question", "unresolved_mapping",
                  "dictionary_gap"]
    department: str
    subject: str
    detail: str
    next_step: str
    #: Corrections: what the sanitizer changed, and why.
    column: str = ""
    before: Any = None
    after: Any = None
    rule: str = ""
    #: Quarantined rows: the checks they fail right now, without their cell values.
    checks: list[str] = Field(default_factory=list)
    releasable: bool | None = None
    shift_suggestion: str = ""
    #: Which file the item came from, when the batch knows.
    source_file: str = ""
    severity: str = ""


class BatchIssues(BaseModel):
    batch_id: str
    status: str
    total: int
    truncated: bool
    counts: dict[str, int] = Field(default_factory=dict)
    items: list[IssueItem] = Field(default_factory=list)
    next_step: str = ""


def _correction_items(batch, counter: dict[str, int]) -> list[IssueItem]:
    items: list[IssueItem] = []
    for table in batch.clean_tables:
        for position, correction in enumerate(table.corrections):
            if correction.rule in _DISPOSITION_RULES:
                continue
            counter["intake_correction"] = counter.get("intake_correction", 0) + 1
            if len(items) >= MAX_ISSUES:
                continue
            items.append(IssueItem(
                id=f"correction:{table.department}:{position}", kind="intake_correction",
                department=table.department, subject=correction.column,
                detail=correction.reason, next_step=(
                    "Read the source file to see the original row; the sanitizer's change is "
                    "a proposal with a stated rule — contest it by fixing the source and re-importing."),
                column=correction.column, before=correction.before, after=correction.after,
                rule=correction.rule, source_file=correction.source.filename if correction.source else ""))
    return items


def _quarantine_items(batch, batch_id: str, counter: dict[str, int]) -> list[IssueItem]:
    listing = quarantine.entries(batch_id, batch)
    items: list[IssueItem] = []
    for entry in listing["entries"]:
        counter["quarantined_row"] = counter.get("quarantined_row", 0) + 1
        if len(items) >= MAX_ISSUES:
            continue
        items.append(IssueItem(
            id=f"quarantine:{entry['department']}:{entry['index']}", kind="quarantined_row",
            department=entry["department"], subject=f"row {entry['index']}",
            detail=("passes revalidation as held" if entry["releasable"]
                    else "; ".join(entry["failing_checks"])),
            next_step=("quarantine_row to read this row's values and provenance, propose the fix, "
                       "quarantine_decide for the person's release-or-discard"),
            checks=entry["failing_checks"], releasable=entry["releasable"],
            shift_suggestion=entry["shift_suggestion"]))
    return items


def _intake_items(batch, counter: dict[str, int]) -> list[IssueItem]:
    items: list[IssueItem] = []
    for department, report in (batch.intake_checks or {}).items():
        for finding in (report.get("must_fix") or []) + (report.get("review") or []):
            severity = "must_fix" if finding in (report.get("must_fix") or []) else "review"
            counter["intake_finding"] = counter.get("intake_finding", 0) + 1
            if len(items) >= MAX_ISSUES:
                continue
            items.append(IssueItem(
                id=f"intake:{department}:{finding.get('check', '')}:{finding.get('row', '')}",
                kind="intake_finding", department=str(department),
                subject=str(finding.get("check", "")), detail=str(finding.get("message", "")),
                next_step=("must_fix findings block the batch — fix the source file and re-import"
                           if severity == "must_fix" else
                           "a review finding does not block; weigh it during the review"),
                severity=severity, source_file=report.get("filename", "")))
    return items


def _dropped_items(batch, counter: dict[str, int]) -> list[IssueItem]:
    items: list[IssueItem] = []
    for dropped in batch.dropped_columns or []:
        department = str(dropped.get("department", ""))
        subject = str(dropped.get("column", ""))
        counter["dropped_column"] = counter.get("dropped_column", 0) + 1
        if len(items) >= MAX_ISSUES:
            continue
        rest = {key: value for key, value in dropped.items() if key not in ("department", "column")}
        items.append(IssueItem(
            id=f"dropped:{department}:{subject}", kind="dropped_column", department=department,
            subject=subject, detail=json.dumps(rest, ensure_ascii=False)[:300],
            next_step="Nothing in the column was representable; if it matters, fix the source field type and re-import."))
    return items


def _match_items(batch, counter: dict[str, int]) -> list[IssueItem]:
    items: list[IssueItem] = []
    for stale in batch.stale_matches:
        counter["stale_match"] = counter.get("stale_match", 0) + 1
        if len(items) >= MAX_ISSUES:
            continue
        items.append(IssueItem(
            id=f"stale:{stale}", kind="stale_match", department=stale.split(".", 1)[0],
            subject=stale, detail="The column's shape changed since this match was approved, so it was not applied.",
            next_step="column_candidates to re-propose, then confirm_column_match — the person decides again."))
    for table in batch.clean_tables:
        unknown, missing = column_matches.open_columns(batch.dictionary_snapshot, table)
        if not missing:
            continue
        for column in unknown:
            counter["column_question"] = counter.get("column_question", 0) + 1
            if len(items) >= MAX_ISSUES:
                continue
            items.append(IssueItem(
                id=f"column:{table.department}:{column}", kind="column_question",
                department=table.department, subject=column,
                detail="The dictionary does not know this uploaded column, but the department has an undeclared slot it could fill.",
                next_step="column_candidates for the closed candidate list, then confirm_column_match; no candidate means the dictionary owner drafts (#205)."))
    return items


def _mapping_items(batch, counter: dict[str, int]) -> list[IssueItem]:
    if batch.graph is None:
        return []
    items: list[IssueItem] = []
    for position, unresolved in enumerate(batch.graph.unresolved):
        counter["unresolved_mapping"] = counter.get("unresolved_mapping", 0) + 1
        if len(items) >= MAX_ISSUES:
            continue
        dump = unresolved.model_dump() if hasattr(unresolved, "model_dump") else dict(unresolved)
        items.append(IssueItem(
            id=f"mapping:{position}", kind="unresolved_mapping",
            department="", subject=f"{dump.get('source', '?')} → {dump.get('target', '?')}",
            detail=str(dump.get("justification", "") or "No justification recorded."),
            next_step="confirm_mapping so a person decides it; unresolved links keep the batch in needs_review."))
    return items


def _dictionary_gap_item(batch) -> IssueItem | None:
    if not batch.refusal:
        return None
    return IssueItem(
        id="dictionary_gap", kind="dictionary_gap", department="",
        subject="field dictionary", detail=batch.refusal,
        next_step=("dictionary_import with the business's OA dictionary spreadsheet, or "
                   "dictionary_draft from this batch's column profiles — then decide every entry "
                   "and publish (#205), and import again."))


@router.post("/batch-issues", response_model=BatchIssues)
async def batch_issues(request: dict, user: Annotated[UserIdentity | None, Depends(require_user)]) -> BatchIssues:
    """Everything waiting on somebody in one batch, as the browser shows it (D8)."""
    batch = _visible(load_batch(str(request.get("batch_id", ""))), user)
    batch_id = str(request.get("batch_id", ""))
    counter: dict[str, int] = {}
    items = (_correction_items(batch, counter) + _quarantine_items(batch, batch_id, counter)
             + _intake_items(batch, counter) + _dropped_items(batch, counter)
             + _match_items(batch, counter) + _mapping_items(batch, counter))
    gap = _dictionary_gap_item(batch)
    truncated = len(items) > MAX_ISSUES
    return BatchIssues(
        batch_id=batch_id,
        status=("needs_configuration" if batch.refusal else "needs_review"
                if counter.get("quarantined_row") or counter.get("column_question") or batch.graph and batch.graph.unresolved
                else "ready" if batch.master_table and batch.master_table.rows else "empty"),
        total=sum(counter.values()), truncated=truncated, counts=counter, items=items[:MAX_ISSUES],
        next_step=(gap.next_step if gap else
                   "Settle the items above with the person — each names the tool that closes it — "
                   "then ask for the review." if items else
                   "Nothing is waiting on this batch; it is ready for the review."))


class RowRequest(BaseModel):
    batch_id: str
    department: str
    index: int = Field(ge=0)


class QuarantinedRow(BaseModel):
    batch_id: str
    department: str
    index: int
    #: The held row's values, keyed by cleaned column name. Strings beyond 4 KB are
    #: truncated and named in `cells_truncated` (D5) — never silently.
    values: dict[str, Any]
    #: cleaned column name → the header as the department wrote it.
    original_columns: dict[str, str]
    filename: str = ""
    sheet: str = ""
    failing_checks: list[str] = Field(default_factory=list)
    releasable: bool = False
    shift_suggestion: str = ""
    cells_truncated: list[str] = Field(default_factory=list)
    next_step: str = ""


def _record_access(*, actor: str, batch_id: str, department: str, index: int, columns: list[str]) -> None:
    """One JSONL line per cell read: who read what, bound to which open item (D2)."""
    configured = Path(settings.cell_access_log_path)
    folder = configured if configured.is_absolute() else REPO_ROOT / configured
    folder.mkdir(parents=True, exist_ok=True)
    entry = {"at": datetime.now(UTC).isoformat(), "actor": actor, "batch_id": batch_id,
             "department": department, "row": index, "item": f"quarantine:{department}:{index}",
             "columns": columns}
    line = json.dumps(entry, ensure_ascii=False)
    with (folder / f"{entry['at'][:10]}.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


@router.post("/quarantine-row", response_model=QuarantinedRow)
async def quarantine_row(request: RowRequest, user: Annotated[UserIdentity | None, Depends(require_user)]) -> QuarantinedRow:
    """One held row: its values, its provenance, the checks it fails — the proposal's evidence.

    Bound to the open item, one row per call (D6); nothing here decides anything.
    """
    batch = _visible(load_batch(request.batch_id), user)
    tables = [table for table in batch.clean_tables if table.department == request.department]
    if len(tables) != 1 or request.index >= len(tables[0].quarantine):
        raise HTTPException(404, "No such quarantined row in this batch")
    table = tables[0]
    raw = table.quarantine[request.index]

    values: dict[str, Any] = {}
    truncated: list[str] = []
    for name, value in list(raw.items())[:MAX_COLUMNS]:
        if isinstance(value, str) and len(value) > MAX_CELL_CHARS:
            value = value[:MAX_CELL_CHARS] + "…(truncated)"
            truncated.append(name)
        values[name] = value
    originals = {name: table.original_columns.get(name, name) for name in values}

    order = ((batch.dictionary_snapshot or {}).get("date_order") or {}).get(request.department)
    _, issues = quarantine.revalidate(table, raw, order)
    passing = [direction for direction in ("left", "right")
               if issues and not quarantine.revalidate(table, quarantine.shifted(table, raw, direction), order)[1]]

    actor = user.sub if user else "host-session"
    _record_access(actor=actor, batch_id=request.batch_id, department=request.department,
                   index=request.index, columns=sorted(values))
    return QuarantinedRow(
        batch_id=request.batch_id, department=request.department, index=request.index,
        values=values, original_columns=originals, filename=table.filename, sheet=table.sheet,
        failing_checks=issues, releasable=not issues,
        shift_suggestion=passing[0] if len(passing) == 1 else "",
        cells_truncated=truncated,
        next_step=("Explain the row and the failed checks to the person, propose fixes with your "
                   "evidence, and record their decision with quarantine_decide — release only with "
                   "cells the person approved, discard with their reason."))
