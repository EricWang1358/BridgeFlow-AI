"""Tests for the two changes that make the pipeline's cost and concurrency honest.

Both were invisible: adjudication looked like a loop over candidates because it was
one, and the evaluator looked concurrent because it called `asyncio.gather`.
"""

from __future__ import annotations

from bridgeflow.llm import get_provider
from bridgeflow.llm.base import Response


class _Counter:
    """A provider that records how it was called instead of calling anything."""

    name = "counter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def complete(self, *, system, messages, schema=None, session_id=None):
        self.calls.append(messages[0].content)
        payload = {"verdicts": []}
        if schema is not None:
            import json

            return Response(text=json.dumps(payload), parsed=schema.model_validate(payload))
        return Response(text="")


async def test_one_call_per_relation_type_not_one_per_candidate():
    """Six candidates across two relation types used to cost six calls."""
    import pandas as pd

    from bridgeflow.agents import DataSanitizerAgent, SanitizerInput, SemanticResolverAgent
    from bridgeflow.config import REPO_ROOT

    samples = REPO_ROOT / "data" / "samples"
    sanitizer = DataSanitizerAgent()
    tables = [
        await sanitizer.run(
            SanitizerInput(d, "2025-11", pd.read_csv(samples / f"{d}_2025-11.csv"))
        )
        for d in ("production", "procurement", "finance", "marketing")
    ]

    counter = _Counter()
    graph = await SemanticResolverAgent(llm=counter).run(tables)

    relations = {link.relation for link in graph.links + graph.unresolved}
    assert len(counter.calls) <= max(1, len(relations)), (
        f"{len(counter.calls)} calls for {len(relations)} relation type(s)"
    )


async def test_a_batch_prompt_carries_every_candidate_with_an_index():
    """Verdicts are matched back by index, so the index has to be in the prompt."""
    import json

    import pandas as pd

    from bridgeflow.agents import DataSanitizerAgent, SanitizerInput, SemanticResolverAgent
    from bridgeflow.config import REPO_ROOT

    samples = REPO_ROOT / "data" / "samples"
    sanitizer = DataSanitizerAgent()
    tables = [
        await sanitizer.run(
            SanitizerInput(d, "2025-11", pd.read_csv(samples / f"{d}_2025-11.csv"))
        )
        for d in ("marketing", "finance")
    ]

    counter = _Counter()
    await SemanticResolverAgent(llm=counter).run(tables)

    for call in counter.calls:
        payload = json.loads(call)
        assert payload["candidates"]
        assert [c["index"] for c in payload["candidates"]] == list(
            range(len(payload["candidates"]))
        )


async def test_an_unjudged_candidate_survives_as_unresolved():
    """A verdict that does not come back must not delete the candidate.

    An unjudged link belongs in the human queue, not the bin.
    """
    import pandas as pd

    from bridgeflow.agents import DataSanitizerAgent, SanitizerInput, SemanticResolverAgent
    from bridgeflow.config import REPO_ROOT

    samples = REPO_ROOT / "data" / "samples"
    sanitizer = DataSanitizerAgent()
    tables = [
        await sanitizer.run(
            SanitizerInput(d, "2025-11", pd.read_csv(samples / f"{d}_2025-11.csv"))
        )
        for d in ("marketing", "production")
    ]

    graph = await SemanticResolverAgent(llm=_Counter()).run(tables)

    assert graph.links or graph.unresolved, "candidates were dropped, not queued"


def test_separate_lanes_are_separate_providers(monkeypatch):
    """The fix for the fake concurrency: four roles must not share one runtime.

    A dsh provider serialises everything behind one lock, so four role agents on one
    provider ran strictly in turn however they were launched. Checked against the
    mock backend because what is under test is the registry, not a runtime.
    """
    monkeypatch.setattr("bridgeflow.config.settings.llm_provider", "mock")
    monkeypatch.setattr("bridgeflow.config.settings.llm_provider_evaluator", "")
    get_provider.cache_clear()

    assert get_provider("evaluator", lane="production") is not get_provider(
        "evaluator", lane="finance"
    )


def test_the_same_lane_is_reused(monkeypatch):
    """Lanes cost a subprocess each; asking twice must not start two."""
    monkeypatch.setattr("bridgeflow.config.settings.llm_provider", "mock")
    monkeypatch.setattr("bridgeflow.config.settings.llm_provider_evaluator", "")
    get_provider.cache_clear()

    assert get_provider("evaluator", lane="production") is get_provider(
        "evaluator", lane="production"
    )
