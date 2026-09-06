"""A spend is not a column of prices.

`material_spend` used to add up a price column and call it money spent, because the
field dictionary declared the sheet's unit price as an amount. It reported 13,540 for
a month whose three priced lines total 117,250 — and every cell it cited was genuine,
which is what let it survive review. Evidence proves a number came from a sheet; it
proves nothing about whether the formula means anything.

These tests hold all three routes open: a stated line amount, a derived one, and the
refusal when a line carries a quantity and no price.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bridgeflow import metrics
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import FieldDictionary, load_field_dictionary
from bridgeflow.config import REPO_ROOT
from bridgeflow.metrics import SPEND
from bridgeflow.schemas import ColumnSpec

SAMPLES = REPO_ROOT / "data" / "samples"

#: 4,850 × 12 + 5,200 × 8 + 3,490 × 5 — the three PO lines that carry a price.
PRICED_TOTAL = 4850 * 12 + 5200 * 8 + 3490 * 5

#: A sheet stating a price and a quantity, but no line amount.
DERIVED = FieldDictionary(
    {
        "measures": {
            "procurement": {"unit_price": "unit_price", "qty": "purchase_quantity"}
        },
        "derived": {
            "purchase_amount": {"product": ["unit_price", "purchase_quantity"]}
        },
    }
)

#: A sheet that states its own line amounts. Nothing here is recomputed.
STATED = FieldDictionary(
    {
        "measures": {
            "procurement": {"po_value": "purchase_amount", "qty": "purchase_quantity"}
        }
    }
)


async def _procurement():
    agent = DataSanitizerAgent()
    return await agent.run(
        SanitizerInput("procurement", "2025-11", pd.read_csv(SAMPLES / "procurement_2025-11.csv"))
    )


def _with_column(table, name: str, values: list[dict]):
    """The same table plus one computed column, as a sheet that states amounts."""
    return table.model_copy(
        update={
            "columns": [*table.columns, ColumnSpec(name=name, dtype="number")],
            "rows": values,
        }
    )


def test_a_derived_only_measure_still_offers_its_metric():
    """Filtering the catalogue on declared columns alone would hide what we can do.

    A metric that is never offered is worse than one that is refused: the model has
    no way to learn the figure exists, so it either reasons without it or asks for
    something the catalogue never contained.
    """
    offered = {spec.name for spec in metrics.available(DERIVED)}

    assert "material_spend" in offered
    assert "material_price_change" in offered
    assert metrics.available(FieldDictionary()) == []


async def test_a_spend_is_derived_from_price_times_quantity():
    table = await _procurement()
    priced = table.model_copy(
        update={"rows": [r for r in table.rows if r.get("unit_price") not in (None, "")]}
    )

    value = metrics.compute("material_spend", "2025-11", [priced], dictionary=DERIVED)

    assert value.value == PRICED_TOTAL
    assert value.value != 4850 + 5200 + 3490, "a column of prices summed as an amount"
    assert "×" in value.formula, "which route produced the figure must be visible in it"


async def test_a_line_without_a_price_refuses_the_spend_rather_than_shrinking_it():
    """One PO line buys 4 units at a price nobody filled in.

    Summing only the priced lines would report 117,250 for a month that spent at
    least that much and possibly more. An unknown is not a zero: this is the same
    rule that makes `compute` refuse to total the rows that happened to parse, and
    it is the case a real partially-filled sheet actually hits.
    """
    table = await _procurement()

    with pytest.raises(metrics.MetricRefused, match="row 3"):
        metrics.compute("material_spend", "2025-11", [table], dictionary=DERIVED)


async def test_a_stated_line_amount_is_summed_as_stated():
    table = await _procurement()
    priced = [r for r in table.rows if r.get("unit_price") not in (None, "")]
    stated = _with_column(
        table, "po_value", [{**r, "po_value": r["unit_price"] * r["qty"]} for r in priced]
    )

    value = metrics.compute("material_spend", "2025-11", [stated], dictionary=STATED)

    assert value.value == PRICED_TOTAL
    assert "states" in value.formula


async def test_the_stated_amount_wins_when_both_routes_are_available():
    """Where the customer wrote a figure down, that is the number an auditor signs."""
    table = await _procurement()
    priced = [r for r in table.rows if r.get("unit_price") not in (None, "")]
    stated = _with_column(
        table, "po_value", [{**r, "po_value": r["unit_price"] * r["qty"]} for r in priced]
    )
    both = FieldDictionary(
        {
            "measures": {
                "procurement": {
                    "po_value": "purchase_amount",
                    "unit_price": "unit_price",
                    "qty": "purchase_quantity",
                }
            },
            "derived": {
                "purchase_amount": {"product": ["unit_price", "purchase_quantity"]}
            },
        }
    )

    value = metrics.compute("material_spend", "2025-11", [stated], dictionary=both)

    assert "states" in value.formula, "a derived figure overrode the sheet's own numbers"


async def test_an_amount_without_any_quantity_column_is_still_a_spend():
    """A finance-style ledger states what each line cost and not how many units.

    Requiring a quantity column everywhere would refuse that sheet, which is a
    capability regression wearing the costume of caution: units are what a *price*
    needs, not what a *sum* needs.
    """
    table = await _procurement()
    priced = [r for r in table.rows if r.get("unit_price") not in (None, "")]
    amounts_only = table.model_copy(
        update={
            "columns": [*table.columns, ColumnSpec(name="po_value", dtype="number")],
            "rows": [{**r, "po_value": r["unit_price"] * r["qty"]} for r in priced],
        }
    )
    no_units = FieldDictionary(
        {"measures": {"procurement": {"po_value": "purchase_amount"}}}
    )

    spend = metrics.compute("material_spend", "2025-11", [amounts_only], dictionary=no_units)

    assert spend.value == PRICED_TOTAL

    # With no units anywhere, a price has nothing to divide by — supplied prior or not.
    with pytest.raises(metrics.MetricRefused, match="no meaning"):
        metrics.compute(
            "material_price_change",
            "2025-11",
            [amounts_only],
            dictionary=no_units,
            prior=[amounts_only],
        )


async def test_two_columns_for_one_factor_are_refused_not_settled_by_order():
    """Which of two price columns prices the line is a question for the dictionary.

    Taking the first match would produce one more plausible figure with nothing
    behind it — the exact failure this file is about.
    """
    table = await _procurement()
    priced = [r for r in table.rows if r.get("unit_price") not in (None, "")]
    twiced = _with_column(
        table, "list_price", [{**r, "list_price": r["unit_price"]} for r in priced]
    )
    ambiguous = FieldDictionary(
        {
            "measures": {
                "procurement": {
                    "unit_price": "unit_price",
                    "list_price": "unit_price",
                    "qty": "purchase_quantity",
                }
            },
            "derived": {
                "purchase_amount": {"product": ["unit_price", "purchase_quantity"]}
            },
        }
    )

    with pytest.raises(metrics.MetricRefused, match="matches 2 columns"):
        metrics.compute("material_spend", "2025-11", [twiced], dictionary=ambiguous)


def test_the_shipped_template_does_not_declare_a_price_as_an_amount():
    """The root cause was a declaration, so one test reads the shipped file.

    Name-based on purpose: it asserts on a data file, not on production logic, where
    naming a column in code is what `CLAUDE.md` forbids.
    """
    dictionary = load_field_dictionary(
        REPO_ROOT / "data" / "mappings" / "field-dictionary.example.yaml"
    )

    amounts = [column for (_dept, column), m in dictionary.measures.items() if m == SPEND]

    assert not [c for c in amounts if "price" in c], f"prices declared as amounts: {amounts}"
