"""Where this month's close has got to, and who still owes what (E14-UC01).

The consolidation lead's question is not "what is in this batch" but "what is still missing,
and from whom". This module answers it as a **read-only projection**: every step reads the
state the owning module already holds, so a step cannot disagree with the page it links to,
and nothing here is stored.

Which steps a month has is declared, not written here (`monthly_close.steps` in the
dictionary): a company that does not export a report has no export step, and a step's owner
role is the company's own. What each kind of step means is code, because reading a batch,
a master or a report are three different things — one `StepEvaluator` each (Strategy).

A step whose state cannot be read is `unknown`, never `done`, and one unknown step is enough
to withhold "ready to close": the whole point of the page is that nobody has to assume.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

State = Literal["done", "open", "blocked", "unknown"]


class StepSpec(BaseModel):
    id: str
    kind: str
    owner_role: str = ""
    required: bool = True
    #: Kind-specific declaration, e.g. which departments must submit.
    params: dict[str, Any] = Field(default_factory=dict)


class StepState(BaseModel):
    id: str
    kind: str
    owner_role: str = ""
    required: bool = True
    state: State = "unknown"
    #: How many things are outstanding (rows, departments, open items); 0 when done.
    count: int = 0
    #: What is outstanding, by name — declared labels or department names, never cell values.
    outstanding: list[str] = Field(default_factory=list)
    #: Which studio view settles it, for the button next to the step.
    next_view: str = ""
    reason: str = ""


class Checklist(BaseModel):
    period: str
    batch_id: str = ""
    declaration: str = ""
    steps: list[StepState] = Field(default_factory=list)
    ready_to_close: bool = False
    #: What a "ready" reading is bound to; a later import or report makes it a different reading.
    bound: dict[str, str] = Field(default_factory=dict)
    refusal: str = ""


class Context(BaseModel):
    """Everything the evaluators may read, gathered once per request."""
    model_config = {"arbitrary_types_allowed": True}

    period: str
    batch_id: str = ""
    batch: Any = None
    master: Any = None
    master_error: str = ""
    report: Any = None
    report_error: str = ""


class StepEvaluator(Protocol):
    def __call__(self, spec: StepSpec, ctx: Context) -> StepState: ...


def _base(spec: StepSpec, **rest) -> StepState:
    return StepState(id=spec.id, kind=spec.kind, owner_role=spec.owner_role, required=spec.required, **rest)


def _departments_submitted(spec: StepSpec, ctx: Context) -> StepState:
    """Which declared departments have not handed in a file."""
    required = list(spec.params.get("departments") or [])
    if not required and ctx.batch is not None and ctx.batch.integration_snapshot:
        required = sorted(ctx.batch.integration_snapshot.get("departments") or {})
    if not required:
        return _base(spec, state="unknown", reason="No departments are declared for this step")
    if ctx.batch is None:
        return _base(spec, state="blocked", count=len(required), outstanding=required, next_view="import")
    present = {table.department for table in ctx.batch.clean_tables}
    missing = [d for d in required if d not in present]
    return _base(spec, state="done" if not missing else "blocked", count=len(missing),
                 outstanding=missing, next_view="import")


def _intake_accepted(spec: StepSpec, ctx: Context) -> StepState:
    """Departments whose file the shared check chain would not accept (E14-UC03)."""
    if ctx.batch is None:
        return _base(spec, state="blocked", next_view="import")
    reports = ctx.batch.intake_checks or {}
    if not reports:
        return _base(spec, state="unknown", reason="This batch predates the intake check chain")
    refused = sorted(d for d, report in reports.items() if not report.get("accepts", False))
    return _base(spec, state="done" if not refused else "open", count=len(refused),
                 outstanding=refused, next_view="state")


def _quarantine_cleared(spec: StepSpec, ctx: Context) -> StepState:
    if ctx.batch is None:
        return _base(spec, state="blocked", next_view="import")
    held = {t.department: len(t.quarantine) for t in ctx.batch.clean_tables if t.quarantine}
    total = sum(held.values())
    return _base(spec, state="done" if not total else "open", count=total,
                 outstanding=[f"{d}×{n}" for d, n in sorted(held.items())], next_view="quarantine")


def _master_open_items(spec: StepSpec, ctx: Context) -> StepState:
    """Cross-department questions the master still has: disagreements, gaps, failed checks."""
    if ctx.batch is None:
        return _base(spec, state="blocked", next_view="import")
    if ctx.master is None:
        return _base(spec, state="unknown", reason=ctx.master_error or "The master table could not be read")
    kinds: dict[str, int] = {}
    for issue in ctx.master.issues:
        kinds[issue.kind] = kinds.get(issue.kind, 0) + 1
    total = sum(kinds.values())
    return _base(spec, state="done" if not total else "open", count=total,
                 outstanding=[f"{kind}×{n}" for kind, n in sorted(kinds.items())], next_view="integration")


def _review_validated(spec: StepSpec, ctx: Context) -> StepState:
    if ctx.report_error:
        return _base(spec, state="unknown", reason=ctx.report_error)
    if ctx.report is None:
        return _base(spec, state="open", next_view="state",
                     reason="No department review has been saved for this batch")
    missing = [role["role"] for role in ctx.report.get("roles", []) if role.get("status") != "validated"]
    return _base(spec, state="done" if not missing else "open", count=len(missing),
                 outstanding=missing, next_view="artifact")


def _brief_ready(spec: StepSpec, ctx: Context) -> StepState:
    if ctx.report_error:
        return _base(spec, state="unknown", reason=ctx.report_error)
    if ctx.report is None:
        return _base(spec, state="blocked", next_view="state",
                     reason="The brief is built from a saved review")
    if ctx.report.get("status") != "validated":
        return _base(spec, state="open", next_view="brief",
                     reason="The saved review is partial; the brief will say which departments are missing")
    return _base(spec, state="done", next_view="brief")


EVALUATORS: dict[str, StepEvaluator] = {
    "departments_submitted": _departments_submitted,
    "intake_accepted": _intake_accepted,
    "quarantine_cleared": _quarantine_cleared,
    "master_open_items": _master_open_items,
    "review_validated": _review_validated,
    "brief_ready": _brief_ready,
}


def declared_steps(dictionary: dict | None) -> list[StepSpec]:
    """The month's steps as the dictionary declares them; an undeclared kind is not invented."""
    raw = ((dictionary or {}).get("monthly_close") or {}).get("steps") or []
    steps = []
    for item in raw:
        if not isinstance(item, dict) or item.get("kind") not in EVALUATORS:
            continue
        steps.append(StepSpec.model_validate(item))
    return steps


def build(dictionary: dict | None, ctx: Context, declaration: str = "") -> Checklist:
    """Evaluate every declared step. A step that raises is `unknown`, never `done`."""
    steps = declared_steps(dictionary)
    if not steps:
        return Checklist(period=ctx.period, batch_id=ctx.batch_id, declaration=declaration,
                         refusal="No monthly close steps are declared; the dictionary owner declares them under monthly_close.steps")
    states = []
    for spec in steps:
        try:
            states.append(EVALUATORS[spec.kind](spec, ctx))
        # Deliberately broad (E14-UC01 AC-3): whatever goes wrong reading one step's state —
        # a timeout, a malformed record, a module that changed — the honest answer for that
        # step is "unknown", and the other steps must still be shown.
        except Exception as exc:  # noqa: BLE001
            states.append(_base(spec, state="unknown", reason=f"{type(exc).__name__}: {exc}"))
    ready = bool(states) and all(s.state == "done" for s in states if s.required)
    bound = {"batch_id": ctx.batch_id, "declaration": declaration}
    if ctx.report is not None and isinstance(ctx.report, dict):
        bound["report_id"] = str(ctx.report.get("report_id", ""))
    return Checklist(period=ctx.period, batch_id=ctx.batch_id, declaration=declaration,
                     steps=states, ready_to_close=ready, bound=bound)
