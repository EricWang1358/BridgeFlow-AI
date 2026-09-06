"""Tests for the diagnosis a blocked batch gets instead of a dead end.

A batch with no declared joinable column is refused, correctly. What follows decides
whether this product is worth having: the operator is holding four departments'
spreadsheets and the same question the machine could not answer, and either the
agent helps or the refusal was a more articulate way of giving up.

Two constraints meet in this module, and these tests exist to keep them met:
nothing it returns is a cell (`CLAUDE.md`, seventh hard constraint), and nothing it
knows is a field name (eighth).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from bridgeflow import profiling
from bridgeflow.schemas import CleanTable, ColumnSpec


def table(department: str, rows: list[dict], dtypes: dict | None = None) -> CleanTable:
    dtypes = dtypes or {}
    columns = [ColumnSpec(name=name, dtype=dtypes.get(name, "string")) for name in (rows[0] if rows else {})]
    return CleanTable(department=department, period="2025-11", rows=rows, columns=columns)


def test_the_profile_never_carries_a_cell():
    """The scenario is 200,000 rows. A diagnosis that shows the model the data is the
    same defect as a tool return value that does."""
    secret = "ACME-CONFIDENTIAL-9931"
    result = profiling.profile("b", "2025-11", [
        table("finance", [{"project": secret, "amount": 5}, {"project": "SKU-B7", "amount": 7}]),
        table("production", [{"sku": secret}, {"sku": "SKU-B7"}]),
    ])

    payload = json.dumps(result.model_dump())

    assert secret not in payload
    assert "SKU-B7" not in payload
    # The overlap is still found — that is the point of hashing rather than omitting.
    assert any(o.left_coverage == 1.0 and o.right_coverage == 1.0 for o in result.overlaps)


def test_the_same_entity_written_three_ways_still_overlaps():
    """`SKU-A1`, `sku a1` and `SKU_A1` are one product typed by three departments."""
    result = profiling.profile("b", "2025-11", [
        table("finance", [{"project": "SKU-A1"}, {"project": "SKU-B7"}]),
        table("marketing", [{"product": "sku a1"}, {"product": "SKU_b7"}]),
    ])

    match = next(o for o in result.overlaps)

    assert match.shared == 2
    assert match.left_coverage == 1.0


def test_a_department_is_blocked_when_its_own_sheet_has_no_declared_column():
    """The default dictionary names `gl_account` for finance; the demo sheet carries
    `project`. Asking only whether the dictionary mentions the department reports
    finance as covered while the batch is unjoinable — the exact case that sent a
    real run into a dead end."""
    tables = [table("finance", [{"project": "SKU-A1"}]), table("production", [{"sku": "SKU-A1"}])]

    result = profiling.profile("b", "2025-11", tables,
                               declared={"finance": ["gl_account", "customer"], "production": ["sku"]})

    assert result.undeclared == ["finance"]


def test_numbers_are_labelled_so_a_coincidence_can_be_discounted():
    """Two numeric columns matching is arithmetic, not evidence of a shared entity.
    The profile does not decide that; it reports the types so the model can."""
    result = profiling.profile("b", "2025-11", [
        table("finance", [{"ar_days": 60}, {"ar_days": 90}], {"ar_days": "number"}),
        table("marketing", [{"terms": 60}, {"terms": 90}], {"terms": "number"}),
    ])

    match = next(o for o in result.overlaps)

    assert match.left_dtype == "number"
    assert match.right_dtype == "number"


def test_the_profile_does_not_grow_with_the_rows():
    """One column of five thousand rows profiles to the same handful of numbers as
    one column of five."""
    small = profiling.profile("b", "2025-11", [table("finance", [{"project": f"P{i}"} for i in range(5)])])
    large = profiling.profile("b", "2025-11", [table("finance", [{"project": f"P{i}"} for i in range(5000)])])

    assert len(small.columns) == len(large.columns) == 1
    assert len(json.dumps(large.model_dump())) < 2 * len(json.dumps(small.model_dump()))


def test_a_wide_sheet_is_capped_and_says_so():
    """A prompt that grows with the width of somebody's spreadsheet is unbounded by
    another name."""
    wide = [{f"c{i}": f"v{i}" for i in range(profiling.MAX_COLUMNS + 10)}]

    result = profiling.profile("b", "2025-11", [table("finance", wide)])

    assert len(result.columns) == profiling.MAX_COLUMNS
    assert result.truncated is True


def test_weak_overlap_is_not_reported_as_evidence():
    """Below the threshold an overlap is coincidence, and offering it as a candidate
    trains the reviewer to approve noise."""
    result = profiling.profile("b", "2025-11", [
        table("finance", [{"project": f"F{i}"} for i in range(10)]),
        table("marketing", [{"product": "F0"}, *[{"product": f"M{i}"} for i in range(9)]]),
    ])

    assert all(max(o.left_coverage, o.right_coverage) >= profiling.MIN_OVERLAP for o in result.overlaps)


def test_no_field_name_is_written_into_the_module():
    """Every signal is structural. The moment this file knows what a `sku` is, the
    customer's schema is hard-coded and the eighth constraint is gone."""
    tree = ast.parse(Path(profiling.__file__).read_text(encoding="utf-8"))
    # Docstrings explain the signals with examples and are allowed to name a column;
    # executable code is not. Stripping them by AST rather than by string surgery is
    # the difference between testing the rule and testing a guess about the layout.
    for node in ast.walk(tree):
        holder = isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        if holder and ast.get_docstring(node) is not None:
            node.body = node.body[1:] or [ast.Pass()]
    code = ast.unparse(tree).lower()

    for name in ("sku", "gl_account", "customer", "material", "project"):
        assert name not in code, f"{name} must not appear in the code"
