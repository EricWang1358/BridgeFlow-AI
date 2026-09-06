"""Tests for the gate in front of anything that writes.

The property under test is not "a dialog appears" — it is that absence of an answer
is a denial. `sdk-minimal` composes no approval service at all, so before this the
question was never asked; with the service loaded and nothing composed to answer it,
a mutating call is refused rather than performed unattended.

Verified against the live runtime on 2026-09-06:

    Error: tool "confirm_mapping" requires approval, but no approval channel is
    available

and nothing was written.
"""

from __future__ import annotations

import re

import pytest
import yaml
from fastapi.testclient import TestClient

from bridgeflow import mappings
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT

GATE = REPO_ROOT / "plugins" / "src" / "approval" / "gate.ts"
PATCH = REPO_ROOT / "dsh" / "approval.patch.yml"


def _gated_tools() -> set[str]:
    source = GATE.read_text(encoding="utf-8")
    # Anchored on the assignment: the type annotation contains `[]` too.
    body = source.split("MUTATING_TOOLS: readonly string[] = [", 1)[1]
    return set(re.findall(r"'([a-z_]+)'", body[: body.index("]")]))


def test_the_only_writing_tool_is_gated():
    """If a second writing tool appears and is not listed here, this fails."""
    assert _gated_tools() == {"confirm_mapping"}


def test_reading_tools_are_not_gated():
    """Asking someone to approve list_metrics teaches them to approve without
    reading, which is worse than not asking."""
    gated = _gated_tools()

    for tool in ("list_metrics", "aggregate_metric", "lookup_field_dictionary"):
        assert tool not in gated


def test_the_approval_service_is_actually_loaded():
    """The gate returns `ask`, which denies unless a service answers. With no
    service composed the question is never asked — the state sdk-minimal ships in."""
    patch = yaml.safe_load(PATCH.read_text(encoding="utf-8"))
    inserted = [row for entry in patch for row in entry.get("insert", [])]

    assert any(row["name"] == "@deepseek-ai/dsh-user-approval" for row in inserted)


def test_the_policy_is_ask_rather_than_never():
    """`never` refuses without anyone seeing the question — right for CI, wrong for
    an operator sitting in front of it."""
    patch = yaml.safe_load(PATCH.read_text(encoding="utf-8"))
    inserted = [row for entry in patch for row in entry.get("insert", [])]
    approval = next(r for r in inserted if r["name"] == "@deepseek-ai/dsh-user-approval")

    assert approval["config"]["policy"] == "ask"


@pytest.fixture
def memory_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "bridgeflow.config.settings.mapping_memory_path", str(tmp_path / "mappings.json")
    )
    return tmp_path


def test_an_approved_confirmation_is_recorded_with_who_and_when(memory_file):
    """Reaching the endpoint means the gate let it through, which is the fact an
    auditor reads — so the identity has to survive into the record."""
    body = TestClient(app).post(
        "/tools/confirm-mapping",
        json={
            "source": "sku:sku-a1",
            "target": "customer:acme-pte-ltd",
            "relation": "ordered_by",
            "accepted": True,
            "confirmed_by": "agent-7",
            "evidence": "marketing row 2",
        },
    ).json()

    assert body["confirmed_by"] == "agent-7"
    assert body["confirmed_at"]
    assert body["remembered"] == 1
    assert mappings.load().confirmations[0].evidence == "marketing row 2"


def test_a_rejection_is_recorded_as_deliberately_as_an_acceptance(memory_file):
    body = TestClient(app).post(
        "/tools/confirm-mapping",
        json={
            "source": "sku:sku-b7",
            "target": "customer:bayfront-ltd",
            "relation": "ordered_by",
            "accepted": False,
            "confirmed_by": "agent-7",
        },
    ).json()

    assert body["accepted"] is False
    assert mappings.load().confirmations[0].accepted is False
