"""This month against a base period (E13-UC02).

A single month's figure rarely means anything on its own: 85% collected is good or bad
depending on last month. This module aligns the current batch with a base period and
reports what changed, without recomputing any business rule of its own — declared review
metrics come from `business.context`, master cells from the frozen integration
declaration, and which master fields may be added up across projects is declared too.

Refusals are explicit and distinguishable, because each means something different to a
reader (docs/requirements/13-conclusions.md, decisions D1-D5):

- `no_base`        nothing was imported for the base period; never shown as 0 or -100%
- `base_unusable`  the base batch exists but cannot be read the same way (its own reason)
- `declaration_changed` the two periods declare different fields, so a delta would
  compare two different things; the differing field names are listed
- a single figure with a zero base is `not_computable`, not an infinite percentage
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from fastapi import HTTPException
from pydantic import BaseModel, Field

from bridgeflow import business
from bridgeflow.conclusions import periods


def shift(period: str, months: int) -> str:
    year, month = (int(part) for part in period.split("-"))
    index = year * 12 + (month - 1) + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


class BasePeriod(Protocol):
    id: str

    def period_for(self, current: str) -> str | None:
        """The period to compare against, or None when this base is not available."""

    def unavailable(self) -> str:
        """Why it is not available, when `period_for` returns None."""


@dataclass(frozen=True)
class PriorMonth:
    id: str = "prior_month"

    def period_for(self, current: str) -> str | None:
        return shift(current, -1)

    def unavailable(self) -> str:
        return ""


@dataclass(frozen=True)
class SameMonthLastYear:
    id: str = "last_year"

    def period_for(self, current: str) -> str | None:
        return shift(current, -12)

    def unavailable(self) -> str:
        return ""


@dataclass(frozen=True)
class DeclaredPlan:
    """Plan values need a declared source; there is none yet, so this refuses (D5)."""

    id: str = "plan"

    def period_for(self, current: str) -> str | None:
        return None

    def unavailable(self) -> str:
        return "No plan source is declared; the business side has not supplied plan values"


BASES: dict[str, BasePeriod] = {b.id: b for b in (PriorMonth(), SameMonthLastYear(), DeclaredPlan())}


class MetricChange(BaseModel):
    metric: str
    unit: str
    current: float
    base: float | None = None
    absolute: float | None = None
    relative: float | None = None
    #: "value" for amounts and quantities, "percentage_points" for a metric already a ratio (D7)
    basis: str = "value"
    #: "compared" | "no_base" | "not_computable" | "missing_in_base"
    state: str


class EntityChange(BaseModel):
    key: list[str]
    field: str
    current: float | None = None
    base: float | None = None
    absolute: float | None = None
    relative: float | None = None
    state: str
    breach: str = ""


class FieldTotals(BaseModel):
    field: str
    current: float
    base: float
    absolute: float
    relative: float | None = None
    #: new + discontinued + continuing == absolute (checked by test, D3)
    new_entities: float
    discontinued: float
    continuing: float


class Comparison(BaseModel):
    base_kind: str
    base_period: str = ""
    base_batch_id: str = ""
    status: str  # "compared" | "no_base" | "base_unusable" | "declaration_changed" | "unavailable"
    reason: str = ""
    changed_fields: list[str] = Field(default_factory=list)
    metrics: list[MetricChange] = Field(default_factory=list)
    totals: list[FieldTotals] = Field(default_factory=list)
    entities: list[EntityChange] = Field(default_factory=list)
    breaches: list[EntityChange] = Field(default_factory=list)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _delta(current: float | None, base: float | None) -> tuple[float | None, float | None, str]:
    if current is None or base is None:
        return None, None, "missing_in_base" if current is not None else "missing"
    absolute = float(Decimal(str(current)) - Decimal(str(base)))
    if base == 0:
        return absolute, None, "not_computable"
    return absolute, absolute / abs(base), "compared"


def declaration_differences(current: dict | None, base: dict | None) -> list[str]:
    """Field declarations that are not the same in both periods (D2).

    Version strings may differ for reasons that do not touch a field (a comment, a new
    convention); what makes a delta meaningless is a field whose declaration changed.
    """
    left = (current or {}).get("fields") or {}
    right = (base or {}).get("fields") or {}
    names = set(left) | set(right)
    return sorted(name for name in names if left.get(name) != right.get(name))


def entity_axis(snapshot: dict | None) -> list[int]:
    """Positions of the master key that identify the entity, not the period (D6).

    The master's grain includes the report period, which is the axis a comparison moves
    along: keeping it in the key would make every row look new. The period field is the
    grain field a department supplies as a period (`period_from`), so this is read from
    the declaration rather than named in code.
    """
    spec = snapshot or {}
    grain, fields = spec.get("grain") or [], spec.get("fields") or {}
    axis = []
    for index, name in enumerate(grain):
        sources = (fields.get(name) or {}).get("sources") or {}
        if not any((ref or {}).get("period_from") for ref in sources.values()):
            axis.append(index)
    return axis or list(range(len(grain)))


@dataclass
class _Master:
    rows: dict[tuple[str, ...], dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def of(cls, result, axis: list[int]) -> _Master:
        return cls({tuple(row.key[i] for i in axis if i < len(row.key)): row.values for row in result.rows})


#: Units whose values are already ratios: their change is in points, and a ratio of two
#: ratios ("-679%" from 0.09% to -0.5%) says nothing a reader can use (D7).
POINT_UNITS = ("%", "‰")


def compare_metrics(current_facts: dict, base_facts: dict, wanted: list[str]) -> list[MetricChange]:
    changes = []
    for name in wanted:
        fact = current_facts.get(name)
        if fact is None:
            continue
        base = base_facts.get(name)
        absolute, relative, state = _delta(fact["value"], base["value"] if base else None)
        points = fact["unit"] in POINT_UNITS
        changes.append(MetricChange(metric=name, unit=fact["unit"], current=fact["value"],
                                    base=base["value"] if base else None, absolute=absolute,
                                    relative=None if points else relative,
                                    basis="percentage_points" if points else "value",
                                    state="compared" if points and absolute is not None else state))
    return changes


def compare_master(current, base, additive: list[str], thresholds: dict[str, dict],
                   axis: list[int]) -> tuple[list[FieldTotals], list[EntityChange], list[EntityChange]]:
    """Per-entity changes for declared additive fields, with totals decomposed (D3).

    Only fields the declaration marks additive are totalled: adding a unit price or a
    ratio across projects produces a number with no meaning. Ratios stay per entity.
    """
    here, there = _Master.of(current, axis).rows, _Master.of(base, axis).rows
    entities, breaches, totals = [], [], []
    for name in additive:
        new_sum = gone_sum = continuing_sum = current_sum = base_sum = 0.0
        for key in sorted(set(here) | set(there)):
            value = _number(here.get(key, {}).get(name))
            was = _number(there.get(key, {}).get(name))
            absolute, relative, state = _delta(value, was)
            current_sum += value or 0.0
            base_sum += was or 0.0
            if value is not None and was is None:
                new_sum += value
            elif value is None and was is not None:
                gone_sum -= was
            elif value is not None and was is not None:
                continuing_sum += absolute or 0.0
            change = EntityChange(key=list(key), field=name, current=value, base=was,
                                  absolute=absolute, relative=relative, state=state)
            rule = thresholds.get(name) or {}
            below, above = rule.get("relative_below"), rule.get("relative_above")
            if relative is not None and below is not None and relative <= below:
                change.breach = "relative_below"
            elif relative is not None and above is not None and relative >= above:
                change.breach = "relative_above"
            entities.append(change)
            if change.breach:
                breaches.append(change)
        totals.append(FieldTotals(field=name, current=current_sum, base=base_sum,
                                  absolute=current_sum - base_sum,
                                  relative=(current_sum - base_sum) / abs(base_sum) if base_sum else None,
                                  new_entities=new_sum, discontinued=gone_sum, continuing=continuing_sum))
    return totals, entities, breaches


def build(*, batch_id: str, batch, base_kind: str, metrics: list[str], master,
          load_batch, master_for, visible) -> Comparison:
    """Compare one batch against a base period. Reads only; writes nothing."""
    base = BASES.get(base_kind)
    if base is None:
        raise HTTPException(422, "Unknown comparison base")
    period = base.period_for(batch.period)
    if period is None:
        return Comparison(base_kind=base_kind, status="unavailable", reason=base.unavailable())
    found = periods.latest_for(period, lambda item: visible(item) and
                               periods.same_series(item, getattr(batch, "demo_case", None), period))
    if found is None:
        return Comparison(base_kind=base_kind, base_period=period, status="no_base",
                          reason=f"No batch has been imported for {period}")
    base_batch = load_batch(found["batch_id"])
    changed = declaration_differences(batch.integration_snapshot, base_batch.integration_snapshot)
    if changed:
        return Comparison(base_kind=base_kind, base_period=period, base_batch_id=found["batch_id"],
                          status="declaration_changed", changed_fields=changed,
                          reason="The two periods declare different fields; a change would compare different things")
    try:
        base_context = business.context(found["batch_id"], base_batch)
    except HTTPException as exc:
        return Comparison(base_kind=base_kind, base_period=period, base_batch_id=found["batch_id"],
                          status="base_unusable", reason=str(exc.detail))
    current_context = business.context(batch_id, batch)
    spec = (batch.integration_snapshot or {}).get("comparison") or {}
    totals, entities, breaches = ([], [], [])
    if master is not None:
        base_master = master_for(found["batch_id"])
        if base_master is not None:
            totals, entities, breaches = compare_master(master, base_master, spec.get("additive", []),
                                                        spec.get("thresholds", {}),
                                                        entity_axis(batch.integration_snapshot))
    return Comparison(base_kind=base_kind, base_period=period, base_batch_id=found["batch_id"], status="compared",
                      metrics=compare_metrics(current_context["facts"], base_context["facts"], metrics),
                      totals=totals, entities=entities, breaches=breaches)
