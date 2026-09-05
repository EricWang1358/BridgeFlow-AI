"""Tests for remembering what a person already decided.

`docs/01` promises month two costs a fraction of month one. That only holds if a
confirmation survives the run it was made in; otherwise every month asks the same
questions and the reviewer learns that answering them changes nothing.
"""

from __future__ import annotations

import pytest

from bridgeflow import mappings
from bridgeflow.schemas import Link


@pytest.fixture
def memory_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "bridgeflow.config.settings.mapping_memory_path", str(tmp_path / "mappings.json")
    )
    return tmp_path


def _link(justification: str = "marketing 2025-11 row 2") -> Link:
    return Link(
        source="sku:sku-a1",
        target="customer:acme-pte-ltd",
        relation="ordered_by",
        confidence=0.4,
        justification=justification,
    )


def test_an_accepted_mapping_is_not_asked_again(memory_file):
    mappings.confirm(_link(), by="ops@example.com", accepted=True, period="2025-11")

    settled, still_open = mappings.apply([_link()])

    assert len(settled) == 1
    assert not still_open
    assert settled[0].confidence == 1.0


def test_a_confirmation_carries_who_and_when(memory_file):
    """It is a decision somebody can be held to, not a cache entry."""
    mappings.confirm(_link(), by="ops@example.com", accepted=True)

    settled, _ = mappings.apply([_link()])

    assert "ops@example.com" in settled[0].justification


def test_a_rejected_mapping_stays_rejected(memory_file):
    """Re-asking a question somebody already answered no to is how a queue loses
    its reader."""
    mappings.confirm(_link(), by="ops@example.com", accepted=False)

    settled, still_open = mappings.apply([_link()])

    assert not settled
    assert not still_open


def test_a_confirmation_goes_stale_when_the_evidence_changes(memory_file):
    """The decision was made about something specific.

    Reusing it against different evidence is how a stale mapping outlives the reason
    for it.
    """
    mappings.confirm(_link("marketing 2025-11 row 2"), by="ops@example.com", accepted=True)

    settled, still_open = mappings.apply([_link("marketing 2025-12 row 7")])

    assert not settled
    assert still_open
    assert "asked again" in still_open[0].justification


def test_an_unseen_mapping_is_still_an_open_question(memory_file):
    settled, still_open = mappings.apply([_link()])

    assert not settled
    assert len(still_open) == 1


def test_the_latest_answer_replaces_the_earlier_one(memory_file):
    mappings.confirm(_link(), by="a@example.com", accepted=True)
    mappings.confirm(_link(), by="b@example.com", accepted=False)

    settled, still_open = mappings.apply([_link()])

    assert not settled and not still_open, "the newer rejection wins"


def test_every_confirmation_is_versioned(memory_file):
    """A batch computed under an older set of mappings must stay reproducible —
    FR 11 forbids a mapping change from silently recomputing a published batch."""
    mappings.confirm(_link(), by="ops@example.com", accepted=True)

    versions = list((memory_file / "versions").glob("mappings--*.json"))

    assert versions
