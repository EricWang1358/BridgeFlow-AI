"""Everything still waiting on somebody, gathered in one place (E14-UC05).

Open items are scattered by construction: a disagreement lives in the master, a held row in
quarantine, an unmatched column in the match memory, a superseded report in the batch chain.
Each module is right to own its own; what nobody owns is the question "what is mine today".

This is a projection and nothing more. It keeps no handling state of its own — an item exists
exactly as long as its own module still reports it, so settling a row in quarantine makes the
item disappear without anything here being told — and it offers no decision: every item
carries a place to go, never an approve or reject. Deciding belongs to the module that has
the evidence and the approval path.

Visibility is the same rule as everywhere else: an item whose departments the viewer may not
see is not shown **and not counted**, because a count of things you cannot look at is just an
unanswerable question.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class OpenItem(BaseModel):
    #: Stable within a batch: the same item keeps its id across refreshes.
    id: str
    #: What kind of thing is waiting; the interface translates it, so no prose here.
    kind: str
    source: str
    batch_id: str = ""
    period: str = ""
    departments: list[str] = Field(default_factory=list)
    #: A short handle for the thing itself: a field name, a row position, a column label.
    subject: str = ""
    detail: str = ""
    #: Which studio view settles it. The inbox never settles anything itself (AC-4).
    next_view: str = ""


class Scope(BaseModel):
    """Which departments this viewer may see. An empty `departments` with `all=True` sees everything."""
    all: bool = False
    departments: set[str] = Field(default_factory=set)

    def allows(self, item: OpenItem) -> bool:
        return self.all or set(item.departments) <= self.departments


class Context(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    batch_id: str = ""
    period: str = ""
    batch: Any = None
    master: Any = None
    has_report: bool = False
    #: Conventions the business side has confirmed, so a confirmed one is not reported as a gap.
    confirmed: list[str] = Field(default_factory=list)
    #: Earlier batches of this period that carry a saved review. When the batch in force has
    #: none of its own, that review was left behind by a correction and the month is waiting
    #: for a new one.
    earlier_reported: list[str] = Field(default_factory=list)


class OpenItemSource(Protocol):
    def __call__(self, ctx: Context) -> list[OpenItem]: ...


def _master_issues(ctx: Context) -> list[OpenItem]:
    if ctx.master is None:
        return []
    items = []
    for index, issue in enumerate(ctx.master.issues):
        items.append(OpenItem(id=f"master:{index}", kind=f"master_{issue.kind}", source="integration",
                              batch_id=ctx.batch_id, period=ctx.period, departments=sorted(issue.departments),
                              subject=issue.field or "", detail=issue.message, next_view="integration"))
    return items


def _quarantined_rows(ctx: Context) -> list[OpenItem]:
    if ctx.batch is None:
        return []
    items = []
    for table in ctx.batch.clean_tables:
        for index in range(len(table.quarantine)):
            items.append(OpenItem(id=f"quarantine:{table.department}:{index}", kind="quarantined_row",
                                  source="quarantine", batch_id=ctx.batch_id, period=ctx.period,
                                  departments=[table.department], subject=f"row {index}", next_view="quarantine"))
    return items


def _column_questions(ctx: Context) -> list[OpenItem]:
    if ctx.batch is None:
        return []
    from bridgeflow import column_matches

    items = []
    for table in ctx.batch.clean_tables:
        unknown, missing = column_matches.open_columns(ctx.batch.dictionary_snapshot, table)
        if not missing:
            continue
        for column in unknown:
            items.append(OpenItem(id=f"column:{table.department}:{column}", kind="column_question",
                                  source="column_matches", batch_id=ctx.batch_id, period=ctx.period,
                                  departments=[table.department], subject=column, next_view="columns"))
    return items


def _stale_report(ctx: Context) -> list[OpenItem]:
    """A review left on data that a later batch corrected (E14-UC04).

    The batch in force has no review of its own while an earlier batch of the same month has
    one: whoever reads that report is reading conclusions drawn on superseded files.
    """
    if ctx.has_report or not ctx.earlier_reported:
        return []
    departments = sorted({t.department for t in ctx.batch.clean_tables}) if ctx.batch is not None else []
    return [OpenItem(id=f"stale:{ctx.earlier_reported[-1]}", kind="stale_report", source="batches",
                     batch_id=ctx.batch_id, period=ctx.period, departments=departments,
                     subject=ctx.earlier_reported[-1], detail="A review of this month was saved on a batch that has since been corrected",
                     next_view="state")]


def _missing_provenance(ctx: Context) -> list[OpenItem]:
    """Master cells whose evidence chain is broken (E13-UC06 AC-3).

    One item per field rather than per cell: at 200k rows "this column has no traceable
    source" is the thing somebody acts on, and the count says how widespread it is.
    """
    if ctx.master is None:
        return []
    from bridgeflow.conclusions.grades import grade_master

    graded, _summary = grade_master([row.provenance for row in ctx.master.rows], frozenset(ctx.confirmed))
    fields: dict[str, int] = {}
    reasons: dict[str, str] = {}
    for row in graded:
        for field_name, result in row.items():
            if result.get("grade") is None:
                fields[field_name] = fields.get(field_name, 0) + 1
                reasons.setdefault(field_name, "; ".join(result.get("missing", [])[:2]))
    departments = sorted({t.department for t in ctx.batch.clean_tables}) if ctx.batch is not None else []
    return [OpenItem(id=f"provenance:{name}", kind="missing_provenance", source="grades",
                     batch_id=ctx.batch_id, period=ctx.period, departments=departments, subject=name,
                     detail=f"{count} cell(s): {reasons.get(name, '')}", next_view="integration")
            for name, count in sorted(fields.items())]


SOURCES: dict[str, OpenItemSource] = {
    "grades": _missing_provenance,
    "integration": _master_issues,
    "quarantine": _quarantined_rows,
    "column_matches": _column_questions,
    "batches": _stale_report,
}


def collect(ctx: Context, scope: Scope, *, department: str = "", kind: str = "") -> dict:
    """Every visible open item, with per-kind and per-department counts over the same set."""
    items: list[OpenItem] = []
    unreadable: list[str] = []
    for name, source in SOURCES.items():
        try:
            items.extend(source(ctx))
        # One module being unreadable must not blank the others' items; it is reported instead.
        except Exception as exc:  # noqa: BLE001
            unreadable.append(f"{name}: {type(exc).__name__}: {exc}")
    visible = [item for item in items if scope.allows(item)]
    shown = [item for item in visible
             if (not department or department in item.departments) and (not kind or item.kind == kind)]
    by_kind: dict[str, int] = {}
    by_department: dict[str, int] = {}
    for item in visible:
        by_kind[item.kind] = by_kind.get(item.kind, 0) + 1
        for name in item.departments:
            by_department[name] = by_department.get(name, 0) + 1
    return {"batch_id": ctx.batch_id, "period": ctx.period, "total": len(visible),
            "items": [item.model_dump(mode="json") for item in shown],
            "by_kind": by_kind, "by_department": by_department, "unreadable": unreadable}
