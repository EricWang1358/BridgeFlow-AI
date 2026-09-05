"""Tests for the two places that used to guess and then say nothing about it.

Both were silent: the pipeline produced an ordinary-looking result that was wrong
throughout, which is worse than a crash because nobody goes looking.
"""

from __future__ import annotations

import pytest

from bridgeflow.agents.semantic_resolver import FieldDictionary
from bridgeflow.agents.sop_flow import UnjoinableTables, _primary_key_column
from bridgeflow.schemas import CleanTable, ColumnSpec, KNOWN_ENTITY_KINDS


def _table(department: str, columns: list[str]) -> CleanTable:
    return CleanTable(
        department=department,
        period="2025-11",
        columns=[ColumnSpec(name=c, dtype="string") for c in columns],
        rows=[{c: "x" for c in columns}],
    )


def test_a_declared_column_becomes_the_join_key():
    dictionary = FieldDictionary({"columns": {"production": {"物料编码": "sku"}}})

    assert _primary_key_column(_table("production", ["日期", "物料编码"]), dictionary) == "物料编码"


def test_an_undeclared_table_has_no_join_key():
    """The defect: this used to return the first column and join on it silently."""
    dictionary = FieldDictionary({"columns": {"production": {"sku": "sku"}}})

    table = _table("production", ["日期", "数量", "产线"])

    assert _primary_key_column(table, dictionary) is None


def test_the_first_column_is_never_a_fallback():
    dictionary = FieldDictionary({"columns": {"finance": {"gl_account": "gl_account"}}})

    assert _primary_key_column(_table("production", ["anything", "at", "all"]), dictionary) is None


def test_refusing_names_the_departments_that_cannot_be_joined():
    error = UnjoinableTables(["production", "marketing"])

    assert "production" in str(error)
    assert "marketing" in str(error)
    assert "field dictionary" in str(error)


@pytest.mark.parametrize("kind", ["work_order", "batch", "project", "工单"])
def test_an_entity_kind_the_dictionary_invents_is_accepted(kind: str):
    """A sixth entity kind must cost a YAML edit, not a schema edit.

    The customer's schema is still being negotiated, so the set cannot be closed.
    """
    dictionary = FieldDictionary({"columns": {"production": {"col": kind}}})

    assert dictionary.kind_for("production", "col") == kind


@pytest.mark.parametrize("relation", ["supersedes", "returned_from", "退货冲销"])
def test_a_relation_the_dictionary_invents_is_accepted(relation: str):
    dictionary = FieldDictionary(
        {"relations": [{"source": "a:1", "target": "b:2", "relation": relation}]}
    )

    assert [r[2] for r in dictionary.relations] == [relation]


def test_the_known_names_are_documentation_not_a_permitted_set():
    """They exist so a reader knows the common case, not to constrain the dictionary."""
    assert "sku" in KNOWN_ENTITY_KINDS
    assert FieldDictionary({"columns": {"x": {"c": "not_in_that_tuple"}}}).kind_for("x", "c")


def test_an_undeclared_column_is_still_rejected_once_a_dictionary_exists():
    """Open does not mean unchecked — the validation moved, it did not disappear."""
    dictionary = FieldDictionary({"columns": {"production": {"sku": "sku"}}})

    assert dictionary.kind_for("production", "customer") is None
