"""Human-declared voting and explicit MVP decisions over frozen meeting inputs.

Transport supplies verified subjects and enforces native approval plus data scope.
A recorded vote, conditional decision or historical approval is not a live handoff.
"""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from bridgeflow.workflow.discovery import (
    Discovery,
    DiscoveryError,
    Identifier,
    Label,
    Reference,
    Strict,
    Text,
)
from bridgeflow.workflow.discovery_meetings import DiscoveryMeetings
from bridgeflow.workflow.lifecycle import Event
from bridgeflow.workflow.store import ConcurrencyError, Pending


class DecisionPolicy(Strict):
    id: Identifier
    project_id: Identifier
    version: int = Field(ge=1)
    departments: list[Label] = Field(min_length=1, max_length=20)
    declared_by: Label
    declaration_ref: Text
    proposers: list[Label] = Field(min_length=1, max_length=50)
    voters: list[Label] = Field(min_length=1, max_length=50)
    approvers: list[Label] = Field(min_length=1, max_length=50)
    condition_confirmers: list[Label] = Field(min_length=1, max_length=50)
    quorum: int = Field(ge=1)
    minimum_yes: int = Field(ge=1)
    no_votes_block: bool
    abstentions_count_for_quorum: bool
    agent2_owner_role: Label

    @model_validator(mode="after")
    def valid_rules(self):
        for key in ("proposers", "voters", "approvers", "condition_confirmers", "departments"):
            values = getattr(self, key)
            if len(set(values)) != len(values):
                raise ValueError(f"{key} must be unique")
        if self.quorum > len(self.voters) or self.minimum_yes > len(self.voters):
            raise ValueError("Voting thresholds exceed the declared electorate")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.model_dump(mode="json"), sort_keys=True,
                                         ensure_ascii=False).encode()).hexdigest()


def load_decision_policy(path: str | Path) -> DecisionPolicy:
    if not str(path):
        raise DiscoveryError("Decision policy not configured")
    try:
        raw = Path(path).read_bytes()
        if len(raw) > 65536:
            raise ValueError("Policy exceeds 64 KiB")
        return DecisionPolicy.model_validate(yaml.safe_load(raw))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise DiscoveryError("Decision policy unavailable or invalid") from exc


class DecisionCondition(Strict):
    id: Identifier
    description: Text
    confirmer: Label


class DecisionProposal(Strict):
    id: Identifier
    project_id: Identifier
    meeting_id: Identifier
    meeting_version: int = Field(ge=1)
    selected_candidates: list[Identifier] = Field(min_length=1, max_length=10)
    scope: list[Text] = Field(min_length=1, max_length=20)
    exclusions: list[Text] = Field(default_factory=list, max_length=20)
    rationale: Text
    conditions: list[DecisionCondition] = Field(default_factory=list, max_length=20)
    policy_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_seq: int = Field(ge=0)

    @model_validator(mode="after")
    def unique_ids(self):
        if len(set(self.selected_candidates)) != len(self.selected_candidates):
            raise ValueError("Selected candidates must be unique")
        if len({c.id for c in self.conditions}) != len(self.conditions):
            raise ValueError("Condition identifiers must be unique")
        return self


class DiscoveryDecisions:
    def __init__(self, discovery: Discovery, policy: DecisionPolicy):
        self.discovery, self.store, self.policy = discovery, discovery.store, policy

    def _subject(self, actor: str, role: str):
        if not actor.strip() or actor not in getattr(self.policy, role):
            raise DiscoveryError(f"Verified subject is not a declared {role} member")

    def _event(self, project: str, identifier: str, version: int | None = None):
        if project != self.policy.project_id:
            raise DiscoveryError("Decision policy belongs to another project")
        events = self.store.read(self.discovery.stream("decision", project, identifier))
        if not events or version is not None and not 1 <= version <= len(events):
            raise DiscoveryError("Decision version not found")
        return events[-1] if version is None else events[version - 1]

    def _stale(self, data: dict) -> list[str]:
        reasons = []
        project = data["project_id"]
        if data["policy_fingerprint"] != self.policy.fingerprint:
            reasons.append("policy_revised")
        if self.discovery.read("meeting", project, data["meeting_id"])["version"] != data["meeting_version"]:
            reasons.append("meeting_revised")
        for candidate in data["meeting_snapshot"]["candidates"]:
            if self.discovery.read("opportunity", project, candidate["id"])["version"] != candidate["version"]:
                reasons.append("candidate_revised")
        for identifier, version in data["source_versions"]:
            if self.discovery.read("material", project, identifier)["version"] != version:
                reasons.append("source_revised")
        return sorted(set(reasons))

    def _guards(self, data: dict) -> list[Pending]:
        if self._stale(data):
            raise DiscoveryError("Decision inputs or policy changed; revise and collect new votes")
        project = data["project_id"]
        bindings = [("meeting", data["meeting_id"], data["meeting_version"])]
        bindings += [("opportunity", c["id"], c["version"]) for c in data["meeting_snapshot"]["candidates"]]
        bindings += [("material", identifier, version) for identifier, version in data["source_versions"]]
        return [Pending(self.discovery.stream(kind, project, identifier), version, []) for kind, identifier, version in bindings]

    def _append(self, data: dict, expected: int, actor: str, action: str) -> dict:
        guards = self._guards(data)
        data["last_actor"], data["last_action"] = actor, action
        stream = self.discovery.stream("decision", data["project_id"], data["id"])
        self.store.commit([*guards, Pending(stream, expected, [Event(type=action, data=data)])],
                          at=datetime.now(UTC).isoformat())
        return self.read(data["project_id"], data["id"], expected + 1)

    def propose(self, proposal: DecisionProposal, actor: str) -> dict:
        self._subject(actor, "proposers")
        if proposal.project_id != self.policy.project_id or proposal.policy_fingerprint != self.policy.fingerprint:
            raise DiscoveryError("Decision policy changed or belongs to another project")
        meeting = DiscoveryMeetings(self.discovery).read(proposal.project_id, proposal.meeting_id)
        if meeting["version"] != proposal.meeting_version or meeting["status"] == "needs_review":
            raise DiscoveryError("Meeting or its inputs changed")
        if meeting["phase"] != "minutes":
            raise DiscoveryError("Recorded meeting minutes are required before a decision proposal")
        if not set(meeting["departments"]) <= set(self.policy.departments):
            raise DiscoveryError("Meeting is outside decision policy scope")
        if not set(proposal.selected_candidates) <= {c["id"] for c in meeting["candidates"]}:
            raise DiscoveryError("Selected candidates must belong to the frozen meeting")
        if any(c.confirmer not in self.policy.condition_confirmers for c in proposal.conditions):
            raise DiscoveryError("Condition confirmer is not declared in policy")
        events = self.store.read(self.discovery.stream("decision", proposal.project_id, proposal.id))
        if len(events) != proposal.expected_seq:
            raise ConcurrencyError("Decision changed; reload before proposing")
        if events and set(events[-1].data["departments"]) != set(meeting["departments"]):
            raise DiscoveryError("Decision department scope cannot change on revision")
        data = {**proposal.model_dump(mode="json", exclude={"expected_seq"}), "proposer": actor,
                "proposal_version": events[-1].data["proposal_version"] + 1 if events else 1,
                "policy": self.policy.model_dump(mode="json"), "meeting_snapshot": meeting,
                "departments": meeting["departments"], "source_versions": meeting["source_versions"],
                "votes": {}, "resolutions": {}, "recorded_status": "proposed", "finalization": None}
        return self._append(data, proposal.expected_seq, actor, "decision_proposed")

    def _current(self, project: str, identifier: str, expected_seq: int, proposal_version: int) -> dict:
        event = self._event(project, identifier)
        if event.seq != expected_seq or event.data["proposal_version"] != proposal_version:
            raise ConcurrencyError("Decision or proposal changed; reload before acting")
        data = dict(event.data)
        self._guards(data)
        return data

    def vote(self, project: str, identifier: str, expected_seq: int, proposal_version: int,
             actor: str, choice: Literal["yes", "no", "abstain"], rationale: str) -> dict:
        self._subject(actor, "voters")
        if choice not in {"yes", "no", "abstain"} or not rationale.strip() or len(rationale) > 1200:
            raise DiscoveryError("A valid vote and bounded rationale are required")
        data = self._current(project, identifier, expected_seq, proposal_version)
        if data["recorded_status"] != "proposed":
            raise DiscoveryError("Voting is closed; revise the proposal before collecting new votes")
        data["votes"][actor] = {"actor": actor, "choice": choice, "rationale": rationale}
        return self._append(data, expected_seq, actor, "decision_vote")

    def resolve(self, project: str, identifier: str, expected_seq: int, proposal_version: int,
                actor: str, condition_id: str, rationale: str, references: list[Reference]) -> dict:
        self._subject(actor, "condition_confirmers")
        if not rationale.strip() or len(rationale) > 1200 or not 1 <= len(references) <= 10:
            raise DiscoveryError("Condition resolution requires rationale and source evidence")
        data = self._current(project, identifier, expected_seq, proposal_version)
        if data["recorded_status"] not in {"proposed", "conditional"}:
            raise DiscoveryError("Final decisions cannot change conditions; revise the proposal")
        condition = next((c for c in data["conditions"] if c["id"] == condition_id), None)
        if condition is None or condition["confirmer"] != actor:
            raise DiscoveryError("Only the assigned subject can confirm this condition")
        versions = {tuple(v) for v in data["source_versions"]}
        for ref in references:
            material = self.discovery.read("material", project, ref.material_id)
            if material["version"] != ref.version or material["department"] not in data["departments"]:
                raise DiscoveryError("Condition evidence is stale or outside scope")
            if material["parser_status"] != "parsed":
                raise DiscoveryError("Condition evidence must be parsed")
            self.discovery.validate_locator(material, ref.locator)
            versions.add((ref.material_id, ref.version))
        data["source_versions"] = sorted(versions)
        data["resolutions"][condition_id] = {"actor": actor, "rationale": rationale,
                                            "references": [r.model_dump(mode="json") for r in references]}
        return self._append(data, expected_seq, actor, "decision_condition_confirmed")

    def _tally(self, data: dict) -> dict:
        # Replay uses the frozen declaration, never the new policy's thresholds.
        policy = DecisionPolicy.model_validate(data["policy"])
        counts = {choice: sum(v["choice"] == choice for v in data["votes"].values()) for choice in ("yes", "no", "abstain")}
        participation = counts["yes"] + counts["no"] + (counts["abstain"] if policy.abstentions_count_for_quorum else 0)
        return {**counts, "participation": participation,
                "passes": participation >= policy.quorum and counts["yes"] >= policy.minimum_yes
                and not (policy.no_votes_block and counts["no"])}

    def decide(self, project: str, identifier: str, expected_seq: int, proposal_version: int,
               actor: str, outcome: Literal["approve", "reject"], rationale: str) -> dict:
        self._subject(actor, "approvers")
        if outcome not in {"approve", "reject"} or not rationale.strip() or len(rationale) > 1200:
            raise DiscoveryError("Explicit decision and bounded rationale required")
        data = self._current(project, identifier, expected_seq, proposal_version)
        if data["recorded_status"] not in {"proposed", "conditional"}:
            raise DiscoveryError("A final decision exists; create a new proposal revision")
        if outcome == "approve" and not self._tally(data)["passes"]:
            raise DiscoveryError("Declared voting conditions are not satisfied")
        pending = {c["id"] for c in data["conditions"]} - data["resolutions"].keys()
        data["recorded_status"] = "rejected" if outcome == "reject" else "conditional" if pending else "approved"
        data["finalization"] = {"actor": actor, "rationale": rationale, "outcome": outcome,
                                "status": data["recorded_status"]}
        return self._append(data, expected_seq, actor, "decision_recorded")

    def read(self, project: str, identifier: str, version: int | None = None) -> dict:
        event = self._event(project, identifier, version)
        data = dict(event.data)
        reasons = self._stale(data)
        current = self._event(project, identifier)
        if event.seq != current.seq:
            reasons.append("historical_revision")
        status = "needs_review" if reasons else data["recorded_status"]
        handoff = None
        if status == "approved":
            handoff = {"decision_id": identifier, "decision_seq": event.seq, "proposal_version": data["proposal_version"],
                       "project_id": project, "owner_role": data["policy"]["agent2_owner_role"],
                       "candidates": [c for c in data["meeting_snapshot"]["candidates"] if c["id"] in data["selected_candidates"]],
                       "scope": data["scope"], "exclusions": data["exclusions"],
                       "meeting_id": data["meeting_id"], "meeting_version": data["meeting_version"],
                       "policy_fingerprint": data["policy_fingerprint"]}
        return {**data, "seq": event.seq, "version": event.seq, "created_at": event.at,
                "status": status, "stale_reasons": reasons, "tally": self._tally(data),
                "pending_conditions": [c["id"] for c in data["conditions"] if c["id"] not in data["resolutions"]],
                "agent2_handoff": handoff}
