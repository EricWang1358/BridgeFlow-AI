"""Versioned meeting preparation and minutes; never a project approval.

The authenticated transport must authorize all candidate/source departments and
supply the verified recorder. Participant names are reported attendance, not votes.
"""
from datetime import UTC, datetime
from typing import Literal

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
from bridgeflow.workflow.lifecycle import Event
from bridgeflow.workflow.store import ConcurrencyError, Pending


class CandidateVersion(Strict):
    id: Identifier
    version: int = Field(ge=1)


class MeetingStatement(Strict):
    text: Text
    basis: Literal["reported", "assumption"]
    references: list[Reference] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def reported_requires_source(self):
        if self.basis == "reported" and not self.references:
            raise ValueError("Reported statements require source references")
        return self


class ProposedStage(Strict):
    id: Identifier
    title: Label
    owner_role: Label
    exit_criteria: list[Text] = Field(min_length=1, max_length=10)
    depends_on: list[Identifier] = Field(default_factory=list, max_length=10)
    rationale: MeetingStatement


class MeetingInput(Strict):
    id: Identifier
    project_id: Identifier
    title: Label
    candidates: list[CandidateVersion] = Field(min_length=1, max_length=10)
    scope: list[MeetingStatement] = Field(min_length=1, max_length=20)
    exclusions: list[Text] = Field(default_factory=list, max_length=20)
    risks: list[MeetingStatement] = Field(default_factory=list, max_length=20)
    resources: list[MeetingStatement] = Field(default_factory=list, max_length=20)
    stages: list[ProposedStage] = Field(min_length=1, max_length=10)
    discussion_questions: list[Text] = Field(default_factory=list, max_length=30)
    phase: Literal["preparation", "minutes"] = "preparation"
    participants: list[Label] = Field(default_factory=list, max_length=30)
    minutes: list[MeetingStatement] = Field(default_factory=list, max_length=30)
    change_reason: Text
    expected_seq: int = Field(ge=0)

    @model_validator(mode="after")
    def consistent_draft(self):
        if len({c.id for c in self.candidates}) != len(self.candidates):
            raise ValueError("Candidate identifiers must be unique")
        ids = {s.id for s in self.stages}
        if len(ids) != len(self.stages):
            raise ValueError("Stage identifiers must be unique")
        dependencies = {s.id: set(s.depends_on) for s in self.stages}
        if any(not parents <= ids or identifier in parents for identifier, parents in dependencies.items()):
            raise ValueError("Stage dependencies must name other stages")
        resolved = set()
        while len(resolved) < len(ids):
            ready = {key for key, parents in dependencies.items() if parents <= resolved} - resolved
            if not ready:
                raise ValueError("Implementation stages cannot contain a dependency cycle")
            resolved.update(ready)
        if self.phase == "minutes" and (not self.participants or not self.minutes):
            raise ValueError("Minutes require reported participants and meeting notes")
        if self.phase == "preparation" and self.minutes:
            raise ValueError("Preparation cannot contain completed meeting minutes")
        return self

    def statements(self) -> list[MeetingStatement]:
        return [*self.scope, *self.risks, *self.resources, *(s.rationale for s in self.stages), *self.minutes]


class DiscoveryMeetings:
    def __init__(self, discovery: Discovery):
        self.discovery, self.store = discovery, discovery.store

    def save(self, meeting: MeetingInput, actor: str) -> dict:
        if not actor.strip():
            raise DiscoveryError("A verified meeting recorder is required")
        stream = self.discovery.stream("meeting", meeting.project_id, meeting.id)
        events = self.store.read(stream)
        if len(events) != meeting.expected_seq:
            raise ConcurrencyError("Meeting changed; reload before saving")
        if events and events[-1].data["phase"] == "minutes" and meeting.phase == "preparation":
            raise DiscoveryError("Recorded minutes cannot revert to preparation; create a new meeting")
        guards, snapshots, departments, refs = {}, [], set(), []
        for binding in meeting.candidates:
            candidate = self.discovery.opportunity(meeting.project_id, binding.id)
            if candidate["version"] != binding.version or candidate["stale_sources"]:
                raise DiscoveryError("Candidate or its evidence changed; review before preparing the meeting")
            snapshots.append(candidate)
            departments.update(candidate["departments"])
            refs.extend(Reference.model_validate(r) for c in candidate["claims"] for r in c["references"])
            candidate_stream = self.discovery.stream("opportunity", meeting.project_id, binding.id)
            guards[candidate_stream] = Pending(candidate_stream, binding.version, [])
        if events and set(events[-1].data["departments"]) != departments:
            raise DiscoveryError("Meeting department scope cannot change on revision")
        refs.extend(ref for statement in meeting.statements() for ref in statement.references)
        for ref in refs:
            material = self.discovery.read("material", meeting.project_id, ref.material_id)
            if material["department"] not in departments or material["parser_status"] != "parsed":
                raise DiscoveryError("Meeting source is outside scope or unparsed")
            if material["version"] != ref.version:
                raise DiscoveryError("Meeting source was revised")
            self.discovery.validate_locator(material, ref.locator)
            source_stream = self.discovery.stream("material", meeting.project_id, ref.material_id)
            guards[source_stream] = Pending(source_stream, ref.version, [])
        # Store referenced candidate contents, never raw source rows. Readbacks do
        # not silently replace the meeting's frozen basis with a newer proposal.
        data = {**meeting.model_dump(mode="json", exclude={"expected_seq"}), "actor": actor,
                "departments": sorted(departments), "candidate_snapshots": snapshots,
                "source_versions": sorted({(r.material_id, r.version) for r in refs}), "approval": "not_decided"}
        self.store.commit([*guards.values(), Pending(stream, meeting.expected_seq,
                          [Event(type="meeting_revision", data=data)])], at=datetime.now(UTC).isoformat())
        return self.read(meeting.project_id, meeting.id, meeting.expected_seq + 1)

    def read(self, project: str, identifier: str, version: int | None = None) -> dict:
        events = self.store.read(self.discovery.stream("meeting", project, identifier))
        if not events or version is not None and not 1 <= version <= len(events):
            raise DiscoveryError("Meeting version not found")
        event = events[-1] if version is None else events[version - 1]
        data = dict(event.data)
        stale_candidates = [c["id"] for c in data["candidates"]
                            if self.discovery.opportunity(project, c["id"])["version"] != c["version"]]
        stale_sources = [identifier for identifier, source_version in data["source_versions"]
                         if self.discovery.read("material", project, identifier)["version"] != source_version]
        return {**data, "seq": event.seq, "version": event.seq, "created_at": event.at,
                "stale_candidates": stale_candidates, "stale_sources": stale_sources,
                "status": "needs_review" if stale_candidates or stale_sources else "draft"}
