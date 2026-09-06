"""The Master Table joins on what an entity *is*, and folds by declared policy.

Two defects this closes, both invisible in the output they produced:

* Rows were keyed on the **raw cell**, so `SKU-A1` and `sku-a1` — already merged into
  one entity by the resolver, aliases and all — arrived as two rows. The alignment was
  computed upstream and thrown away in the one step the demo shows.
* Several source rows reaching one cell **overwrote** each other, so a material bought
  on three POs appeared as the last one: 4 units, no price, and the rise inside the
  month gone from the table the rise was about.

What replaces an overwrite is declared per measurement, because summing a price and
averaging a quantity are both arithmetic and both wrong somewhere (`FR 09`).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest
import yaml

from bridgeflow import metrics
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput, SOPFlowEngine
from bridgeflow.agents.sop_flow import MissingRollup, SOPInput
from bridgeflow.config import REPO_ROOT
from bridgeflow.schemas import CleanTable, ColumnSpec, Entity, EntityGraph

SAMPLES = REPO_ROOT / "data" / "samples"
EXAMPLE_DICTIONARY = REPO_ROOT / "data" / "mappings" / "field-dictionary.example.yaml"

#: Both spellings of one SKU, produced on one line, two weeks apart.
ONE_SKU_TWICE = [
    {"sku": "SKU-A1", "output_qty": 1200, "capacity_hrs": 180, "date": "2025-11-03"},
    {"sku": "sku-a1", "output_qty": 1100, "capacity_hrs": 175, "date": "2025-11-08"},
]

GRAPH = EntityGraph(
    entities=[
        Entity(id="sku:sku-a1", kind="sku", label="SKU-A1", aliases=["SKU-A1", "sku-a1"])
    ]
)


def _dictionary(rollups: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "columns": {
            "production": {"sku": "sku"},
            "procurement": {"material": "raw_material"},
        },
        "measures": {
            "production": {
                "output_qty": "output_quantity",
                "capacity_hrs": "capacity_hours",
            },
            "procurement": {
                "unit_price": "unit_price",
                "qty": "purchase_quantity",
                "line_count": "line_count",
            },
        },
        "rollups": (
            {
                "output_quantity": "sum",
                "capacity_hours": "sum",
                "purchase_quantity": "sum",
                "unit_price": "average",
                "line_count": "sum",
            }
            if rollups is None
            else rollups
        ),
    }


def _production(rows: list[dict[str, Any]]) -> CleanTable:
    return CleanTable(
        department="production",
        period="2025-11",
        columns=[
            ColumnSpec(name="sku", dtype="string"),
            ColumnSpec(name="output_qty", dtype="number"),
            ColumnSpec(name="capacity_hrs", dtype="number"),
            ColumnSpec(name="date", dtype="date"),
        ],
        rows=rows,
    )


def _procurement(rows: list[dict[str, Any]]) -> CleanTable:
    return CleanTable(
        department="procurement",
        period="2025-11",
        columns=[
            ColumnSpec(name="material", dtype="string"),
            ColumnSpec(name="supplier", dtype="string"),
            ColumnSpec(name="unit_price", dtype="number"),
            ColumnSpec(name="qty", dtype="number"),
            ColumnSpec(name="line_count", dtype="number"),
        ],
        rows=rows,
    )


@pytest.fixture
def dictionary(tmp_path, monkeypatch):
    """Point the engine at a dictionary the test wrote, and give it back as a setter."""
    def _use(raw: dict[str, Any]) -> None:
        path = tmp_path / "field-dictionary.yaml"
        path.write_text(yaml.safe_dump(raw), encoding="utf-8")
        monkeypatch.setattr(
            "bridgeflow.config.settings.field_dictionary_path", str(path)
        )

    return _use


async def _master(tables: list[CleanTable], graph: EntityGraph | None = None):
    return await SOPFlowEngine().run(
        SOPInput(period="2025-11", tables=tables, graph=graph or GRAPH)
    )


async def test_two_spellings_of_one_sku_become_one_row(dictionary):
    """The resolver merged these two; the table has to use that and not the spelling."""
    dictionary(_dictionary())

    output = await _master([_production(ONE_SKU_TWICE)])
    rows = output.master_table.rows

    assert len(rows) == 1, rows
    assert rows[0]["entity_id"] == "sku:sku-a1"
    assert rows[0]["entity"] == "SKU-A1", "the canonical label, not whichever came first"
    assert rows[0]["production.output_qty"] == 2300
    assert rows[0]["production.capacity_hrs"] == 355
    assert rows[0]["source_rows"] == 2


async def test_several_purchase_lines_fold_instead_of_overwriting(dictionary):
    """Three POs for one material — and the month is not simply the last sheet row."""
    dictionary(_dictionary())
    material = _procurement(
        [
            {"material": "RM-Alu-6061", "supplier": "SG Metals", "unit_price": 4850, "qty": 12, "line_count": 1},
            {"material": "RM-Alu-6061", "supplier": "SG Metals", "unit_price": 5200, "qty": 8, "line_count": 1},
            {"material": "RM-Alu-6061", "supplier": "SG Metals", "qty": 4, "line_count": 1},
        ]
    )

    row = (await _master([material])).master_table.rows[0]

    assert row["procurement.qty"] == 24, "the overwrite used to leave 4"
    assert row["procurement.line_count"] == 3
    assert row["procurement.unit_price"] == 5025.0, "the two lines that state a price"
    assert row["rollups"]["procurement.unit_price"] == "average"
    assert row["source_rows"] == 3


async def test_an_attribute_that_disagrees_stays_visible(dictionary):
    """Two supplier names do not combine, so the disagreement is shown not settled."""
    dictionary(_dictionary())
    material = _procurement(
        [
            {"material": "RM-Alu-6061", "supplier": "SG Metals", "qty": 12},
            {"material": "RM-Alu-6061", "supplier": "Metal Importers", "qty": 8},
        ]
    )

    row = (await _master([material])).master_table.rows[0]

    assert set(row["procurement.supplier"]) == {"SG Metals", "Metal Importers"}
    assert row["rollups"]["procurement.supplier"] == "disagreed"


async def test_a_fold_with_no_stated_policy_refuses_the_table(dictionary):
    """Sum or average? The sheet cannot answer, so nobody gets a plausible number."""
    dictionary(_dictionary({"capacity_hours": "sum", "purchase_quantity": "sum"}))

    with pytest.raises(MissingRollup, match="output_quantity"):
        await _master([_production(ONE_SKU_TWICE)])


async def test_a_label_the_graph_never_saw_is_named_on_the_table(dictionary):
    """An unmerged label is a coverage gap in the dictionary, not a second entity."""
    dictionary(_dictionary())

    output = await _master(
        [
            _production(
                [
                    {"sku": "SKU-A1", "output_qty": 1200, "capacity_hrs": 180, "date": "2025-11-03"},
                    {"sku": "SKU-Z9", "output_qty": 50, "capacity_hrs": 5, "date": "2025-11-04"},
                ]
            )
        ]
    )

    assert len(output.master_table.rows) == 2
    assert output.master_table.unmatched_entities == ["production: SKU-Z9"]


async def test_the_same_string_for_two_kinds_is_not_merged(dictionary):
    """A customer and a SKU sharing a label is a coincidence, not an alias."""
    dictionary(_dictionary())
    graph = EntityGraph(
        entities=[
            Entity(id="sku:acme", kind="sku", label="Acme", aliases=["Acme"]),
            Entity(id="customer:acme", kind="customer", label="Acme", aliases=["Acme"]),
        ]
    )

    row = (
        await _master([_production([{"sku": "Acme", "output_qty": 10, "capacity_hrs": 1, "date": "2025-11-03"}])], graph)
    ).master_table.rows[0]

    assert row["entity_id"] == "sku:acme"


async def test_a_misfiled_date_is_still_announced(dictionary):
    """The #79 mark survives the rewrite: a row lands where its date says, and says so."""
    dictionary(_dictionary())

    output = await _master(
        [
            _production(
                [
                    {"sku": "SKU-A1", "output_qty": 1200, "capacity_hrs": 180, "date": "2025-11-03"},
                    {"sku": "SKU-A1", "output_qty": 980, "capacity_hrs": 150, "date": "2025-03-11"},
                ]
            )
        ]
    )
    march = [r for r in output.master_table.rows if r["period"] == "2025-03"]

    assert len(march) == 1
    assert "2025-11 batch" in march[0]["period_from"]


async def test_the_shipped_dictionary_reconciles_with_the_metric(dictionary):
    """The table and the metric must not disagree about the same month.

    They used to: the metric summed every production row to 4,030 while the table
    showed 1,100 for a SKU that produced 2,300, because one spelling overwrote the
    other. A wide table nobody can add up is not a deliverable.
    """
    dictionary(
        yaml.safe_load(EXAMPLE_DICTIONARY.read_text("utf-8"))
    )
    agent = DataSanitizerAgent()
    table = await agent.run(
        SanitizerInput("production", "2025-11", pd.read_csv(SAMPLES / "production_2025-11.csv"))
    )

    output = await _master([table], graph=EntityGraph())
    from_table = sum(
        row.get("production.output_qty") or 0 for row in output.master_table.rows
    )
    computed = metrics.compute("total_output", "2025-11", [table])

    # Only the unambiguous subset; the uploaded-batch API refuses a full total
    # until the quarantined 980-unit row has been resolved and reimported.
    assert from_table == computed.value == 3050
    assert len(table.quarantine) == 1
