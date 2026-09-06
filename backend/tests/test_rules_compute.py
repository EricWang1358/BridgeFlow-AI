"""Tests for "rules compute, the model explains".

The evaluator used to serialise every cleaned row into the prompt and let the model
work the figures out. That does not survive the batch size the PRD specifies, and a
figure the model arrived at by reading rows cannot be reproduced or signed off.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bridgeflow import metrics
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import FieldDictionary
from bridgeflow.config import REPO_ROOT

SAMPLES = REPO_ROOT / "data" / "samples"
DICTIONARY = FieldDictionary(
    {
        "columns": {"production": {"sku": "sku"}},
        "measures": {
            "production": {"output_qty": "output_quantity"},
            "finance": {"amount": "revenue_amount"},
        },
    }
)


async def _tables(*departments: str):
    agent = DataSanitizerAgent()
    return [
        await agent.run(
            SanitizerInput(d, "2025-11", pd.read_csv(SAMPLES / f"{d}_2025-11.csv"))
        )
        for d in departments
    ]


async def test_a_metric_is_computed_from_declared_columns():
    value = metrics.compute(
        "total_output", "2025-11", await _tables("production"), dictionary=DICTIONARY
    )

    assert value.value == 3050  # Clean subset; the 980-unit ambiguous date is quarantined.
    assert value.formula


async def test_the_sources_are_a_bounded_sample_with_a_true_count():
    value = metrics.compute(
        "total_output", "2025-11", await _tables("production"), dictionary=DICTIONARY
    )

    assert len(value.sources) <= metrics.EVIDENCE_SAMPLE
    assert value.source_count == 4
    assert value.truncated is False


async def test_an_undeclared_measure_is_refused_not_estimated():
    empty = FieldDictionary({"columns": {"production": {"sku": "sku"}}})

    with pytest.raises(metrics.MetricRefused, match="declares"):
        metrics.compute("total_output", "2025-11", await _tables("production"), dictionary=empty)


async def test_a_role_is_told_what_could_not_be_computed():
    """A role not told a metric is missing will reason as though it does not matter."""
    values, refusals = metrics.for_role(
        "production", "2025-11", await _tables("production"), DICTIONARY
    )

    assert [v.metric for v in values] == ["total_output"]
    assert refusals, "capacity_hours is undeclared here and the role must be told"
    assert any("capacity_hours" in r for r in refusals)


def test_the_catalogue_offers_only_what_the_dictionary_supports():
    assert metrics.available(FieldDictionary()) == []
    offered = {m.name for m in metrics.available(DICTIONARY)}
    # Only what this dictionary's measures support: output quantity and revenue
    # amount, which is enough for the sums and for the account-split metrics.
    assert "total_output" in offered
    assert "capacity_utilisation" not in offered, "capacity hours are undeclared here"


async def test_the_prompt_context_carries_metrics_and_not_rows():
    """The point of the whole change: 200,000 rows must never reach a context."""
    from bridgeflow.agents.evaluator import MultiRoleEvaluatorAgent
    from bridgeflow.schemas import EntityGraph

    tables = await _tables("production")
    captured: dict[str, str] = {}

    class _Recorder:
        name = "recorder"

        async def complete(self, *, system, messages, schema=None, session_id=None):
            captured["prompt"] = messages[0].content
            raise RuntimeError("stop here — the prompt is what is under test")

    agent = MultiRoleEvaluatorAgent(llm=_Recorder())
    payload = type(
        "P", (), {"period": "2025-11", "tables": tables, "graph": EntityGraph()}
    )()

    with pytest.raises(RuntimeError):
        await agent._evaluate_role("production", payload)

    prompt = captured["prompt"]
    assert "metrics" in prompt
    assert "total_output" in prompt
    # The raw row values must not be there. 180 is a capacity figure from row 0.
    assert '"rows"' not in prompt, "the cleaned rows are back in the prompt"
