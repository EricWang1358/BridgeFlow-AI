from decimal import Decimal

import pytest
from pydantic import ValidationError
from test_discovery import domain as domain  # noqa: PLC0414 -- pytest fixture re-export
from test_discovery import material, opportunity

from bridgeflow.workflow.discovery import DiscoveryError
from bridgeflow.workflow.discovery_scoring import (
    DiscoveryScores,
    ScoreDraft,
    ScoringPolicy,
    load_policy,
)
from bridgeflow.workflow.store import ConcurrencyError


def policy():
    axis = {"title": "Declared axis", "unit": "points", "minimum": 0, "maximum": 10, "split": 5,
            "split_is_high": True, "low_meaning": "Low", "high_meaning": "High"}
    return ScoringPolicy.model_validate({"id": "workshop", "project_id": "project", "version": 1,
        "departments": ["production"], "declared_by": "business-owner", "declaration_ref": "Synthetic test declaration, not production policy",
        "effort": axis, "value": {**axis, "split_is_high": False}})


def score(**changes):
    rating = {"score": 5, "rationale": "Explicit estimate, not measured savings", "references": [
        {"material_id": "source", "version": 1, "locator": {"kind": "header", "sheet": "csv"}}]}
    return ScoreDraft.model_validate({"id": "rating", "project_id": "project", "opportunity_id": "candidate",
        "opportunity_version": 1, "policy_fingerprint": policy().fingerprint, "expected_seq": 0,
        "effort": rating, "value": rating, **changes})


def prepared(domain):
    domain.register(material(), b"a,b\n", "employee")
    domain.propose(opportunity(), "employee")
    return DiscoveryScores(domain, policy())


def test_declared_boundary_ties_and_exact_decimal_coordinates(domain):
    scores = prepared(domain)
    saved = scores.save(score(), "verified-reviewer")
    assert saved["coordinates"]["effort"] == {"score": "5", "side": "high", "normalized": "0.5"}
    assert saved["coordinates"]["value"]["side"] == "low"
    assert saved["actor"] == "verified-reviewer" and saved["approval"] == "not_decided"
    assert domain.opportunity("project", "candidate")["approval"] == "not_decided"


@pytest.mark.parametrize("missing", [None, {"score": 3}, {"score": 3, "rationale": "No source"}])
def test_incomplete_ratings_persist_without_plotting(domain, missing):
    saved = prepared(domain).save(score(value=missing), "reviewer")
    assert saved["coordinates"] is None
    assert "value_incomplete" in saved["not_plotted_reasons"]


def test_bounds_nonfinite_scales_and_missing_policy_are_refused(domain, tmp_path):
    scores = prepared(domain)
    invalid = score().model_copy(deep=True)
    invalid.effort.score = Decimal(11)
    with pytest.raises(DiscoveryError, match="outside"):
        scores.save(invalid, "reviewer")
    assert domain.store.streams("discovery:score:") == []
    with pytest.raises(ValidationError):
        score(value={"score": "NaN"})
    data = policy().model_dump()
    data["effort"]["split"] = 10
    with pytest.raises(ValidationError):
        ScoringPolicy.model_validate(data)
    with pytest.raises(DiscoveryError):
        load_policy(tmp_path / "missing.yaml")


def test_policy_and_candidate_revisions_withhold_coordinates_preserving_history(domain):
    scores = prepared(domain)
    scores.save(score(), "reviewer")
    changed = policy().model_copy(update={"version": 2})
    current = DiscoveryScores(domain, changed)
    assert current.read("project", "rating")["coordinates"] is None
    assert "policy_revised" in current.read("project", "rating")["not_plotted_reasons"]
    with pytest.raises(DiscoveryError, match="policy changed"):
        current.save(score(expected_seq=1), "reviewer")
    domain.propose(opportunity(expected_seq=1, title="Changed scope hypothesis"), "reviewer")
    assert scores.read("project", "rating")["coordinates"] is None
    assert scores.read("project", "rating")["policy"]["version"] == 1


def test_scoring_concurrency_guards_source_revision(domain, monkeypatch):
    scores = prepared(domain)
    commit = domain.store.commit
    def race(pending, *args, **kwargs):
        monkeypatch.setattr(domain.store, "commit", commit)
        domain.register(material(expected_seq=1), b"x,y\n", "other")
        return commit(pending, *args, **kwargs)
    monkeypatch.setattr(domain.store, "commit", race)
    with pytest.raises(ConcurrencyError):
        scores.save(score(), "reviewer")
    assert domain.store.streams("discovery:score:") == []
