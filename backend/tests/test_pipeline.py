from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.pipeline import Orchestrator
from bridgeflow.schemas import Department

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"
PERIOD = "2025-11"


def _frames() -> dict[Department, pd.DataFrame]:
    return {
        dept: pd.read_csv(SAMPLES / f"{dept}_{PERIOD}.csv")
        for dept in ("production", "procurement", "finance", "marketing")
    }


async def test_sanitizer_normalises_headers_and_logs_every_change():
    frame = pd.read_csv(SAMPLES / f"production_{PERIOD}.csv")
    table = await DataSanitizerAgent().run(SanitizerInput("production", PERIOD, frame))

    assert "output_qty" in [c.name for c in table.columns], "headers should be snake_cased"
    assert table.corrections, "a messy sheet must produce a non-empty correction log"
    assert all(0.0 <= c.confidence <= 1.0 for c in table.corrections)


async def test_sanitizer_quarantines_rather_than_drops():
    frame = pd.read_csv(SAMPLES / f"production_{PERIOD}.csv")
    table = await DataSanitizerAgent().run(SanitizerInput("production", PERIOD, frame))

    # The mostly-empty SKU-B7 row must survive somewhere — never silently dropped.
    total = len(table.rows) + len(table.quarantine)
    assert total == len(frame.dropna(how="all"))


@pytest.mark.parametrize("period", [PERIOD])
async def test_full_pipeline_runs_on_mock_provider(period: str):
    result = await Orchestrator().run(period, _frames())

    assert result.period == period
    assert len(result.clean_tables) == 4
    assert result.master_table.rows, "master table should not be empty"
    assert result.risk_report is not None
    # Master table rows carry columns from more than one department — the whole point.
    prefixes = {k.split(".")[0] for row in result.master_table.rows for k in row if "." in k}
    assert len(prefixes) > 1, f"expected multiple departments merged, got {prefixes}"
