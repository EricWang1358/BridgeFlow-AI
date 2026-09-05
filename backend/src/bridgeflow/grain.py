"""Rolling source data onto a monthly axis without throwing the detail away.

Production is per day, procurement per week, finance per posting date. FR 09 asks
for one monthly axis — and asks for the original grain to survive, because an
approver who cannot see the daily rows cannot check the monthly figure.

How a measurement rolls up is a property of the measurement, not of the code: a
quantity sums, a price averages, a stock level takes the period-end value. Those
choices are declared in the field dictionary alongside everything else, because
getting one wrong is the kind of error that produces a plausible number.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from pydantic import BaseModel, Field

from bridgeflow.agents.semantic_resolver import FieldDictionary
from bridgeflow.schemas import CleanTable, SourceRef

#: How a measurement combines when several periods roll into one.
ROLLUPS = ("sum", "average", "period_end")

#: Used when the dictionary does not say. Sum is the honest default for a quantity
#: and wrong for a price, which is why the dictionary is asked first and a
#: disagreement is reported rather than silently resolved.
DEFAULT_ROLLUP = "sum"


class MonthlyValue(BaseModel):
    measure: str
    month: str
    value: float
    rollup: str
    #: The periods that were combined, so the monthly figure can be opened up.
    contributing: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    source_count: int = 0


class GrainConflict(Exception):
    """Two rows claim the same measurement for the same month with different rollups."""


def month_of(value: object) -> str | None:
    """The month a date-ish value belongs to, or None when it is not a date.

    Accepts what the sanitizer produces (ISO strings) and what a caller might still
    be holding (dates, timestamps). Anything else is not a date, and guessing is how
    a row ends up counted in the wrong month.
    """
    if isinstance(value, (datetime, date)):
        return f"{value.year:04d}-{value.month:02d}"
    if isinstance(value, str):
        text = value.strip()
        if len(text) >= 7 and text[4] == "-" and text[:4].isdigit() and text[5:7].isdigit():
            return text[:7]
    return None


def rollup_for(dictionary: FieldDictionary, measure: str) -> str:
    """How this measurement combines across periods."""
    declared = getattr(dictionary, "rollups", {}).get(measure)
    if declared in ROLLUPS:
        return declared
    return DEFAULT_ROLLUP


def to_monthly(
    tables: list[CleanTable],
    dictionary: FieldDictionary,
    *,
    date_column_by_department: dict[str, str] | None = None,
) -> tuple[list[MonthlyValue], list[str]]:
    """Roll every declared measurement onto months.

    Returns the monthly values and the rows that could not be placed on the axis at
    all. An unplaceable row is reported rather than dropped or dumped into the
    period the table happens to be labelled with: a row with no readable date is
    unknown, not "this month".
    """
    buckets: dict[tuple[str, str], list[tuple[float, SourceRef]]] = defaultdict(list)
    unplaced: list[str] = []

    for table in tables:
        date_column = (date_column_by_department or {}).get(table.department) or _date_column(table)
        for index, row in enumerate(table.rows):
            month = month_of(row.get(date_column)) if date_column else None
            if month is None:
                unplaced.append(
                    f"{table.department} row {index}: no readable date in "
                    f"{date_column or 'any column'}"
                )
                continue
            for column, value in row.items():
                measure = dictionary.measure_for(table.department, column)
                if measure is None:
                    continue
                number = _as_number(value)
                if number is None:
                    continue
                buckets[(measure, month)].append(
                    (
                        number,
                        SourceRef(
                            department=table.department,
                            period=table.period,
                            row=index,
                            column=column,
                        ),
                    )
                )

    values = []
    for (measure, month), entries in sorted(buckets.items()):
        rollup = rollup_for(dictionary, measure)
        numbers = [n for n, _ in entries]
        combined = {
            "sum": sum(numbers),
            "average": sum(numbers) / len(numbers),
            "period_end": numbers[-1],
        }[rollup]
        values.append(
            MonthlyValue(
                measure=measure,
                month=month,
                value=round(combined, 4),
                rollup=rollup,
                contributing=sorted({ref.period for _, ref in entries}),
                sources=[ref for _, ref in entries[:5]],
                source_count=len(entries),
            )
        )
    return values, unplaced


def _date_column(table: CleanTable) -> str | None:
    """The column holding this table's dates, by declared type rather than by name."""
    return next((c.name for c in table.columns if c.dtype == "date"), None)


def _as_number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None
