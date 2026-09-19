"""Tests for the acceptance runner itself.

The runner is expected to be red — the defects it names are open issues. What must
be true regardless is that it runs all three industries, attributes each failure to
an owner, and cannot be quietly made green by deleting an expectation.
"""

from __future__ import annotations

import yaml

from bridgeflow import eval as acceptance
from bridgeflow.config import REPO_ROOT


async def test_it_checks_every_industry():
    report = await acceptance.run()

    # The golden path is per industry; the adversarial track is the suite's other half.
    assert {c.industry for c in report.checks if c.track == "golden"} == set(acceptance.INDUSTRIES)
    assert {c.track for c in report.checks} == {"golden", "adversarial"}


async def test_every_failure_is_either_owned_or_new():
    """A red row with no owner is a finding; a red row with one is a known gap.

    Both are fine. What is not fine is a red row nobody can trace to a decision.
    """
    report = await acceptance.run()

    unowned = [c for c in report.checks if not c.passed and not c.owner]
    for check in unowned:
        assert check.detail, f"{check.name} fails with no owner and no explanation"


async def test_the_planted_instruction_is_recognised_in_every_industry():
    """This one must be green. It is the rubric item the suite exists to prove."""
    report = await acceptance.run()

    recognised = [c for c in report.checks if "planted instruction" in c.name]
    # One per industry's held-out file, plus the standalone case in the adversarial track.
    assert len([c for c in recognised if c.track == "golden"]) == len(acceptance.INDUSTRIES)
    assert any(c.track == "adversarial" for c in recognised)
    assert all(c.passed for c in recognised)


def test_expectations_cannot_be_deleted_to_go_green():
    """Every acceptance set must still declare defects and a refusal.

    The failure mode this guards against is the tempting one: the suite is red, so
    someone removes the expectation rather than the defect.
    """
    for industry in acceptance.INDUSTRIES:
        expected = yaml.safe_load(
            (REPO_ROOT / "data" / "acceptance" / industry / "expected.yaml").read_text("utf-8")
        )
        assert len(expected["quality_defects"]) >= 5
        assert expected["refusals"]


async def test_the_report_names_the_issue_that_owns_a_known_gap():
    report = await acceptance.run()

    rendered = report.render()
    assert "#16" in rendered, "shifted columns and duplicate rows belong to #16"


async def test_a_metric_that_cannot_be_computed_says_why():
    """The suite's own output has to be actionable, not just a count."""
    report = await acceptance.run()

    failed_metrics = [c for c in report.checks if "total_output" in c.name and not c.passed]
    for check in failed_metrics:
        assert "Refusing" in check.detail or "declares" in check.detail
