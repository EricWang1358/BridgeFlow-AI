"""Tests for how the sanitizer decides a column's type.

Every test here exists because the previous tests asserted column NAMES and never
looked at the values, which let a whole column of quantities be silently replaced.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bridgeflow.agents import DataSanitizerAgent, SanitizerInput


async def _clean(frame: pd.DataFrame):
    return await DataSanitizerAgent().run(SanitizerInput("production", "2025-11", frame))


async def test_a_column_of_quantities_stays_quantities():
    """The defect: `pd.to_datetime` reads a bare integer as nanoseconds since the
    epoch, so 1200 / 980 / 450 all parsed as dates and became 1970-01-01."""
    table = await _clean(pd.DataFrame({"output_qty": [1200, 980, 450, 1100]}))

    values = [row["output_qty"] for row in table.rows]

    assert values == [1200, 980, 450, 1100]
    assert not any(str(v).startswith("1970") for v in values)


async def test_dates_are_still_normalised():
    table = await _clean(
        pd.DataFrame({"date": ["2025-11-03", "03/11/2025", "Nov 8 2025", "2025-11-12"]})
    )

    assert [row["date"] for row in table.rows] == [
        "2025-11-03",
        "2025-11-08",
        "2025-11-12",
    ]
    assert table.quarantine == [{"date": "03/11/2025"}]


async def test_currency_text_is_still_stripped_to_a_number():
    table = await _clean(pd.DataFrame({"unit_price": ["S$ 4,850", "S$ 3,200", "1,900", "540"]}))

    assert [row["unit_price"] for row in table.rows] == [4850.0, 3200.0, 1900.0, 540.0]


@pytest.mark.parametrize(
    ("column", "values"),
    [
        ("sku", ["SKU-A1", "SKU-B7", "sku-a1", "SKU-C3"]),
        ("line", ["Line 2", "Line 1", "Line 2", "Line 3"]),
    ],
)
async def test_labels_are_left_alone(column: str, values: list[str]):
    table = await _clean(pd.DataFrame({column: values}))

    assert [row[column] for row in table.rows] == values
