"""Quarantined rows get an exit: release after revalidation, or discard, on the record (#88).

A row lands in quarantine because it could not be trusted as imported — too many
blank cells, a value that does not fit its column, a date that reads two ways. Before
this module quarantine was only ever written to; a batch with quarantined rows refused
review, and the only way forward was to fix the file and import again.

The exit keeps three rules:

- **Frozen batches stay frozen.** Decisions are recorded against the batch, and applying
  them produces a *new* batch that names the one it came from. Reports on the old batch
  keep meaning what they meant.
- **Release is revalidation, not permission.** A row is released only if it passes the
  column types of its table and the frozen dictionary's declared date order — with any
  corrected cells a person supplied. Otherwise the decision is refused with the reason.
- **Every decision is a person's.** Deciding and applying are approval-gated writes; each
  decision keeps its reason, any corrected cells, and the authenticated session.

Nothing here returns a cell value to a model: listings carry the department, the row's
position and the checks that fail, by column name.
"""

from __future__ import annotations

import math
import re
import shutil
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

from bridgeflow.agents.sanitizer import _SLASHED_DATE, _is_ambiguous_date, _read_declared
from bridgeflow.agents.semantic_resolver import FieldDictionary
from bridgeflow.schemas import CleanTable, Correction, SourceRef
from bridgeflow.store import _root, _write

MAX_LISTED = 100
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Fix(BaseModel):
    column: str = Field(min_length=1, max_length=80)
    value: str = Field(max_length=200)


class Disposition(BaseModel):
    department: str
    index: int = Field(ge=0)
    action: Literal["release", "discard"]
    reason: str = Field(min_length=1, max_length=300)
    fixes: list[Fix] = Field(default_factory=list, max_length=10)
    decided_by: str = ""
    authorised_by: str = ""
    decided_at: str = ""


class Ledger(BaseModel):
    batch_id: str
    decisions: list[Disposition] = Field(default_factory=list)
    applied_to: str = ""


def _ledger_path(batch_id: str):
    return _root() / "quarantine-decisions" / f"{batch_id}.json"


def ledger(batch_id: str) -> Ledger:
    path = _ledger_path(batch_id)
    if not path.is_file():
        return Ledger(batch_id=batch_id)
    return Ledger.model_validate_json(path.read_text(encoding="utf-8"))


def decisions_by_row(batch_id: str) -> dict[tuple[str, int], dict[str, Any]]:
    return {(d.department, d.index): d.model_dump() for d in ledger(batch_id).decisions}


# --- revalidation ------------------------------------------------------------------


def revalidate(table: CleanTable, row: dict[str, Any], date_order: str | None,
               fixes: list[Fix] | None = None) -> tuple[dict[str, Any] | None, list[str]]:
    """The row as it would enter the table, or the checks it still fails (by column name)."""
    values = dict(row)
    known = {spec.name for spec in table.columns}
    issues: list[str] = []
    for fix in fixes or []:
        if fix.column not in known:
            issues.append(f"{fix.column}: not a column of this table")
        else:
            values[fix.column] = fix.value
    blank = [name for name in known if _blank(values.get(name))]
    if len(known) - len(blank) < max(1, len(known) // 2):
        issues.append("more than half of the row's cells are blank")
    cleaned: dict[str, Any] = {}
    for spec in table.columns:
        value = values.get(spec.name)
        if _blank(value):
            cleaned[spec.name] = None
            continue
        text = str(value).strip()
        if spec.dtype == "number":
            try:
                number = Decimal(text.replace(",", ""))
                cleaned[spec.name] = int(number) if number == number.to_integral_value() else float(number)
            except InvalidOperation:
                issues.append(f"{spec.name}: expected a number")
        elif spec.dtype == "date":
            if _ISO_DATE.fullmatch(text):
                cleaned[spec.name] = text
            elif _SLASHED_DATE.match(text) and date_order:
                iso = _read_declared(text, date_order)
                if iso is None:
                    issues.append(f"{spec.name}: not a date in the declared {date_order} order")
                else:
                    cleaned[spec.name] = iso
            elif _SLASHED_DATE.match(text) and not _is_ambiguous_date(text):
                issues.append(f"{spec.name}: write the date as YYYY-MM-DD or declare the department's date_order")
            else:
                issues.append(f"{spec.name}: date is ambiguous or unreadable; supply it as YYYY-MM-DD")
        else:
            cleaned[spec.name] = text
    return (None, issues) if issues else (cleaned, [])


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or str(value).strip() == ""


# --- listing, deciding, applying ------------------------------------------------------


class Entry(BaseModel):
    department: str
    index: int
    failing_checks: list[str]
    releasable: bool
    decision: str = ""


def _order(batch, department: str) -> str | None:
    return ((batch.dictionary_snapshot or {}).get("date_order") or {}).get(department)


def entries(batch_id: str, batch) -> dict[str, Any]:
    decided = decisions_by_row(batch_id)
    items: list[Entry] = []
    total = 0
    for table in batch.clean_tables:
        for index, row in enumerate(table.quarantine):
            total += 1
            if len(items) >= MAX_LISTED:
                continue
            _, issues = revalidate(table, row, _order(batch, table.department))
            items.append(Entry(department=table.department, index=index, failing_checks=issues,
                               releasable=not issues, decision=decided.get((table.department, index), {}).get("action", "")))
    return {"batch_id": batch_id, "total": total, "truncated": total > len(items),
            "applied_to": ledger(batch_id).applied_to, "entries": [e.model_dump() for e in items]}


def decide(batch_id: str, batch, decision: Disposition) -> Ledger:
    book = ledger(batch_id)
    if book.applied_to:
        raise HTTPException(409, f"Decisions for this batch were already applied to {book.applied_to}; work on that batch")
    tables = [t for t in batch.clean_tables if t.department == decision.department]
    if len(tables) != 1 or not 0 <= decision.index < len(tables[0].quarantine):
        raise HTTPException(404, "No such quarantined row in this batch")
    if decision.action == "release":
        _, issues = revalidate(tables[0], tables[0].quarantine[decision.index], _order(batch, decision.department),
                               decision.fixes)
        if issues:
            raise HTTPException(409, "Row still fails revalidation: " + "; ".join(issues))
    elif decision.fixes:
        raise HTTPException(422, "Corrected cells only make sense when releasing a row")
    decision.decided_at = datetime.now(UTC).isoformat()
    book.decisions = [d for d in book.decisions if (d.department, d.index) != (decision.department, decision.index)]
    book.decisions.append(decision)
    _write(_ledger_path(batch_id), book.model_dump())
    return book


async def apply(batch_id: str, batch, *, batch_path, load_batch, assemble, summary) -> dict[str, Any]:
    """Create the derived batch once. Applying again returns the same derived batch."""
    book = ledger(batch_id)
    if book.applied_to:
        return {"batch": summary(book.applied_to, load_batch(book.applied_to)).model_dump(), "replayed": True}
    if not book.decisions:
        raise HTTPException(409, "No quarantine decisions recorded for this batch")
    derived = batch.model_copy(deep=True)
    new_id = uuid.uuid4().hex
    decided = {(d.department, d.index): d for d in book.decisions}
    for table in derived.clean_tables:
        kept = []
        for index, row in enumerate(table.quarantine):
            decision = decided.get((table.department, index))
            if decision is None:
                kept.append(row)
                continue
            if decision.action == "release":
                cleaned, issues = revalidate(table, row, _order(batch, table.department), decision.fixes)
                if issues:  # the frozen batch cannot have changed, but never trust that silently
                    raise HTTPException(409, f"{table.department} row {index} no longer revalidates: {'; '.join(issues)}")
                table.rows.append(cleaned)
            table.corrections.append(Correction(
                source=SourceRef(department=table.department, period=batch.period, row=index, column="(row)",
                                 filename=table.filename, sheet=table.sheet, batch=new_id),
                row=index, column="(row)", before=None, after=None, rule={"release": "quarantine_released", "discard": "quarantine_discarded"}[decision.action],
                confidence=1.0, reason=f"{decision.reason} (decided by {decision.authorised_by or decision.decided_by})"))
        table.quarantine = kept
        table.batch = new_id
    derived.derived_from = batch_id
    derived.dispositions = [d.model_dump() for d in book.decisions]
    await assemble(derived, FieldDictionary(derived.dictionary_snapshot or {}))
    sources = batch_path(batch_id).parent / "sources"
    if (sources / batch_id).is_dir():
        shutil.copytree(sources / batch_id, sources / new_id)
    _write(batch_path(new_id), derived.model_dump(mode="json"))
    book.applied_to = new_id
    _write(_ledger_path(batch_id), book.model_dump())
    return {"batch": summary(new_id, derived).model_dump(), "replayed": False}
