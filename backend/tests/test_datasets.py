"""Tests that the three industry datasets actually exercise what they claim to.

A dataset that says it is a compatibility test and quietly resembles the one the
code was written against tests nothing. So the properties are asserted: different
column names, different languages, a working dictionary per industry, and metrics
that compute on all three without a line of industry-specific code.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest
import yaml

from bridgeflow import metrics
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import FieldDictionary
from bridgeflow.config import REPO_ROOT

DATA = REPO_ROOT / "data"
INDUSTRIES = ("manufacturing", "food", "electronics")
DEPARTMENTS = ("production", "procurement", "finance", "marketing")


def _dictionary(industry: str) -> FieldDictionary:
    if industry == "manufacturing":
        path = DATA / "mappings" / "field-dictionary.example.yaml"
    else:
        path = DATA / "mappings" / f"field-dictionary.{industry}.example.yaml"
    return FieldDictionary(yaml.safe_load(path.read_text(encoding="utf-8")))


def _sample_path(industry: str, department: str) -> Path:
    prefix = "" if industry == "manufacturing" else f"{industry}_"
    return DATA / "samples" / f"{prefix}{department}_2025-11.csv"


@pytest.mark.parametrize("industry", INDUSTRIES)
@pytest.mark.parametrize("department", DEPARTMENTS)
def test_every_industry_has_every_department(industry: str, department: str):
    assert _sample_path(industry, department).is_file()


@pytest.mark.parametrize("industry", INDUSTRIES)
def test_the_acceptance_set_is_a_different_month(industry: str):
    """Held out, and not merely a copy: a second month is what cross-month memory needs."""
    acceptance = DATA / "acceptance" / industry
    assert list(acceptance.glob("*_2025-12.csv"))
    assert not list(acceptance.glob("*_2025-11.csv")), "the acceptance set must not be the dev set"


@pytest.mark.parametrize("industry", INDUSTRIES)
def test_each_acceptance_set_ships_its_ground_truth(industry: str):
    expected = yaml.safe_load((DATA / "acceptance" / industry / "expected.yaml").read_text("utf-8"))

    assert expected["refusals"], "an acceptance set with no expected refusal proves nothing"
    assert expected["quality_defects"]


def test_the_industries_do_not_share_column_names():
    """The point of three datasets. If they overlapped, one dictionary would serve all
    three and nothing about field-independence would be under test."""
    headers = {}
    for industry in INDUSTRIES:
        with _sample_path(industry, "production").open(encoding="utf-8") as handle:
            headers[industry] = {c.strip().lower() for c in next(csv.reader(handle))}

    for a, b in (("manufacturing", "food"), ("manufacturing", "electronics"), ("food", "electronics")):
        assert not headers[a] & headers[b], f"{a} and {b} share column names"


def test_at_least_one_industry_has_non_english_headers():
    """The built-in English column hints must be visibly useless somewhere."""
    with _sample_path("food", "production").open(encoding="utf-8") as handle:
        header = next(csv.reader(handle))

    assert any(any("一" <= ch <= "鿿" for ch in name) for name in header)


@pytest.mark.parametrize("industry", INDUSTRIES)
async def test_a_metric_computes_on_every_industry_without_industry_specific_code(industry: str):
    agent = DataSanitizerAgent()
    tables = [
        await agent.run(
            SanitizerInput(d, "2025-11", pd.read_csv(_sample_path(industry, d)))
        )
        for d in DEPARTMENTS
    ]

    value = metrics.compute("total_output", "2025-11", tables, dictionary=_dictionary(industry))

    assert value.value > 0
    assert value.sources


@pytest.mark.parametrize("industry", INDUSTRIES)
def test_each_industry_has_a_poisoned_variant(industry: str):
    poisoned = list((DATA / "poisoned" / industry).glob("*.csv"))

    assert poisoned, "docs/12 promises a poisoned dataset per industry"
    text = poisoned[0].read_text(encoding="utf-8")
    assert "ignore" in text.lower() or "忽略" in text or "System:" in text
