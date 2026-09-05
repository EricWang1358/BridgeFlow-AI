"""Tests for the metrics the demo actually says out loud.

`docs/04` beat 5 is four sentences — margin turned negative, aluminium is up,
line 2 is at 94%, Acme is tier C. Sums could not express any of them, so the beat
was marked ❌ while "rules compute" was nominally done.
"""

from __future__ import annotations

import pandas as pd
import pytest
import yaml

from bridgeflow import metrics
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import FieldDictionary
from bridgeflow.config import REPO_ROOT

SAMPLES = REPO_ROOT / "data" / "samples"
DEPARTMENTS = ("production", "procurement", "finance", "marketing")
DICTIONARY = FieldDictionary(
    yaml.safe_load((REPO_ROOT / "data" / "mappings" / "field-dictionary.example.yaml").read_text("utf-8"))
)


async def _tables(period: str):
    agent = DataSanitizerAgent()
    return [
        await agent.run(SanitizerInput(d, period, pd.read_csv(SAMPLES / f"{d}_{period}.csv")))
        for d in DEPARTMENTS
    ]


async def test_sales_and_cost_are_told_apart_by_account_code():
    """They live in one column. Summing them together is how revenue came out as
    11,700 in a month with 134,400 of sales — arithmetically right, semantically wrong."""
    tables = await _tables("2025-11")

    sales = metrics.compute("sales", "2025-11", tables, dictionary=DICTIONARY)
    cost = metrics.compute("cost_of_sales", "2025-11", tables, dictionary=DICTIONARY)

    assert sales.value > 0
    assert cost.value < 0
    assert sales.value != abs(cost.value)


async def test_gross_margin_is_a_ratio_of_the_two():
    tables = await _tables("2025-11")

    margin = metrics.compute("gross_margin", "2025-11", tables, dictionary=DICTIONARY)

    assert 0 < margin.value < 1
    assert margin.sources, "the demo's headline number must cite cells"


async def test_a_month_on_month_change_needs_the_previous_month():
    """"No comparison" and "no change" are different answers.

    A warning saying prices are flat when nobody looked is worse than one saying it
    cannot tell.
    """
    tables = await _tables("2025-11")

    with pytest.raises(metrics.MetricRefused, match="previous period"):
        metrics.compute("material_price_change", "2025-11", tables, dictionary=DICTIONARY)


async def test_a_price_rise_is_visible_against_the_prior_month():
    change = metrics.compute(
        "material_price_change",
        "2025-11",
        await _tables("2025-11"),
        dictionary=DICTIONARY,
        prior=await _tables("2025-10"),
    )

    assert change.value > 0, "October was authored cheaper so a rise is real, not asserted"


async def test_a_ratio_refuses_a_zero_denominator():
    """Zero capacity means the figure has no meaning, not that utilisation is zero."""
    from bridgeflow.schemas import CleanTable, ColumnSpec

    empty = CleanTable(
        department="production",
        period="2025-11",
        columns=[ColumnSpec(name="output_qty", dtype="number"), ColumnSpec(name="capacity_hrs", dtype="number")],
        rows=[{"output_qty": 100, "capacity_hrs": 0}],
    )

    with pytest.raises(metrics.MetricRefused, match="no meaning"):
        metrics.compute("capacity_utilisation", "2025-11", [empty], dictionary=DICTIONARY)


async def test_a_blank_cell_does_not_turn_a_numeric_column_into_text():
    """One deliberately empty cell in four dropped the parse rate below the
    threshold, left the whole column as text, and made every figure over it refuse."""
    tables = await _tables("2025-11")
    procurement = next(t for t in tables if t.department == "procurement")

    values = [r["unit_price"] for r in procurement.rows if r["unit_price"] not in (None, "")]

    assert values and all(isinstance(v, (int, float)) for v in values)
