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
from bridgeflow.schemas import CleanTable, ColumnSpec

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


# --- what a row is about, versus what it measures ----------------------------

def _finance(rows: list[dict]) -> CleanTable:
    """A finance table whose identity column is declared and whose amount is not."""
    return CleanTable(
        department="finance", period="2025-11", rows=rows,
        columns=[ColumnSpec(name=name, dtype="number" if name == "amount" else "string")
                 for name in rows[0]],
    )


ACCOUNTS = FieldDictionary({
    "columns": {"finance": {"gl_account": "gl_account"}},
    "measures": {"finance": {"amount": "revenue_amount"}},
    "account_classes": {"finance": {"sales": ["sales"], "cost_of_sales": ["cogs", "cost"]}},
})


async def test_a_customer_name_cannot_turn_a_sale_into_a_cost():
    """The marker used to be searched for anywhere in the row, so a buyer called
    "Cost Cutters Ltd" put its own revenue into cost of sales. Every column got a
    vote on what kind of line it was, including the ones that are not identity.

    Asserted on `cost_of_sales` rather than `sales`, because the sales line matches
    both markers under the old rule and only the wrong total gives the bug away.
    """
    tables = [_finance([
        {"gl_account": "4000-SALES", "customer": "Cost Cutters Ltd", "amount": 90000},
        {"gl_account": "5000-COGS", "customer": "Acme Pte Ltd", "amount": -70000},
    ])]

    cost = metrics.compute("cost_of_sales", "2025-11", tables, dictionary=ACCOUNTS)

    # Under the old whole-row search the sales line matched "cost" through the
    # customer name and this came back as 20,000.
    assert cost.value == -70000


async def test_an_entity_filter_reads_identity_not_the_rest_of_the_line():
    """Filtering by entity also matched the stringified row, so any column carrying
    the entity's text — a note, a description, a reference — pulled an unrelated
    line into the total."""
    tables = [_finance([
        {"gl_account": "4000-SALES", "customer": "A1 Trading", "note": "-", "amount": 100},
        {"gl_account": "4000-SALES", "customer": "Bayfront", "note": "replaces A1 order", "amount": 5000},
    ])]
    declared = FieldDictionary({
        "columns": {"finance": {"customer": "customer"}},
        "measures": {"finance": {"amount": "revenue_amount"}},
    })

    only_a1 = metrics.compute("revenue", "2025-11", tables, entity="A1", dictionary=declared)

    # `note` is not declared as identity, so it does not decide which rows are A1's.
    # Under the old rule this returned 5,100.
    assert only_a1.value == 100


async def test_undeclared_account_classes_refuse_sales_and_cost_instead_of_guessing():
    """#92: which codes are sales is the customer's chart of accounts, not a keyword list in code."""
    tables = await _tables("finance")
    unclassified = FieldDictionary({"columns": {"finance": {"gl_account": "gl_account"}},
                                    "measures": {"finance": {"amount": "revenue_amount"}}})
    for metric in ("sales", "cost_of_sales", "gross_margin"):
        with pytest.raises(metrics.MetricRefused, match="account_classes"):
            metrics.compute(metric, "2025-11", tables, dictionary=unclassified)


async def test_a_net_of_classified_lines_is_never_reported_as_revenue():
    tables = await _tables("finance")
    with pytest.raises(metrics.MetricRefused, match="net"):
        metrics.compute("revenue", "2025-11", tables, dictionary=ACCOUNTS)


def test_no_account_keyword_is_written_into_metrics_code():
    import ast
    from pathlib import Path
    tree = ast.parse(Path(metrics.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        holder = isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        if holder and ast.get_docstring(node) is not None:
            node.body = node.body[1:] or [ast.Pass()]
    code = ast.unparse(tree)
    for marker in ("cogs", "销售", "收入", "成本", "'rev'"):
        assert marker not in code
