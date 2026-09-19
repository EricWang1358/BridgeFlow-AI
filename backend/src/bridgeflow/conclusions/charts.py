"""Declared charts over declared numbers (E13-UC03).

A chart is a claim about data, so which charts exist is declared (`business_review.charts`)
next to the metrics they draw, not chosen by a model at request time. This module turns a
declaration into points and nothing else: no chart keeps its own copy of a value, every
point carries the batch it came from so a reader can drill to the source, and the same
points serve the chart and the table beside it — the table cannot disagree with the picture
because there is only one set of numbers.

Three kinds, each refusing rather than implying something it cannot show:

- `trend`    a metric across periods. Fewer than two periods is an explanation, not a line
             with one dot; a period with no batch is a gap, never interpolated.
- `variance` one additive field's change against a base period, decomposed into new,
             discontinued and continuing entities (E13-UC02), which sum to the total.
- `entity_bars` this period's value per entity for one declared field, largest first,
             marking the entities that breach a declared threshold.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Status = Literal["ready", "needs_more_periods", "unavailable"]


class ChartSpec(BaseModel):
    id: str
    kind: Literal["trend", "variance", "entity_bars"]
    #: A declared metric (trend) or a declared master field (variance, entity_bars).
    metric: str = ""
    field: str = ""
    periods: int = Field(default=6, ge=2, le=24)
    #: Draw the threshold of this declared check beside the line.
    threshold_from_check: str = ""
    base: str = "prior_month"
    top: int = Field(default=8, ge=1, le=50)


class Point(BaseModel):
    label: str
    value: float | None = None
    #: Where this point came from, so clicking it can open the source.
    batch_id: str = ""
    period: str = ""
    key: list[str] = Field(default_factory=list)
    #: For a waterfall: whether the part adds to or subtracts from the total.
    part: str = ""
    breach: bool = False


class Chart(BaseModel):
    id: str
    kind: str
    status: Status = "ready"
    #: What the chart is about, as declared: the metric or field name. Never a sentence
    #: written here — the interface writes the conclusion title from these parts.
    subject: str = ""
    unit: str = ""
    points: list[Point] = Field(default_factory=list)
    threshold: float | None = None
    threshold_label: str = ""
    reason: str = ""


def declared(dictionary: dict | None) -> list[ChartSpec]:
    raw = ((dictionary or {}).get("business_review") or {}).get("charts") or []
    specs = []
    for item in raw:
        if isinstance(item, dict) and item.get("kind") in ("trend", "variance", "entity_bars"):
            specs.append(ChartSpec.model_validate(item))
    return specs


def _threshold(dictionary: dict | None, check_id: str) -> tuple[float | None, str]:
    for check in ((dictionary or {}).get("business_review") or {}).get("checks") or []:
        if check.get("id") == check_id and "threshold" in check:
            return float(check["threshold"]), str(check.get("attention_when", ""))
    return None, ""


def trend(spec: ChartSpec, dictionary: dict | None, series: list[dict]) -> Chart:
    """`series` is one entry per period, newest last: {period, batch_id, value, unit}."""
    unit = next((str(item.get("unit", "")) for item in series if item.get("value") is not None), "")
    points = [Point(label=str(item["period"]), period=str(item["period"]), batch_id=str(item.get("batch_id", "")),
                    value=None if item.get("value") is None else float(item["value"])) for item in series]
    measured = [p for p in points if p.value is not None]
    threshold, when = _threshold(dictionary, spec.threshold_from_check or spec.metric)
    chart = Chart(id=spec.id, kind="trend", subject=spec.metric, unit=unit, points=points,
                  threshold=threshold, threshold_label=when)
    if len(measured) < 2:
        chart.status = "needs_more_periods"
        chart.reason = "A trend needs at least two periods with a batch; a single point is not a line"
    if threshold is not None:
        for point in measured:
            point.breach = point.value > threshold if when == "above" else point.value < threshold
    return chart


def variance(spec: ChartSpec, comparison: Any, *, batch_id: str = "", period: str = "") -> Chart:
    """The waterfall of one additive field: base → new, discontinued, continuing → current."""
    chart = Chart(id=spec.id, kind="variance", subject=spec.field)
    if comparison is None or getattr(comparison, "status", "") != "compared":
        chart.status = "unavailable"
        chart.reason = getattr(comparison, "reason", "") or "No comparable base period"
        return chart
    total = next((t for t in comparison.totals if t.field == spec.field), None)
    if total is None:
        chart.status = "unavailable"
        chart.reason = f"{spec.field} is not declared as an additive field for comparison"
        return chart
    chart.points = [
        Point(label="base", value=float(total.base), period=comparison.base_period, batch_id=comparison.base_batch_id, part="start"),
        Point(label="new_entities", value=float(total.new_entities), part="delta"),
        Point(label="discontinued", value=float(total.discontinued), part="delta"),
        Point(label="continuing", value=float(total.continuing), part="delta"),
        Point(label="current", value=float(total.current), period=period, batch_id=batch_id, part="end"),
    ]
    return chart


def entity_bars(spec: ChartSpec, master: Any, breaches: list[Any] | None = None,
                axis: list[int] | None = None) -> Chart:
    """This period's value per entity, largest first. Only declared fields; no ranking invented.

    `axis` is the entity part of the master key (E13-UC02 D6): a breach is reported against the
    entity, while the point keeps the full key so a click lands on this period's row.
    """
    chart = Chart(id=spec.id, kind="entity_bars", subject=spec.field)
    if master is None or spec.field not in getattr(master, "columns", []):
        chart.status = "unavailable"
        chart.reason = f"{spec.field} is not a column of this batch's master table"
        return chart
    breached = {tuple(b.key) for b in (breaches or []) if getattr(b, "field", "") == spec.field}
    rows = []
    for row in master.rows:
        value = row.values.get(spec.field)
        if isinstance(value, int | float):
            entity = tuple(row.key[i] for i in axis if i < len(row.key)) if axis else tuple(row.key)
            rows.append(Point(label=" · ".join(row.key[:2]), value=float(value), key=list(row.key),
                              breach=entity in breached))
    rows.sort(key=lambda p: abs(p.value or 0), reverse=True)
    chart.points = rows[:spec.top]
    if not rows:
        chart.status = "unavailable"
        chart.reason = f"No numeric values for {spec.field} in this batch"
    return chart
