"""Tests for whether a result can be traced back to a cell.

`docs/07` requires it, `docs/04`'s demo rules say a judge will ask, and
`docs/08` called it the foundation several other requirements sit on. Before this,
a Correction carried a row index and a column name — which cannot say which of the
four files that arrive every month it belongs to.
"""

from __future__ import annotations

import pandas as pd

from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.schemas import Evidence, SourceRef


async def test_every_correction_says_which_file_it_belongs_to():
    frame = pd.DataFrame({"Output Qty": [1200, 980], "Date": ["2025-11-03", "03/11/2025"]})

    table = await DataSanitizerAgent().run(SanitizerInput("production", "2025-11", frame))

    assert table.corrections
    for correction in table.corrections:
        assert correction.source is not None, "a correction with no source cannot be audited"
        assert correction.source.department == "production"
        assert correction.source.period == "2025-11"


async def test_a_citation_reads_as_something_a_person_can_act_on():
    frame = pd.DataFrame({"Output Qty": [1200, 980]})

    table = await DataSanitizerAgent().run(SanitizerInput("production", "2025-11", frame))
    citation = table.corrections[0].source.cite()

    assert "production" in citation
    assert "column" in citation


def test_a_citation_prefers_the_filename_the_user_recognises():
    ref = SourceRef(
        department="finance",
        period="2025-11",
        filename="Nov finance export.xlsx",
        sheet="Sheet2",
        row=7,
        column="amount",
    )

    assert ref.cite() == "Nov finance export.xlsx [Sheet2] row 7 column amount"


def test_evidence_carries_its_sources_and_a_true_count():
    """The count is separate from the list because the list is a bounded sample."""
    evidence = Evidence(
        period="2025-11",
        entity_id="sku:sku-a1",
        metric="total_output",
        value=4030,
        sources=[SourceRef(department="production", period="2025-11", row=0, column="output_qty")],
        source_count=200_000,
    )

    assert len(evidence.sources) == 1
    assert evidence.source_count == 200_000


def test_a_warning_can_state_its_baseline_threshold_and_impact():
    """PRD chapter 16 lists all three as required parts of a warning.

    They are optional in the schema so that older logs load, but the fields exist —
    before this there was nowhere to put them at all.
    """
    evidence = Evidence(
        period="2025-11",
        entity_id="sku:sku-a1",
        metric="material_price",
        value=4850,
        baseline="2025-10 average 4,110",
        threshold="+10% month on month",
        impact="unit cost +18%, margin turns negative above 92-day terms",
    )

    assert evidence.baseline and evidence.threshold and evidence.impact


def test_missing_parts_are_absent_rather_than_invented():
    evidence = Evidence(period="2025-11", entity_id="x", metric="m", value=1.0)

    assert evidence.baseline is None
    assert evidence.sources == []
    assert evidence.source_count == 0
