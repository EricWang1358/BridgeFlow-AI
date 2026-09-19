"""Replacing one department's file as a new batch version (E14-UC04).

After an import, usually only one department's file is wrong. Re-importing all four would
make the other three departments upload again for nothing and would change their source
digests, so a correction derives a new batch instead: the replaced department is parsed and
cleaned afresh, the other departments keep the exact sources and cleaned tables of the batch
they came from, and the master is rebuilt from the mix.

The original batch is never touched — not its rows, not its master, not its report, and not
its lineage record. A batch's successors are found by looking for batches that name it as
their origin (`derived_from`), so nothing has to be written back into a frozen file.

Refusals come before any derivation: a file for another month, another department's file, or
a file byte-identical to the one already in the batch leaves the batch alone and says why.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MasterDiff(BaseModel):
    """What changed in the master between the original batch and the derived one.

    Counts and field names only: at 200k rows the count is the answer, and the cells belong
    to the authenticated views that already show them.
    """
    rows_before: int = 0
    rows_after: int = 0
    rows_added: int = 0
    rows_removed: int = 0
    cells_changed: int = 0
    fields_changed: list[str] = Field(default_factory=list)
    issues_before: dict[str, int] = Field(default_factory=dict)
    issues_after: dict[str, int] = Field(default_factory=dict)
    #: Open-item kinds this correction settled or introduced, as after − before.
    issues_delta: dict[str, int] = Field(default_factory=dict)


def _by_key(result) -> dict[tuple[str, ...], dict[str, Any]]:
    return {tuple(row.key): row.values for row in result.rows}


def _issue_counts(result) -> dict[str, int]:
    counts: dict[str, int] = {}
    for issue in result.issues:
        counts[issue.kind] = counts.get(issue.kind, 0) + 1
    return counts


def diff(before, after) -> MasterDiff:
    """Compare two master results. Either may be None when its batch has no master."""
    if before is None or after is None:
        return MasterDiff(rows_before=len(before.rows) if before else 0,
                          rows_after=len(after.rows) if after else 0)
    old, new = _by_key(before), _by_key(after)
    changed_fields: set[str] = set()
    cells = 0
    for key in old.keys() & new.keys():
        for name in set(old[key]) | set(new[key]):
            if old[key].get(name) != new[key].get(name):
                cells += 1
                changed_fields.add(name)
    issues_before, issues_after = _issue_counts(before), _issue_counts(after)
    delta = {kind: issues_after.get(kind, 0) - issues_before.get(kind, 0)
             for kind in set(issues_before) | set(issues_after)
             if issues_after.get(kind, 0) != issues_before.get(kind, 0)}
    return MasterDiff(rows_before=len(before.rows), rows_after=len(after.rows),
                      rows_added=len(new.keys() - old.keys()), rows_removed=len(old.keys() - new.keys()),
                      cells_changed=cells, fields_changed=sorted(changed_fields),
                      issues_before=issues_before, issues_after=issues_after, issues_delta=delta)


def periods_refusal(spec, sheet, period: str) -> str:
    """Why this file is not a file for `period`, or "" if it is (AC-4).

    The period is read from the rows themselves through the declaration, because the form
    field says what the uploader believes, not what the file contains. A file whose period
    cannot be read is not refused on that ground: the declaration may simply not give this
    department a period column.
    """
    from bridgeflow import integration

    found = integration.periods_in(spec, sheet) if spec is not None else set()
    other = sorted(found - {period})
    if not other:
        return ""
    return (f"This file reports {', '.join(other[:3])}, not {period}. "
            "Upload the file for this batch's month, or import the other month as its own batch.")


def unchanged_refusal(previous: dict | None, sha256: str) -> str:
    """AC-3: a byte-identical file derives nothing, and says so rather than silently succeeding."""
    if previous and previous.get("sha256") == sha256:
        return "This file is identical to the one already in the batch; nothing was derived."
    return ""
