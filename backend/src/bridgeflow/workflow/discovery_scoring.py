"""Evidence-backed coordinates under a human-declared, fingerprinted scoring policy."""
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated

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
from bridgeflow.workflow.lifecycle import Event
from bridgeflow.workflow.store import ConcurrencyError, Pending

Number = Annotated[Decimal, Field(allow_inf_nan=False, max_digits=18, decimal_places=6)]


class Axis(Strict):
    title: Label
    unit: Label
    minimum: Number
    maximum: Number
    split: Number
    split_is_high: bool
    low_meaning: Text
    high_meaning: Text

    @model_validator(mode="after")
    def valid_scale(self):
        if not self.minimum < self.split < self.maximum:
            raise ValueError("Axis split must lie strictly inside the declared scale")
        return self


class ScoringPolicy(Strict):
    id: Identifier
    project_id: Identifier
    version: int = Field(ge=1)
    departments: list[Label] = Field(min_length=1, max_length=20)
    declared_by: Label
    declaration_ref: Text
    effort: Axis
    value: Axis

    @property
    def fingerprint(self) -> str:
        encoded = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False).encode()
        return hashlib.sha256(encoded).hexdigest()


def load_policy(path: str | Path) -> ScoringPolicy:
    if not str(path):
        raise DiscoveryError("Scoring policy not configured")
    try:
        data = Path(path).read_bytes()
        if len(data) > 65536:
            raise ValueError("Policy exceeds 64 KiB")
        return ScoringPolicy.model_validate(yaml.safe_load(data))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise DiscoveryError("Scoring policy unavailable or invalid") from exc


class Rating(Strict):
    score: Number | None = None
    rationale: str = Field("", max_length=1200)
    references: list[Reference] = Field(default_factory=list, max_length=10)


class ScoreDraft(Strict):
    id: Identifier
    project_id: Identifier
    opportunity_id: Identifier
    opportunity_version: int = Field(ge=1)
    policy_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    effort: Rating | None = None
    value: Rating | None = None
    expected_seq: int = Field(ge=0)


class DiscoveryScores:
    def __init__(self, discovery: Discovery, policy: ScoringPolicy):
        self.discovery, self.store, self.policy = discovery, discovery.store, policy

    def save(self, score: ScoreDraft, actor: str) -> dict:
        if not actor.strip():
            raise DiscoveryError("A verified scorer is required")
        if score.project_id != self.policy.project_id or score.policy_fingerprint != self.policy.fingerprint:
            raise DiscoveryError("Scoring policy changed or belongs to another project")
        candidate = self.discovery.opportunity(score.project_id, score.opportunity_id)
        if candidate["version"] != score.opportunity_version or candidate["stale_sources"]:
            raise DiscoveryError("Candidate or its evidence changed; review before scoring")
        if not set(candidate["departments"]) <= set(self.policy.departments):
            raise DiscoveryError("Candidate departments are outside the scoring policy")
        refs = [Reference.model_validate(ref) for c in candidate["claims"] for ref in c["references"]]
        for name in ("effort", "value"):
            rating, axis = getattr(score, name), getattr(self.policy, name)
            if rating is not None:
                if rating.score is not None and not axis.minimum <= rating.score <= axis.maximum:
                    raise DiscoveryError(f"{name} is outside its declared scale")
                refs.extend(rating.references)
        stream = self.discovery.stream("score", score.project_id, score.id)
        events = self.store.read(stream)
        if len(events) != score.expected_seq:
            raise ConcurrencyError("Score revision changed; reload before saving")
        if events and events[-1].data["opportunity_id"] != score.opportunity_id:
            raise DiscoveryError("A score cannot be reassigned to another candidate")
        guards = {}
        candidate_stream = self.discovery.stream("opportunity", score.project_id, score.opportunity_id)
        guards[candidate_stream] = Pending(candidate_stream, score.opportunity_version, [])
        for ref in refs:
            material = self.discovery.read("material", score.project_id, ref.material_id)
            if material["department"] not in candidate["departments"] or material["parser_status"] != "parsed":
                raise DiscoveryError("Score source is outside scope or unparsed")
            if material["version"] != ref.version:
                raise DiscoveryError("Score source was revised")
            self.discovery.validate_locator(material, ref.locator)
            source_stream = self.discovery.stream("material", score.project_id, ref.material_id)
            guards[source_stream] = Pending(source_stream, ref.version, [])
        data = {**score.model_dump(mode="json", exclude={"expected_seq"}), "actor": actor,
                "departments": candidate["departments"], "policy": self.policy.model_dump(mode="json")}
        now = datetime.now(UTC).isoformat()
        self.store.commit([*guards.values(), Pending(stream, score.expected_seq,
                          [Event(type="score_revision", data=data)])], at=now)
        return self.read(score.project_id, score.id, score.expected_seq + 1)

    def read(self, project: str, identifier: str, version: int | None = None) -> dict:
        events = self.store.read(self.discovery.stream("score", project, identifier))
        if not events or version is not None and not 1 <= version <= len(events):
            raise DiscoveryError("Score version not found")
        event = events[-1] if version is None else events[version - 1]
        data = dict(event.data)
        reasons = []
        candidate = self.discovery.opportunity(project, data["opportunity_id"])
        if candidate["version"] != data["opportunity_version"] or candidate["stale_sources"]:
            reasons.append("candidate_or_evidence_revised")
        if data["policy_fingerprint"] != self.policy.fingerprint:
            reasons.append("policy_revised")
        for name in ("effort", "value"):
            rating = data[name]
            if not rating or rating["score"] is None or not rating["rationale"] or not rating["references"]:
                reasons.append(f"{name}_incomplete")
            if rating:
                for ref in rating["references"]:
                    if self.discovery.read("material", project, ref["material_id"])["version"] != ref["version"]:
                        reasons.append(f"{name}_evidence_revised")
        coordinates = None
        if not reasons:
            policy = ScoringPolicy.model_validate(data["policy"])
            coordinates = {}
            for name in ("effort", "value"):
                axis, number = getattr(policy, name), Decimal(data[name]["score"])
                high = number >= axis.split if axis.split_is_high else number > axis.split
                coordinates[name] = {"score": str(number), "side": "high" if high else "low",
                                     "normalized": str((number - axis.minimum) / (axis.maximum - axis.minimum))}
        return {**data, "seq": event.seq, "version": event.seq, "created_at": event.at,
                "status": "ready_for_discussion" if coordinates is not None else "incomplete_or_stale",
                "coordinates": coordinates, "not_plotted_reasons": sorted(set(reasons)), "approval": "not_decided"}
