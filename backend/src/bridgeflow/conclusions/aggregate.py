"""Declared metrics over a quarter or a year, read back from their months (#301).

A quarter's figure is not the average of three monthly figures. Every declared metric is
an arithmetic tree over table leaves (`business.expression`); a quarter evaluates the same
tree, with each leaf added up across the quarter's month batches *before* the arithmetic
runs. A margin is therefore Σprofit ÷ Σrevenue, recomputed from its parts.

Adding a leaf up across months is only right for a flow (revenue, volume). A balance
(closing balance, anything cumulative) at the end of a quarter is its last month's
balance, and a price summed over months is meaningless. Which is which is the company's
declaration, per department and measure:

    business_review.period_aggregation:
      measures: {finance: {revenue: flow, closing_balance: period_end, ...}, ...}
      month_only: {receivable_months: "<why this metric has no quarterly meaning>"}

- `flow`        summed across the months present
- `period_end`  read from the latest month present (`as_of` says which)
- `rate`        only inside a `sum_product` beside one flow or period-end measure
                (Σ volume × unit margin is an amount; Σ unit margin is nothing)

Anything undeclared is refused for quarters and years, never defaulted: a summed balance
looks exactly like a correct figure. A metric whose formula itself changes meaning over a
longer period (a balance over *monthly* billing) is declared `month_only` with the reason.

Partial periods are reported as they are: the months present, the months that should be
and are not, and the ones whose batch cannot be reviewed — never extrapolated, never
zero-filled. Comparisons are like for like: a quarter with two months is compared with the
same two months of the base quarter, or not at all.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import chain, pairwise, zip_longest
from math import isfinite
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

from bridgeflow import business
from bridgeflow.conclusions.comparison import POINT_UNITS, _delta
from bridgeflow.conclusions.grain import Grain, Period

Kind = Literal["flow", "period_end", "rate"]
KINDS = ("flow", "period_end", "rate")
FactState = Literal["computed", "no_data", "month_only", "aggregation_undeclared",
                    "declaration_changed", "not_computable"]
#: Same bound as `business.expression`: a sample of contributing cells, never all of them.
SOURCE_SAMPLE = 5


@dataclass(frozen=True)
class Aggregation:
    measures: dict[str, dict[str, Kind]] = field(default_factory=dict)
    month_only: dict[str, str] = field(default_factory=dict)

    @classmethod
    def declared(cls, dictionary: dict | None) -> Aggregation:
        raw = (((dictionary or {}).get("business_review") or {}).get("period_aggregation") or {})
        measures, month_only = raw.get("measures") or {}, raw.get("month_only") or {}
        invalid = HTTPException(503, "business_review.period_aggregation is invalid: measures map department → "
                                     f"measure → one of {', '.join(KINDS)}, and month_only maps metric → reason; "
                                     "ask the dictionary owner to correct it")
        if not isinstance(measures, dict) or not isinstance(month_only, dict):
            raise invalid
        for kinds in measures.values():
            if not isinstance(kinds, dict) or any(kind not in KINDS for kind in kinds.values()):
                raise invalid
        if any(not isinstance(reason, str) or not reason.strip() for reason in month_only.values()):
            raise invalid
        return cls(measures, month_only)

    def leaf_kind(self, node: dict) -> Literal["flow", "period_end"]:
        """How one table leaf adds up across months, or a refusal naming what is undeclared."""
        department = str(node.get("department", ""))
        names = node.get("measures") or []
        kinds = [self.measures.get(department, {}).get(name) for name in names]
        undeclared = [name for name, kind in zip(names, kinds, strict=True) if kind is None]
        if undeclared:
            raise _Refused("aggregation_undeclared",
                           f"{department}: {', '.join(undeclared)} declare(s) no period aggregation "
                           "(flow, period_end or rate); a quarter or year is not computed by guessing")
        flows, ends = kinds.count("flow"), kinds.count("period_end")
        if flows + ends != 1:
            raise _Refused("aggregation_undeclared",
                           f"{department}: {' × '.join(names)} must carry exactly one flow or period-end "
                           "measure, the others rates; this combination has no meaning across months")
        return "flow" if flows else "period_end"


class _Refused(Exception):
    def __init__(self, state: FactState, reason: str):
        super().__init__(reason)
        self.state, self.reason = state, reason


@dataclass(frozen=True)
class Month:
    month: str
    batch_id: str
    batch: Any
    #: `business.context` facts: the month's own figures, under its own frozen declaration.
    facts: dict


class Months:
    """Reads each month once per request: the batch, and whether it can be reviewed at all."""

    def __init__(self, lookup: Callable[[str], tuple[str, Any] | None]):
        self._lookup = lookup
        self._seen: dict[str, Month | str | None] = {}

    def read(self, month: str) -> Month | str | None:
        """The month, the reason it cannot be used, or None when nothing was imported."""
        if month not in self._seen:
            found = self._lookup(month)
            if found is None:
                self._seen[month] = None
            else:
                batch_id, batch = found
                try:
                    self._seen[month] = Month(month, batch_id, batch, business.context(batch_id, batch)["facts"])
                except HTTPException as exc:
                    self._seen[month] = str(exc.detail)
        return self._seen[month]


class Coverage(BaseModel):
    #: Every month of the period, and the ones this view looks at (up to the anchor month).
    months: list[str]
    considered: list[str]
    present: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    #: Imported, but the batch cannot be reviewed; the review's own refusal is kept.
    unusable: dict[str, str] = Field(default_factory=dict)
    batch_ids: dict[str, str] = Field(default_factory=dict)
    #: Every month of the period is present and usable — the only state a total is final in.
    complete: bool = False


class PeriodFact(BaseModel):
    metric: str
    unit: str = ""
    formula: str = ""
    value: float | None = None
    state: FactState
    reason: str = ""
    #: The month a period-end leaf was read from; empty when the metric has none.
    as_of: str = ""
    sources: list[dict] = Field(default_factory=list)
    source_count: int = 0
    truncated: bool = False


class PeriodFacts(BaseModel):
    grain: Grain
    period: str
    coverage: Coverage
    facts: list[PeriodFact]


def _definition(declaration: dict, metric: str) -> dict:
    return (((declaration or {}).get("business_review") or {}).get("metrics") or {})[metric]


def _spread(values: list[business.Value]) -> list:
    """A source sample that shows every month rather than filling up on the first."""
    return [ref for ref in chain.from_iterable(zip_longest(*(v.sources for v in values))) if ref][:SOURCE_SAMPLE]


def _fact(metric: str, spec: dict, period: Period, present: list[Month], aggregation: Aggregation) -> PeriodFact:
    base = {"metric": metric, "unit": spec.get("unit", ""), "formula": spec.get("formula", "")}
    if not present:
        return PeriodFact(**base, state="no_data", reason=f"No reviewable batch for any month of {period.key}")
    if period.grain == "month":
        fact = present[0].facts.get(metric)
        if fact is None:
            return PeriodFact(**base, state="declaration_changed",
                              reason=f"{present[0].month} does not declare {metric}")
        return PeriodFact(**base, value=fact["value"], state="computed", sources=fact["sources"],
                          source_count=fact["source_count"], truncated=fact["truncated"])
    if metric in aggregation.month_only:
        return PeriodFact(**base, state="month_only", reason=aggregation.month_only[metric])
    changed = [m.month for m in present if _month_definition(m, metric) != spec]
    if changed:
        return PeriodFact(**base, state="declaration_changed",
                          reason=f"{metric} is declared differently in {', '.join(changed)}; "
                                 "adding the months up would mix two formulas")
    as_of = ""

    def leaf(node: dict) -> business.Value:
        nonlocal as_of
        if aggregation.leaf_kind(node) == "period_end":
            as_of = present[-1].month
            return business.expression(node, present[-1].batch)
        values = [business.expression(node, m.batch) for m in present]
        return business.Value(sum((v.number for v in values), Decimal(0)), _spread(values), sum(v.count for v in values))

    try:
        result = business.expression(spec["expression"], None, leaf=leaf)
    except _Refused as refused:
        return PeriodFact(**base, state=refused.state, reason=refused.reason)
    except HTTPException as exc:
        return PeriodFact(**base, state="not_computable", reason=str(exc.detail))
    if not isfinite(float(result.number)):
        return PeriodFact(**base, state="not_computable", reason="The result is outside the supported numeric range")
    return PeriodFact(**base, value=float(round(result.number, 4)), state="computed", as_of=as_of,
                      sources=[ref.model_dump() for ref in result.sources], source_count=result.count,
                      truncated=result.count > len(result.sources))


def _month_definition(month: Month, metric: str) -> dict | None:
    try:
        return _definition(month.batch.dictionary_snapshot, metric)
    except KeyError:
        return None


def period_facts(period: Period, considered: list[str], *, metrics: list[str], declaration: dict,
                 months: Months) -> PeriodFacts:
    """The declared metrics over the given months of one period. Reads only."""
    aggregation = Aggregation.declared(declaration)
    coverage = Coverage(months=period.months(), considered=considered)
    present: list[Month] = []
    for month in considered:
        found = months.read(month)
        if found is None:
            coverage.missing.append(month)
        elif isinstance(found, str):
            coverage.unusable[month] = found
        else:
            present.append(found)
            coverage.present.append(month)
            coverage.batch_ids[month] = found.batch_id
    coverage.complete = coverage.present == coverage.months
    facts = [_fact(metric, _definition(declaration, metric), period, present, aggregation) for metric in metrics]
    return PeriodFacts(grain=period.grain, period=period.key, coverage=coverage, facts=facts)


class PeriodChange(BaseModel):
    metric: str
    unit: str = ""
    current: float | None = None
    base: float | None = None
    absolute: float | None = None
    relative: float | None = None
    #: "value", or "percentage_points" for a metric that is already a ratio (as month comparisons).
    basis: str = "value"
    #: "compared" | "not_computable" | "incomplete" | "missing_in_base" | a fact state of the current side
    state: str
    reason: str = ""
    #: Set in a series, where each change is between two named columns.
    from_period: str = ""
    to_period: str = ""


def _change(metric: str, current: PeriodFact, base: PeriodFact) -> PeriodChange:
    if current.state != "computed":
        return PeriodChange(metric=metric, unit=current.unit, state=current.state, reason=current.reason)
    if base.state != "computed":
        return PeriodChange(metric=metric, unit=current.unit, current=current.value, state="missing_in_base",
                            reason=base.reason)
    absolute, relative, state = _delta(current.value, base.value)
    points = current.unit in POINT_UNITS
    return PeriodChange(metric=metric, unit=current.unit, current=current.value, base=base.value,
                        absolute=absolute, relative=None if points else relative,
                        basis="percentage_points" if points else "value",
                        state="compared" if points and absolute is not None else state)


class PeriodComparison(BaseModel):
    grain: Grain
    period: str
    base_kind: Literal["prior", "last_year"]
    base_period: str
    #: "compared" | "no_data" | "no_base" | "base_incomplete"
    status: str
    reason: str = ""
    current: PeriodFacts
    base: PeriodFacts | None = None
    changes: list[PeriodChange] = Field(default_factory=list)


def compare(period: Period, *, as_of: str, base_kind: Literal["prior", "last_year"], metrics: list[str],
            declaration: dict, months: Months) -> PeriodComparison:
    """One period against 环比 (prior) or 同比 (last_year), month for month."""
    considered = [m for m in period.months() if m <= as_of]
    current = period_facts(period, considered, metrics=metrics, declaration=declaration, months=months)
    base_period = period.prior() if base_kind == "prior" else period.last_year()
    result = PeriodComparison(grain=period.grain, period=period.key, base_kind=base_kind,
                              base_period=base_period.key, status="compared", current=current)
    if not current.coverage.present:
        result.status, result.reason = "no_data", f"No reviewable batch for {period.key} up to {as_of}"
        return result
    # Like for like: the base contributes the same positions of its period that the current side has.
    positions = [period.months().index(m) for m in current.coverage.present]
    aligned = [base_period.months()[i] for i in positions]
    result.base = period_facts(base_period, aligned, metrics=metrics, declaration=declaration, months=months)
    if result.base.coverage.present != aligned:
        absent = result.base.coverage.missing + list(result.base.coverage.unusable)
        result.status = "base_incomplete" if result.base.coverage.present else "no_base"
        result.reason = (f"{base_period.key} lacks {', '.join(sorted(absent))}, which {period.key} has; "
                         "a comparison over different months would not be like for like")
        return result
    base_facts = {fact.metric: fact for fact in result.base.facts}
    result.changes = [_change(fact.metric, fact, base_facts[fact.metric]) for fact in current.facts]
    return result


class PeriodSeries(BaseModel):
    grain: Grain
    as_of: str
    columns: list[PeriodFacts]
    #: Between each pair of neighbouring columns, only when both are complete periods.
    changes: list[PeriodChange] = Field(default_factory=list)


def series(periods: list[Period], *, as_of: str, metrics: list[str], declaration: dict,
           months: Months) -> PeriodSeries:
    """Several periods side by side, each with its coverage, and the change between neighbours."""
    columns = [period_facts(p, [m for m in p.months() if m <= as_of], metrics=metrics,
                            declaration=declaration, months=months) for p in periods]
    changes = []
    for before, after in pairwise(columns):
        prior = {fact.metric: fact for fact in before.facts}
        for fact in after.facts:
            if not (before.coverage.complete and after.coverage.complete):
                incomplete = [c.period for c in (before, after) if not c.coverage.complete]
                change = PeriodChange(metric=fact.metric, unit=fact.unit, state="incomplete",
                                      reason=f"{', '.join(incomplete)} is not complete; totals of "
                                             "different lengths are not compared")
            else:
                change = _change(fact.metric, fact, prior[fact.metric])
            changes.append(change.model_copy(update={"from_period": before.period, "to_period": after.period}))
    grain = periods[0].grain if periods else "month"
    return PeriodSeries(grain=grain, as_of=as_of, columns=columns, changes=changes)
