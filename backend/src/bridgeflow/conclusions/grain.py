"""Months, quarters and years as periods of one calendar (#301).

Data arrives one month per batch and stays that way: a quarter or a year is never stored,
it is a list of months read back from their own batches. This module only says which
months a period is made of and which period comes before it — no figure is computed here.

The calendar is declared (`business_review.calendar.fiscal_year_start_month`), because
whether a year starts in January is the company's convention, not something to infer.
Under the default the keys are the familiar `2024`, `2024-Q3`; a fiscal year that starts
in another month is written `FY2024`, `FY2024-Q1`, named after the calendar year it starts
in, so the two kinds of key can never be mistaken for each other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException

Grain = Literal["month", "quarter", "year"]
GRAINS: tuple[Grain, ...] = ("month", "quarter", "year")
#: How many months one period of each grain spans.
SPAN = {"month": 1, "quarter": 3, "year": 12}

MONTH = re.compile(r"^(\d{4})-(\d{2})$")
QUARTER = re.compile(r"^(FY)?(\d{4})-Q([1-4])$")
YEAR = re.compile(r"^(FY)?(\d{4})$")


def _index(month: str) -> int:
    """Months since year 0, so shifting never has to think about December."""
    match = MONTH.match(month)
    if not match or not 1 <= int(match.group(2)) <= 12:
        raise HTTPException(422, f"Not a month: {month!r}; expected YYYY-MM")
    return int(match.group(1)) * 12 + int(match.group(2)) - 1


def _month(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


@dataclass(frozen=True)
class Calendar:
    fiscal_year_start_month: int = 1

    @classmethod
    def declared(cls, dictionary: dict | None) -> Calendar:
        raw = (((dictionary or {}).get("business_review") or {}).get("calendar") or {})
        start = raw.get("fiscal_year_start_month", 1)
        if isinstance(start, bool) or not isinstance(start, int) or not 1 <= start <= 12:
            raise HTTPException(503, "business_review.calendar.fiscal_year_start_month must be a month number "
                                     "1–12; ask the dictionary owner to correct it")
        return cls(start)

    @property
    def prefix(self) -> str:
        return "" if self.fiscal_year_start_month == 1 else "FY"


#: January to December, the default when no fiscal year is declared.
CALENDAR_YEAR = Calendar()


@dataclass(frozen=True)
class Period:
    grain: Grain
    #: Index of the period's first month (see `_index`).
    first: int
    calendar: Calendar = CALENDAR_YEAR

    @property
    def key(self) -> str:
        if self.grain == "month":
            return _month(self.first)
        year, offset = divmod(self.first - (self.calendar.fiscal_year_start_month - 1), 12)
        if self.grain == "year":
            return f"{self.calendar.prefix}{year:04d}"
        return f"{self.calendar.prefix}{year:04d}-Q{offset // 3 + 1}"

    def months(self) -> list[str]:
        return [_month(self.first + i) for i in range(SPAN[self.grain])]

    def shift(self, periods: int) -> Period:
        return Period(self.grain, self.first + periods * SPAN[self.grain], self.calendar)

    def prior(self) -> Period:
        """环比: the period immediately before, at the same grain."""
        return self.shift(-1)

    def last_year(self) -> Period:
        """同比: the same period one year earlier."""
        return Period(self.grain, self.first - 12, self.calendar)


def containing(month: str, grain: Grain, calendar: Calendar = CALENDAR_YEAR) -> Period:
    """The period of this grain that the month falls in."""
    index = _index(month)
    if grain == "month":
        return Period("month", index, calendar)
    start = calendar.fiscal_year_start_month - 1
    offset = (index - start) % 12
    within = offset if grain == "year" else offset % 3
    return Period(grain, index - within, calendar)


def parse(key: str, calendar: Calendar = CALENDAR_YEAR) -> Period:
    """A period key back into a period, refusing keys of another calendar."""
    if MONTH.match(key):
        return Period("month", _index(key), calendar)
    patterns: tuple[tuple[Grain, re.Pattern[str]], ...] = (("quarter", QUARTER), ("year", YEAR))
    for grain, pattern in patterns:
        match = pattern.match(key)
        if not match:
            continue
        if (match.group(1) or "") != calendar.prefix:
            written = "with FY, as fiscal years" if calendar.prefix else "without FY, as calendar years"
            raise HTTPException(422, f"{key!r} is not a period of this calendar; its years are written {written}")
        year = int(match.group(2))
        quarter = int(match.group(3)) if grain == "quarter" else 1
        first = year * 12 + (calendar.fiscal_year_start_month - 1) + (quarter - 1) * 3
        return Period(grain, first, calendar)
    raise HTTPException(422, f"Not a period key: {key!r}; expected YYYY-MM, YYYY-Qn or YYYY")
