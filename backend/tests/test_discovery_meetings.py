import pytest
from pydantic import ValidationError
from test_discovery import domain as domain  # noqa: PLC0414 -- pytest fixture re-export
from test_discovery import material, opportunity

from bridgeflow.workflow.discovery import DiscoveryError
from bridgeflow.workflow.discovery_meetings import DiscoveryMeetings, MeetingInput
from bridgeflow.workflow.store import ConcurrencyError

REF = {"material_id": "source", "version": 1, "locator": {"kind": "header", "sheet": "csv"}}


def meeting(**changes):
    return MeetingInput.model_validate({"id": "workshop", "project_id": "project", "title": "Pilot discussion",
        "candidates": [{"id": "candidate", "version": 1}],
        "scope": [{"text": "Review the source structure", "basis": "reported", "references": [REF]}],
        "exclusions": ["No project approval in this meeting draft"],
        "risks": [{"text": "Availability is unconfirmed", "basis": "assumption"}],
        "resources": [{"text": "One reviewer may be needed; not a commitment", "basis": "assumption"}],
        "stages": [{"id": "pilot", "title": "Validate the proposal", "owner_role": "pilot owner",
                    "exit_criteria": ["Owner confirms the evidence"],
                    "rationale": {"text": "Proposed pilot, no measured savings", "basis": "assumption"}}],
        "discussion_questions": ["Who can validate the proposed scope?"],
        "expected_seq": 0, "change_reason": "Prepare initial agenda", **changes})


def prepared(domain):
    domain.register(material(), b"a,b\n", "employee")
    domain.propose(opportunity(), "employee")
    return DiscoveryMeetings(domain)


def test_preparation_and_minutes_retain_frozen_history_without_approval(domain):
    meetings = prepared(domain)
    saved = meetings.save(meeting(), "recorder")
    assert saved["actor"] == "recorder" and saved["approval"] == "not_decided"
    assert saved["resources"][0]["basis"] == "assumption"
    meetings.save(meeting(expected_seq=1, phase="minutes", participants=["reported attendee"],
                          minutes=[{"text": "Scope still needs confirmation", "basis": "reported", "references": [REF]}],
                          change_reason="Record discussion with source"), "other-recorder")
    assert DiscoveryMeetings(domain).read("project", "workshop", 1)["phase"] == "preparation"
    assert meetings.read("project", "workshop")["version"] == 2
    assert domain.opportunity("project", "candidate")["approval"] == "not_decided"
    assert domain.store.streams("handoff:") == [] and domain.store.notifications() == []
    with pytest.raises(DiscoveryError, match="cannot revert"):
        meetings.save(meeting(expected_seq=2), "recorder")
    assert meetings.read("project", "workshop")["version"] == 2


def test_meeting_revisions_signal_stale_inputs_without_rewriting_snapshot(domain):
    meetings = prepared(domain)
    original = meetings.save(meeting(), "recorder")["candidate_snapshots"]
    domain.propose(opportunity(expected_seq=1, title="Changed candidate"), "employee")
    domain.register(material(expected_seq=1), b"c,d\n", "employee")
    saved = meetings.read("project", "workshop")
    assert saved["candidate_snapshots"] == original
    assert saved["stale_candidates"] == ["candidate"] and saved["stale_sources"] == ["source"]
    assert saved["status"] == "needs_review"
    with pytest.raises(DiscoveryError, match="changed"):
        meetings.save(meeting(expected_seq=1), "recorder")


def test_meeting_requires_sourced_claims_and_explicit_valid_stages():
    with pytest.raises(ValidationError, match="source references"):
        meeting(scope=[{"text": "Claimed measured savings", "basis": "reported"}])
    with pytest.raises(ValidationError, match="participants"):
        meeting(phase="minutes")
    stages = meeting().model_dump()["stages"]
    stages[0]["depends_on"] = ["missing"]
    with pytest.raises(ValidationError, match="other stages"):
        meeting(stages=stages)
    stages[0]["depends_on"] = ["next"]
    stages.append({**stages[0], "id": "next", "depends_on": ["pilot"]})
    with pytest.raises(ValidationError, match="cycle"):
        meeting(stages=stages)


def test_meeting_scope_actor_and_sequence_protect_existing_record(domain):
    meetings = prepared(domain)
    with pytest.raises(DiscoveryError, match="recorder"):
        meetings.save(meeting(), " ")
    meetings.save(meeting(), "recorder")
    with pytest.raises(ConcurrencyError):
        meetings.save(meeting(), "recorder")
    domain.register(material(id="secret", department="finance"), b"a,b\n", "employee")
    with pytest.raises(DiscoveryError, match="scope"):
        meetings.save(meeting(expected_seq=1, risks=[{"text": "Unauthorized source", "basis": "reported",
            "references": [{**REF, "material_id": "secret"}]}]), "recorder")
    assert meetings.read("project", "workshop")["version"] == 1


@pytest.mark.parametrize("race_kind", ["candidate", "source"])
def test_meeting_guards_all_input_versions_in_commit(domain, monkeypatch, race_kind):
    meetings = prepared(domain)
    commit = domain.store.commit
    def race(pending, *args, **kwargs):
        monkeypatch.setattr(domain.store, "commit", commit)
        if race_kind == "candidate":
            domain.propose(opportunity(expected_seq=1, title="concurrent edit"), "employee")
        else:
            domain.register(material(expected_seq=1), b"c,d\n", "employee")
        return commit(pending, *args, **kwargs)
    monkeypatch.setattr(domain.store, "commit", race)
    with pytest.raises(ConcurrencyError):
        meetings.save(meeting(), "recorder")
    assert domain.store.streams("discovery:meeting:") == []
