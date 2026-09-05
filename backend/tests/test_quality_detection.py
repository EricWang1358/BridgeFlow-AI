"""Tests for the three defects FR 02 names and nothing detected.

Each of them looks like a business result rather than a data fault, which is why
they matter: a doubled total reads as a good month.
"""

from __future__ import annotations

import pandas as pd

from bridgeflow.agents import DataSanitizerAgent, SanitizerInput


async def _clean(frame: pd.DataFrame, department: str = "production"):
    return await DataSanitizerAgent().run(SanitizerInput(department, "2025-11", frame))


async def test_an_exact_repeat_is_removed_and_logged():
    frame = pd.DataFrame(
        {"sku": ["A1", "B7", "A1"], "qty": [100, 50, 100], "date": ["2025-11-01"] * 3}
    )

    table = await _clean(frame)

    assert len(table.rows) == 2, "a pasted-twice block doubles every total over it"
    assert any(c.rule == "duplicate_row" for c in table.corrections)


async def test_a_repeated_value_in_a_single_column_is_not_a_duplicate_row():
    """One column cannot tell a repeated record from a repeated value.

    A sheet listing line names would otherwise lose every line appearing twice.
    """
    table = await _clean(pd.DataFrame({"line": ["Line 2", "Line 1", "Line 2", "Line 3"]}))

    assert [r["line"] for r in table.rows] == ["Line 2", "Line 1", "Line 2", "Line 3"]


async def test_a_shifted_row_is_detected_and_quarantined():
    """It cannot be repaired — we do not know which way it slid — but it must not
    reach the Master Table pretending to be sound."""
    frame = pd.DataFrame(
        {
            "sku": ["A1", "", "B7", "C3"],
            "line": ["Line 2", "A1", "Line 1", "Line 3"],
            "qty": [100, "Line 2", 50, 75],
        }
    )

    table = await _clean(frame)

    assert any(c.rule == "column_shift" for c in table.corrections)
    assert table.quarantine, "a shifted row belongs in quarantine, not the Master Table"
    assert all(r.get("qty") != "Line 2" for r in table.rows)


async def test_a_shifted_row_does_not_decide_what_its_columns_hold():
    """One shifted row put a number in a date column, dragged the parse rate to the
    threshold, and the whole column stayed text — so the mixed date formats
    elsewhere in it went unreported."""
    frame = pd.DataFrame(
        {
            "sku": ["A1", "", "B7", "C3", "D4"],
            "qty": [100, "A1", 50, 75, 90],
            "date": ["2025-11-01", 70, "13/11/2025", "2025-11-20", "2025-11-27"],
        }
    )

    table = await _clean(frame)

    assert any(c.rule == "date_parse" for c in table.corrections), (
        "the broken row voted on the column type and hid a real correction"
    )


async def test_a_sound_sheet_produces_no_false_positives():
    frame = pd.DataFrame(
        {
            "sku": ["A1", "B7", "C3"],
            "line": ["Line 2", "Line 1", "Line 3"],
            "qty": [100, 50, 75],
        }
    )

    table = await _clean(frame)

    assert len(table.rows) == 3
    assert not table.quarantine
    assert not any(c.rule in {"duplicate_row", "column_shift"} for c in table.corrections)
