import pytest
from pydantic import ValidationError
from test_discovery import domain as domain  # noqa: PLC0414 -- pytest fixture re-export
from test_discovery import material, opportunity
from test_discovery_meetings import REF, meeting

from bridgeflow.workflow.discovery import DiscoveryError, Reference
from bridgeflow.workflow.discovery_decisions import (
    DecisionPolicy,
    DecisionProposal,
    DiscoveryDecisions,
    load_decision_policy,
)
from bridgeflow.workflow.discovery_meetings import DiscoveryMeetings
from bridgeflow.workflow.store import ConcurrencyError


def policy(**changes):
    return DecisionPolicy.model_validate({"id": "pilot-rules", "project_id": "project", "version": 1,
        "departments": ["production"], "declared_by": "synthetic-owner", "declaration_ref": "Synthetic test only",
        "proposers": ["proposer"], "voters": ["voter-a", "voter-b"], "approvers": ["approver"],
        "condition_confirmers": ["checker", "other-checker"], "quorum": 2, "minimum_yes": 2,
        "no_votes_block": True, "abstentions_count_for_quorum": False,
        "agent2_owner_role": "standardization owner", **changes})


def proposal(**changes):
    return DecisionProposal.model_validate({"id": "mvp", "project_id": "project", "meeting_id": "workshop",
        "meeting_version": 1, "selected_candidates": ["candidate"], "scope": ["Pilot only"],
        "exclusions": ["No rollout approval"], "rationale": "Discussed pilot scope", "expected_seq": 0,
        "policy_fingerprint": policy().fingerprint, **changes})


def prepared(domain, rules=None):
    domain.register(material(), b"a,b\n", "employee")
    domain.propose(opportunity(), "employee")
    DiscoveryMeetings(domain).save(meeting(phase="minutes", participants=["Reported attendee"],
        minutes=[{"text": "Pilot remains a proposal", "basis": "reported", "references": [REF]}]), "recorder")
    return DiscoveryDecisions(domain, rules or policy())


def voted(decisions, **changes):
    decisions.propose(proposal(**changes), "proposer")
    decisions.vote("project", "mvp", 1, 1, "voter-a", "yes", "Evidence reviewed")
    return decisions.vote("project", "mvp", 2, 1, "voter-b", "yes", "Support pilot")


def test_votes_never_approve_without_designated_decider(domain):
    decisions = prepared(domain)
    state = voted(decisions)
    assert state["tally"]["passes"] and state["status"] == "proposed"
    assert state["agent2_handoff"] is None
    with pytest.raises(DiscoveryError, match="approvers"):
        decisions.decide("project", "mvp", 3, 1, "voter-a", "approve", "Not my role")
    approved = decisions.decide("project", "mvp", 3, 1, "approver", "approve", "Approve this pilot only")
    assert approved["status"] == "approved"
    assert approved["finalization"]["actor"] == "approver"
    assert approved["agent2_handoff"]["candidates"] == [{"id": "candidate", "version": 1}]
    assert approved["agent2_handoff"]["exclusions"] == ["No rollout approval"]
    assert domain.store.notifications() == [] and domain.store.streams("handoff:") == []
    with pytest.raises(DiscoveryError, match="Voting is closed"):
        decisions.vote("project", "mvp", 4, 1, "voter-a", "no", "Reconsider")


def test_conditional_decision_requires_assigned_evidence_then_explicit_release(domain):
    decisions = prepared(domain)
    voted(decisions, conditions=[{"id": "check", "description": "Confirm source", "confirmer": "checker"}])
    conditional = decisions.decide("project", "mvp", 3, 1, "approver", "approve", "Only after source check")
    assert conditional["status"] == "conditional" and conditional["agent2_handoff"] is None
    refs = [Reference.model_validate(REF)]
    with pytest.raises(DiscoveryError, match="assigned"):
        decisions.resolve("project", "mvp", 4, 1, "other-checker", "check", "Not assigned", refs)
    with pytest.raises(DiscoveryError, match="evidence"):
        decisions.resolve("project", "mvp", 4, 1, "checker", "check", "No source", [])
    resolved = decisions.resolve("project", "mvp", 4, 1, "checker", "check", "Source checked", refs)
    assert resolved["pending_conditions"] == [] and resolved["status"] == "conditional"
    assert resolved["agent2_handoff"] is None
    approved = decisions.decide("project", "mvp", 5, 1, "approver", "approve", "Conditions checked; release scope")
    assert approved["status"] == "approved"
    assert approved["resolutions"]["check"]["actor"] == "checker"


def test_policy_thresholds_abstention_veto_and_vote_replacement(domain):
    rules = policy(minimum_yes=1, abstentions_count_for_quorum=True)
    decisions = prepared(domain, rules)
    decisions.propose(proposal(policy_fingerprint=rules.fingerprint), "proposer")
    decisions.vote("project", "mvp", 1, 1, "voter-a", "yes", "Support")
    with pytest.raises(DiscoveryError, match="voting conditions"):
        decisions.decide("project", "mvp", 2, 1, "approver", "approve", "Too early")
    state = decisions.vote("project", "mvp", 2, 1, "voter-b", "no", "Veto")
    assert state["tally"]["participation"] == 2 and not state["tally"]["passes"]
    state = decisions.vote("project", "mvp", 3, 1, "voter-b", "abstain", "Withdraw objection")
    assert len(state["votes"]) == 2 and state["tally"]["passes"]
    assert decisions.read("project", "mvp", 3)["votes"]["voter-b"]["choice"] == "no"
    decisions.decide("project", "mvp", 4, 1, "approver", "approve", "Threshold passed under declared rule")


def test_revise_invalidates_votes_conditions_and_old_handoff(domain):
    decisions = prepared(domain)
    voted(decisions)
    decisions.decide("project", "mvp", 3, 1, "approver", "approve", "Pilot approved")
    revised = decisions.propose(proposal(expected_seq=4, scope=["A different scope"]), "proposer")
    assert revised["proposal_version"] == 2 and revised["votes"] == {} and revised["resolutions"] == {}
    assert revised["status"] == "proposed" and revised["agent2_handoff"] is None
    old = decisions.read("project", "mvp", 4)
    assert old["recorded_status"] == "approved" and old["agent2_handoff"] is None
    assert "historical_revision" in old["stale_reasons"]
    with pytest.raises(ConcurrencyError):
        decisions.vote("project", "mvp", 5, 1, "voter-a", "yes", "Old proposal version")


@pytest.mark.parametrize("changed", ["policy", "meeting", "candidate", "source"])
def test_upstream_changes_withdraw_handoff_and_reject_further_actions(domain, changed):
    decisions = prepared(domain)
    voted(decisions)
    decisions.decide("project", "mvp", 3, 1, "approver", "approve", "Approved")
    if changed == "policy":
        decisions = DiscoveryDecisions(domain, policy(version=2))
    elif changed == "meeting":
        DiscoveryMeetings(domain).save(meeting(expected_seq=1, phase="minutes", participants=["person"],
            minutes=[{"text": "Revised discussion", "basis": "assumption"}]), "recorder")
    elif changed == "candidate":
        domain.propose(opportunity(expected_seq=1, title="Changed scope"), "employee")
    else:
        domain.register(material(expected_seq=1), b"c,d\n", "employee")
    state = decisions.read("project", "mvp")
    assert state["status"] == "needs_review" and state["agent2_handoff"] is None
    assert f"{changed}_revised" in state["stale_reasons"]
    with pytest.raises(DiscoveryError, match="changed"):
        decisions.decide("project", "mvp", 4, 1, "approver", "reject", "Cannot decide on stale basis")


def test_policy_requires_explicit_rules_and_valid_electorate(tmp_path):
    for path in ("", tmp_path / "absent.yaml"):
        with pytest.raises(DiscoveryError):
            load_decision_policy(path)
    with pytest.raises(ValidationError):
        policy(quorum=3)
    with pytest.raises(ValidationError):
        policy(voters=["same", "same"])
    values = policy().model_dump()
    del values["no_votes_block"]
    with pytest.raises(ValidationError):
        DecisionPolicy.model_validate(values)
    path = tmp_path / "policy.json"
    path.write_text(policy().model_dump_json())
    assert load_decision_policy(path).fingerprint == policy().fingerprint


def test_nonmembers_cannot_propose_vote_or_resolve_and_rejection_is_explicit(domain):
    decisions = prepared(domain)
    with pytest.raises(DiscoveryError, match="proposers"):
        decisions.propose(proposal(), "attendee")
    decisions.propose(proposal(), "proposer")
    with pytest.raises(DiscoveryError, match="voters"):
        decisions.vote("project", "mvp", 1, 1, "attendee", "yes", "Reported meeting attendance is not eligibility")
    rejected = decisions.decide("project", "mvp", 1, 1, "approver", "reject", "Outside current priorities")
    assert rejected["status"] == "rejected" and rejected["agent2_handoff"] is None


def test_decision_commit_guards_meeting_changes_after_validation(domain, monkeypatch):
    decisions = prepared(domain)
    decisions.propose(proposal(), "proposer")
    commit = domain.store.commit
    def race(pending, *args, **kwargs):
        monkeypatch.setattr(domain.store, "commit", commit)
        DiscoveryMeetings(domain).save(meeting(expected_seq=1, phase="minutes", participants=["person"],
            minutes=[{"text": "Concurrent edit", "basis": "assumption"}]), "recorder")
        return commit(pending, *args, **kwargs)
    monkeypatch.setattr(domain.store, "commit", race)
    with pytest.raises(ConcurrencyError):
        decisions.vote("project", "mvp", 1, 1, "voter-a", "yes", "Now stale")
    assert decisions.read("project", "mvp")["votes"] == {}
