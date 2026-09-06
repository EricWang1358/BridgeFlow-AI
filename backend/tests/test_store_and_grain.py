"""Tests for where a result lives, and for putting four grains on one axis."""

from __future__ import annotations

import pandas as pd
import pytest
import yaml

from bridgeflow import grain, store
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import FieldDictionary
from bridgeflow.config import REPO_ROOT
from bridgeflow.schemas import MasterTable, PipelineResult, RiskReport

DICTIONARY = FieldDictionary(
    yaml.safe_load(
        (REPO_ROOT / "data" / "mappings" / "field-dictionary.example.yaml").read_text("utf-8")
    )
)


@pytest.fixture
def outputs(tmp_path, monkeypatch):
    monkeypatch.setattr("bridgeflow.config.settings.result_store_path", str(tmp_path))
    return tmp_path


def _result(period: str) -> PipelineResult:
    return PipelineResult(
        period=period,
        clean_tables=[],
        master_table=MasterTable(grain="month", periods=[period], rows=[]),
        risk_report=RiskReport(period=period, findings=[], tensions=[], cards=[]),
    )


def test_a_result_survives_the_process_that_made_it(outputs):
    store.save(_result("2025-11"))

    assert store.load("2025-11").period == "2025-11"


def test_an_unanalysed_period_is_absent_rather_than_an_error(outputs):
    assert store.load("2099-01") is None


def test_a_period_cannot_escape_the_store_directory(outputs):
    """The period arrives from a form field, so it is not trusted as a path."""
    store.save(_result("../../etc/passwd"))

    assert not (outputs.parent.parent / "etc").exists()
    assert list(outputs.glob("*.json"))


def test_the_previous_period_can_be_found(outputs):
    """Cross-month work starts here: no comparison and no change differ."""
    for period in ("2025-09", "2025-10", "2025-11"):
        store.save(_result(period))

    assert store.previous("2025-11").period == "2025-10"
    assert store.previous("2025-09") is None


async def _tables(period: str, departments=("production", "procurement", "finance")):
    agent = DataSanitizerAgent()
    samples = REPO_ROOT / "data" / "samples"
    return [
        await agent.run(SanitizerInput(d, period, pd.read_csv(samples / f"{d}_{period}.csv")))
        for d in departments
    ]


async def test_daily_and_weekly_rows_land_on_a_monthly_axis():
    values, unplaced = grain.to_monthly(await _tables("2025-11"), DICTIONARY)

    assert values
    assert not unplaced
    assert all(len(v.month) == 7 for v in values)


async def test_a_monthly_figure_can_be_opened_back_up():
    """An approver who cannot see the rows cannot check the total."""
    values, _ = grain.to_monthly(await _tables("2025-11"), DICTIONARY)
    # The ambiguous row is quarantined; only unambiguous dates reach aggregation.
    output = next(v for v in values if v.measure == "output_quantity" and v.month == "2025-11")

    assert output.source_count > 1
    assert output.sources


async def test_the_monthly_axis_excludes_undecided_dates():
    """An ambiguous date must not invent a March period in a November batch."""
    values, _ = grain.to_monthly(await _tables("2025-11"), DICTIONARY)

    months = {v.month for v in values}

    assert "2025-11" in months
    assert months == {"2025-11"}


async def test_how_a_measurement_rolls_up_is_declared_not_assumed():
    values, _ = grain.to_monthly(await _tables("2025-11"), DICTIONARY)
    by_measure = {v.measure: v.rollup for v in values}

    assert by_measure["output_quantity"] == "sum"
    assert by_measure["receivable_days"] == "average", "averaging days is not summing them"


def test_a_row_with_no_readable_date_is_reported_not_filed_under_this_month():
    """Unknown is not "this month". Filing it there is how a figure moves silently."""
    from bridgeflow.schemas import CleanTable, ColumnSpec

    table = CleanTable(
        department="production",
        period="2025-11",
        columns=[ColumnSpec(name="date", dtype="date"), ColumnSpec(name="output_qty", dtype="number")],
        rows=[{"date": "not a date", "output_qty": 100}],
    )

    values, unplaced = grain.to_monthly([table], DICTIONARY)

    assert not values
    assert unplaced and "row 0" in unplaced[0]


async def test_an_ambiguous_date_says_so_instead_of_choosing_quietly():
    """03/11/2025 is 3 November to a Singaporean SME and 11 March to pandas.

    Both parse, nothing errors, and the row lands in the wrong month until something
    aggregates and a March figure turns up in a November batch.
    """
    table = (await _tables("2025-11", ("production",)))[0]

    ambiguous = [c for c in table.corrections if c.rule == "date_parse_ambiguous"]

    assert ambiguous, "a coin toss was recorded as a confident fix"
    assert ambiguous[0].confidence <= 0.5
    assert "locale" in ambiguous[0].reason
    assert ambiguous[0].after is None
    assert any(row.get("date") == "03/11/2025" for row in table.quarantine)


def test_rerunning_a_month_does_not_make_the_earlier_figures_unfindable(outputs):
    """FR 11 forbids silently recomputing a published batch.

    Re-running a month is allowed. Making the figures somebody signed unfindable
    is not.
    """
    import time

    store.save(_result("2025-11"))
    time.sleep(1.1)  # the stamp has second resolution
    store.save(_result("2025-11"))

    stamps = store.versions("2025-11")

    assert len(stamps) == 2, "the earlier run was overwritten"
    assert store.load_version("2025-11", stamps[0]) is not None


def test_a_period_that_was_never_run_has_no_versions(outputs):
    assert store.versions("2099-01") == []


async def test_a_row_is_filed_by_its_own_date_not_the_batch_label():
    """A row dated 11 March inside a November upload belongs in March.

    Filing it under the batch label is how a misread date stays invisible.
    """
    from bridgeflow.agents import SOPFlowEngine, SOPInput
    from bridgeflow.schemas import EntityGraph

    tables = await _tables("2025-11", ("production",))
    # A declared ISO March date is different from an unresolved slash-date guess.
    tables[0].rows[0]["date"] = "2025-03-11"
    output = await SOPFlowEngine().run(
        SOPInput(
            period="2025-11", tables=tables, graph=EntityGraph(), findings=[], tensions=[]
        )
    )

    months = set(output.master_table.periods)

    assert "2025-11" in months
    assert any(row.get("period_from") for row in output.master_table.rows), (
        "a row filed somewhere other than its batch must say so"
    )
