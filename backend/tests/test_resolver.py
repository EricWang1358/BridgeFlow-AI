"""Tests for how the resolver decides two identifiers are related.

The rule under test throughout: relationships come from declarations and from
what the rows put together, never from how identifiers are spelled.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from bridgeflow.agents import DataSanitizerAgent, SanitizerInput, SemanticResolverAgent
from bridgeflow.agents.semantic_resolver import FieldDictionary, load_field_dictionary
from bridgeflow.schemas import Department

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"
MAPPINGS = Path(__file__).resolve().parents[2] / "data" / "mappings"
PERIOD = "2025-11"


async def _clean_tables() -> list:
    agent = DataSanitizerAgent()
    departments: list[Department] = ["production", "procurement", "finance", "marketing"]
    return [
        await agent.run(
            SanitizerInput(d, PERIOD, pd.read_csv(SAMPLES / f"{d}_{PERIOD}.csv"))
        )
        for d in departments
    ]


async def test_co_occurrence_finds_links_string_matching_never_could():
    """Acme ordered SKU-A1. The labels share nothing; the marketing row says so."""
    graph = await SemanticResolverAgent().run(await _clean_tables())

    assert graph.entities, "no entities extracted"
    found = graph.links + graph.unresolved
    assert found, "resolver produced no links at all — the defect in #24"

    ordered_by = {
        (link.source, link.target) for link in found if link.relation == "ordered_by"
    }
    assert ("sku:sku-a1", "customer:acme-pte-ltd") in ordered_by, (
        f"the marketing sheet names both in one row; got {sorted(ordered_by)}"
    )


async def test_every_link_cites_its_support():
    graph = await SemanticResolverAgent().run(await _clean_tables())
    for link in graph.links + graph.unresolved:
        assert link.justification, f"{link.source}->{link.target} has no justification"


def test_declared_columns_suppress_hint_guessing():
    """Once OA declares the columns, an undeclared column is ignored, not guessed."""
    dictionary = FieldDictionary({"columns": {"production": {"sku": "sku"}}})

    assert dictionary.kind_for("production", "sku") == "sku"
    # 'customer' would match a hint, but this dictionary does not claim it.
    assert dictionary.kind_for("marketing", "customer") is None


def test_empty_dictionary_falls_back_to_hints():
    """Sample data must still run before the OA export exists."""
    dictionary = FieldDictionary()

    assert dictionary.is_empty
    assert dictionary.kind_for("marketing", "customer") == "customer"
    assert dictionary.kind_for("procurement", "material") == "raw_material"
    assert dictionary.kind_for("production", "output_qty") is None


def test_example_dictionary_parses_and_declares_the_bom_relation():
    """The BOM link is the one co-occurrence cannot find — no sheet holds both."""
    dictionary = load_field_dictionary(MAPPINGS / "field-dictionary.example.yaml")

    assert not dictionary.is_empty
    assert dictionary.kind_for("marketing", "product") == "sku"
    declared = {(s, t, r) for s, t, r, _ in dictionary.relations}
    assert ("sku:sku-a1", "raw_material:rm-alu-6061", "consumes") in declared


def test_missing_dictionary_file_is_not_an_error():
    assert load_field_dictionary(Path("does/not/exist.yaml")).is_empty


@pytest.mark.parametrize(
    ("a", "b"),
    [("SKU-A1", "RM-Alu-6061"), ("SKU-A1", "4000-Sales/A1"), ("SKU-A1", "Line 2")],
)
def test_cross_department_identifiers_do_not_resemble_each_other(a: str, b: str):
    """Documents why string similarity is not used for link discovery.

    If this ever starts failing, it means the identifiers happen to look alike —
    which still would not make them related.
    """
    from rapidfuzz import fuzz

    assert fuzz.token_set_ratio(a, b) < 55


def test_codes_that_differ_in_a_digit_are_different_entities():
    """PRJ2024011 and PRJ2024017 score 89 on token similarity; merging them mixed two projects."""
    from bridgeflow.schemas import Entity
    agent = SemanticResolverAgent()
    entities = {f"project:{c}": Entity(id=f"project:{c}", kind="project", label=c, aliases=[c])
                for c in ("PRJ2024011", "PRJ2024017", "PRJ2024011A")}
    agent._merge_aliases(entities)
    assert sorted(entities) == ["project:PRJ2024011", "project:PRJ2024017"]
    assert entities["project:PRJ2024011"].aliases == ["PRJ2024011", "PRJ2024011A"]  # same digits still fold
