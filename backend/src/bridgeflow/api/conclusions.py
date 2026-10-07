"""The one-page monthly brief for a batch (E13-UC01), for the authenticated browser."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from bridgeflow import business, column_matches
from bridgeflow.api.batches import _visible, load_batch
from bridgeflow.api.reviews import saved_review
from bridgeflow.conclusions import aggregate, charts, conventions, report
from bridgeflow.conclusions import comparison as comparison_module
from bridgeflow.conclusions.brief import BriefBuilder, ConclusionBrief, declaration
from bridgeflow.conclusions.grain import Calendar, Grain, Period, containing, parse
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
                        comparison=change,
                        confirmed_conventions=frozenset(conventions.confirmed(batch.integration_snapshot or {}))).build()


@router.get("/conclusions/batches/{batch_id}/charts")
async def metric_charts(batch_id: str, user: Annotated[UserIdentity | None, Depends(require_user)]) -> dict:
    """The declared charts for this batch (E13-UC03).

    Every number is recomputed from its batch; no chart keeps a copy. A trend uses this
    batch for its current month and the latest visible batch for each earlier month.
    """
    batch = _visible(load_batch(batch_id), user)
    dictionary = batch.dictionary_snapshot or {}
    specs = charts.declared(dictionary)
    if not specs:
        return {"batch_id": batch_id, "period": batch.period, "charts": [],
                "refusal": "No charts are declared for this dictionary; a metric without a chart declaration is shown as a table"}
    master = _master_or_none(batch_id, user)
    comparison = None
    if any(spec.kind == "variance" for spec in specs):
        try:
            comparison = comparison_module.build(
                batch_id=batch_id, batch=batch, base_kind="prior_month",
                metrics=declaration(dictionary).key_metrics, master=master, load_batch=load_batch,
                master_for=lambda other: _master_or_none(other, user), visible=_visibility(user))
        except HTTPException:
            comparison = None
    confirmed = conventions.confirmed(batch.integration_snapshot or {})
    cell_grades = []
    if master is not None and any(spec.kind == "entity_bars" for spec in specs):
        from bridgeflow.conclusions.grades import grade_master
        cell_grades, _summary = grade_master([row.provenance for row in master.rows], frozenset(confirmed))
    built = []
    for spec in specs:
        if spec.kind == "trend":
            built.append(charts.trend(spec, dictionary, _metric_series(spec, batch_id, batch, user), confirmed))
        elif spec.kind == "variance":
            built.append(charts.variance(spec, comparison, batch_id=batch_id, period=batch.period))
        else:
            built.append(charts.entity_bars(spec, master, comparison.breaches if comparison else [],
                                            comparison_module.entity_axis(batch.integration_snapshot),
                                            cell_grades))
    return {"batch_id": batch_id, "period": batch.period,
            "charts": [chart.model_dump(mode="json") for chart in built]}


def _metric_series(spec: charts.ChartSpec, batch_id: str, batch, user: UserIdentity | None) -> list[dict]:
    """One declared metric across the last N periods, ending at the selected batch.

    A period with no visible batch, or one whose figures cannot be computed, is a point with
    no value: the chart shows a gap, because a line drawn through it would be an assertion
    nobody made.
    """
    series = []
    visible = _visibility(user)
    for period in _recent_periods(batch.period, spec.periods):
        entry = ({"batch_id": batch_id} if period == batch.period else
                 comparison_module.periods.latest_for(period, lambda item, period=period: visible(item) and
                                                      comparison_module.periods.same_series(item, batch.demo_case, period)))
        if entry is None:
            series.append({"period": period, "batch_id": "", "value": None, "unit": ""})
            continue
        other = batch if period == batch.period else load_batch(entry["batch_id"])
        value, unit = None, ""
        try:
            facts = business.context(entry["batch_id"], other)["facts"]
            fact = facts.get(spec.metric)
            if fact is not None:
                value, unit = fact["value"], fact["unit"]
        except Exception:  # noqa: BLE001 - a period that cannot be computed is a gap, not a zero
            value, unit = None, ""
        series.append({"period": period, "batch_id": entry["batch_id"], "value": value, "unit": unit})
    return series


def _recent_periods(period: str, count: int) -> list[str]:
    return [comparison_module.shift(period, offset) for offset in range(-(count - 1), 1)]


@router.get("/conclusions/batches/{batch_id}/report")
async def monthly_report(batch_id: str, user: Annotated[UserIdentity | None, Depends(require_user)],
                         report_id: Annotated[str | None, Query(pattern=r"^[a-f0-9]{32}$")] = None,
                         lang: Literal["zh", "en"] = "zh") -> dict:
    """The monthly report as a Word document (E13-UC04), worded in the interface's language.

    Generated from the brief, so it cannot say anything the page does not, and refused when
    that brief is stale: exporting superseded conclusions makes a document that outlives the
    data it was true of.
    """
    brief = await monthly_brief(batch_id, user, report_id)
    if brief.stale:
        raise HTTPException(409, "This brief is superseded by a newer review; rebuild it before exporting")
    batch = _visible(load_batch(batch_id), user)
    declared = conventions.views(batch.integration_snapshot or {})
    used = {key for metric in brief.key_metrics for key in
            (declaration(batch.dictionary_snapshot or {}).conventions.get(metric.metric, []))}
    filename, payload = report.build(
        brief.model_dump(mode="json"),
        # Only the conventions the reported figures actually rest on; the rest are not this
        # report's limitations (AC-2).
        conventions=[view.model_dump(mode="json") for view in declared if not used or view.id in used],
        case=str((batch.dictionary_snapshot or {}).get("business_review", {}).get("case", "")), language=lang)
    import base64

    return {"filename": filename, "base64": base64.b64encode(payload).decode(),
            "bound": brief.bound, "stale": False}


# --- quarters and years (#301) -------------------------------------------------------------

#: How many periods one side-by-side view may hold.
MAX_COLUMNS = 12


class _Anchor:
    """One batch's view of its series: its calendar, its declared metrics, and its months.

    The selected batch fixes everything a period view depends on, exactly as a month
    comparison does: which data series the earlier months come from (sample history never
    mixes with uploads), which declaration governs, and the month the view is "as of".
    """

    def __init__(self, batch_id: str, user: UserIdentity | None):
        self.batch_id = batch_id
        self.batch = _visible(load_batch(batch_id), user)
        self.declaration = self.batch.dictionary_snapshot or {}
        defined = (self.declaration.get("business_review") or {}).get("metrics") or {}
        if not defined:
            raise HTTPException(409, "No business review contract is declared for this batch; periods compare declared metrics only")
        self.defined = list(defined)
        self.calendar = Calendar.declared(self.declaration)
        visible = _visibility(user)

        def lookup(month: str):
            if month == self.batch.period:
                return batch_id, self.batch
            entry = comparison_module.periods.latest_for(month, lambda item: visible(item) and
                                                         comparison_module.periods.same_series(item, self.batch.demo_case, month))
            return (entry["batch_id"], load_batch(entry["batch_id"])) if entry else None

        self.months = aggregate.Months(lookup)

    def metrics(self, wanted: str | list[str] | None) -> list[str]:
        """The requested metrics, or the brief's key metrics; an unknown name is refused, not dropped."""
        names = [n.strip() for n in (wanted.split(",") if isinstance(wanted, str) else wanted or []) if n.strip()]
        if not names:
            try:
                return declaration(self.declaration).key_metrics
            except HTTPException:
                return self.defined
        unknown = [n for n in names if n not in self.defined]
        if unknown:
            raise HTTPException(422, f"Unknown metric {', '.join(unknown)}; declared: {', '.join(self.defined)}. "
                                     "Call again with one of these; do not invent names.")
        return list(dict.fromkeys(names))

    def current(self, unit: Grain) -> Period:
        return containing(self.batch.period, unit, self.calendar)


Base = Literal["prior", "last_year"]


@router.get("/conclusions/batches/{batch_id}/period-comparison", response_model=aggregate.PeriodComparison)
async def grain_comparison(batch_id: str, user: Annotated[UserIdentity | None, Depends(require_user)],
                           unit: Annotated[Grain, Query(alias="grain")] = "quarter",
                           base: Base = "prior", metrics: str | None = None) -> aggregate.PeriodComparison:
    """The month, quarter or year this batch falls in, against 环比 or 同比, as of this batch's month."""
    anchor = _Anchor(batch_id, user)
    return aggregate.compare(anchor.current(unit), as_of=anchor.batch.period, base_kind=base,
                             metrics=anchor.metrics(metrics), declaration=anchor.declaration, months=anchor.months)


@router.get("/conclusions/batches/{batch_id}/periods", response_model=aggregate.PeriodSeries)
async def period_series(batch_id: str, user: Annotated[UserIdentity | None, Depends(require_user)],
                        unit: Annotated[Grain, Query(alias="grain")] = "quarter",
                        periods: str | None = None, count: Annotated[int, Query(ge=2, le=MAX_COLUMNS)] = 4,
                        metrics: str | None = None) -> aggregate.PeriodSeries:
    """Periods side by side: the named ones (`periods=2024-Q1,2024-Q3`), or the last `count`.

    Nothing after this batch's month is shown: the view is as of the selected batch, so
    opening an older batch shows what was known then.
    """
    anchor = _Anchor(batch_id, user)
    current = anchor.current(unit)
    if periods:
        chosen = {parse(key.strip(), anchor.calendar) for key in periods.split(",") if key.strip()}
        if any(p.grain != unit for p in chosen):
            raise HTTPException(422, f"Every period must be a {unit}")
        if any(p.first > current.first for p in chosen):
            raise HTTPException(422, f"Periods after {current.key} are not known as of this batch")
        if not 2 <= len(chosen) <= MAX_COLUMNS:
            raise HTTPException(422, f"Choose 2–{MAX_COLUMNS} periods")
        columns = sorted(chosen, key=lambda p: p.first)
    else:
        columns = [current.shift(offset) for offset in range(-(count - 1), 1)]
    return aggregate.series(columns, as_of=anchor.batch.period, metrics=anchor.metrics(metrics),
                            declaration=anchor.declaration, months=anchor.months)


class ComparePeriodsRequest(BaseModel):
    batch_id: str
    grain: Grain = "quarter"
    base: Base = "prior"
    metrics: list[str] = Field(default_factory=list, max_length=24)


@router.post("/tools/compare-periods", response_model=aggregate.PeriodComparison)
async def compare_periods_tool(request: ComparePeriodsRequest,
                               user: Annotated[UserIdentity | None, Depends(require_user)]) -> aggregate.PeriodComparison:
    """The agent's read of the same comparison the page shows; it computes nothing itself."""
    anchor = _Anchor(request.batch_id, user)
    return aggregate.compare(anchor.current(request.grain), as_of=anchor.batch.period, base_kind=request.base,
                             metrics=anchor.metrics(request.metrics), declaration=anchor.declaration,
                             months=anchor.months)
