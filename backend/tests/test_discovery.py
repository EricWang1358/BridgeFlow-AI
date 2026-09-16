"""Discovery keeps source history and never upgrades proposals to business facts."""
import json

import pytest
from pydantic import ValidationError

from bridgeflow.workflow.discovery import Discovery, DiscoveryError, MaterialInput, OpportunityInput
from bridgeflow.workflow.store import ConcurrencyError, WorkflowStore


@pytest.fixture
def domain(tmp_path):
    return Discovery(WorkflowStore(tmp_path / "workflow.sqlite3"), tmp_path / "blobs")


def material(**changes):
    return MaterialInput.model_validate({"id": "source", "project_id": "project", "department": "production",
        "period": "2026-09", "filename": "empty.csv", "declared_kind": "records",
        "source_description": "Uploaded by the department", "expected_seq": 0} | changes)


def opportunity(**changes):
    return OpportunityInput.model_validate({"id": "candidate", "project_id": "project", "title": "A proposal",
        "departments": ["production"], "expected_seq": 0,
        "claims": [{"kind": "problem", "text": "An unconfirmed problem", "basis": "inferred",
                     "references": [{"material_id": "source", "version": 1, "locator": {"kind": "header", "sheet": "csv"}}]}],
        "open_questions": ["Does an actual handoff exist?"]} | changes)


def test_empty_template_is_not_promoted_to_data_and_revisions_survive_restart(domain):
    first = domain.register(material(), b"item,amount\n", "employee")
    assert first["detected_kind"] == "template"
    assert first["declared_kind"] == "records"  # Declaration is retained, not trusted as detection.
    domain.register(material(expected_seq=1), b"item,amount\nsecret-customer,1\n", "employee")
    restored = Discovery(WorkflowStore(domain.store.path), domain.blobs)
    assert restored.read("material", "project", "source", 1)["digest"] == first["digest"]
    latest = restored.read("material", "project", "source")
    assert latest["version"] == 2 and latest["detected_kind"] == "records"
    assert "secret-customer" not in json.dumps(latest)
    assert (domain.blobs / latest["digest"]).read_bytes().endswith(b"secret-customer,1\n")


def test_revision_conflict_does_not_replace_material(domain):
    domain.register(material(), b"a,b\n", "employee")
    with pytest.raises(ConcurrencyError):
        domain.register(material(), b"a,c\n", "employee")
    assert domain.read("material", "project", "source")["version"] == 1


def test_candidate_retains_hypothesis_and_marks_revised_evidence(domain):
    domain.register(material(), b"a,b\n", "employee")
    candidate = domain.propose(opportunity(), "reviewer")
    assert candidate["status"] == "proposed"
    assert candidate["claims"][0]["basis"] == "inferred"
    assert domain.opportunity("project", "candidate")["stale_sources"] == []
    domain.register(material(expected_seq=1), b"a,c\n", "employee")
    view = domain.opportunity("project", "candidate")
    assert view["stale_sources"] == ["source"] and view["approval"] == "not_decided"
    with pytest.raises(DiscoveryError, match="revised"):
        domain.propose(opportunity(expected_seq=1), "reviewer")
    assert domain.opportunity("project", "candidate")["version"] == 1


def test_failed_and_unsupported_material_remain_inventory_only(domain):
    for filename in ["broken.xlsx", "recording.mp3"]:
        saved = domain.register(material(id=filename.replace(".", "_"), filename=filename), b"invalid", "employee")
        assert saved["parser_status"] in {"failed", "unsupported"}
        proposal = opportunity()
        proposal.claims[0].references[0].material_id = saved["id"]
        with pytest.raises(DiscoveryError, match="Unparsed"):
            domain.propose(proposal, "reviewer")
    assert domain.store.streams("discovery:opportunity:") == []


def test_department_scope_and_source_project_cannot_be_changed(domain):
    domain.register(material(), b"a,b\n", "employee")
    with pytest.raises(DiscoveryError, match="Scope is immutable"):
        domain.register(material(expected_seq=1, department="finance"), b"a,b\n", "employee")
    with pytest.raises(DiscoveryError, match="scope"):
        domain.propose(opportunity(departments=["finance"]), "reviewer")
    with pytest.raises(DiscoveryError, match="not found"):
        domain.propose(opportunity(project_id="other"), "reviewer")


def test_text_content_is_retained_only_as_blob_and_claim_requires_reference(domain):
    saved = domain.register(material(filename="meeting.md", declared_kind="meeting"), b"private discussion", "employee")
    assert saved["shape"] == {"characters": 18, "lines": 1}
    assert "private discussion" not in json.dumps(saved)
    with pytest.raises(ValidationError):
        opportunity(claims=[{"kind": "problem", "text": "No evidence", "basis": "inferred", "references": []}])
    with pytest.raises(ValidationError):
        material(project_id="../project")


def test_source_change_between_check_and_commit_is_atomic(domain, monkeypatch):
    domain.register(material(), b"a,b\n", "employee")
    original = domain.store.commit
    def race(pending, *args, **kwargs):
        monkeypatch.setattr(domain.store, "commit", original)
        domain.register(material(expected_seq=1), b"a,c\n", "other-employee")
        return original(pending, *args, **kwargs)
    monkeypatch.setattr(domain.store, "commit", race)
    with pytest.raises(ConcurrencyError):
        domain.propose(opportunity(), "reviewer")
    assert domain.store.streams("discovery:opportunity:") == []


@pytest.mark.parametrize("locator", [
    {"kind": "header", "sheet": "missing"},
    {"kind": "rows", "sheet": "csv", "start": 2, "end": 99},
    {"kind": "lines", "start": 1, "end": 1},
])
def test_candidate_rejects_nonexistent_source_positions(domain, locator):
    domain.register(material(), b"a,b\nx,1\n", "employee")
    data = opportunity().model_dump()
    data["claims"][0]["references"][0]["locator"] = locator
    with pytest.raises(DiscoveryError):
        domain.propose(OpportunityInput.model_validate(data), "reviewer")
    assert domain.store.streams("discovery:opportunity:") == []


def test_physical_row_positions_preserve_blank_rows(domain):
    saved = domain.register(material(), b"a,b\n\nx,1\n", "employee")
    assert saved["shape"]["sheets"][0]["physical_rows"] == 3
    data = opportunity().model_dump()
    data["claims"][0]["references"][0]["locator"] = {
        "kind": "rows", "sheet": "csv", "start": 3, "end": 3}
    assert domain.propose(OpportunityInput.model_validate(data), "reviewer")["version"] == 1


def test_text_references_validate_lines_without_exposing_content(domain):
    domain.register(material(filename="meeting.txt", declared_kind="meeting"), b"private\nsecond line", "employee")
    data = opportunity().model_dump()
    data["claims"][0]["references"][0]["locator"] = {"kind": "lines", "start": 2, "end": 2}
    proposal = domain.propose(OpportunityInput.model_validate(data), "reviewer")
    assert "second line" not in json.dumps(proposal)
    data["expected_seq"] = 1
    data["claims"][0]["references"][0]["locator"]["end"] = 3
    with pytest.raises(DiscoveryError, match="outside"):
        domain.propose(OpportunityInput.model_validate(data), "reviewer")


@pytest.mark.parametrize("locator", [
    {"kind": "rows", "sheet": "csv", "start": 3, "end": 2},
    {"kind": "lines", "start": 0, "end": 1},
    {"kind": "header", "sheet": "csv", "start": 1},
    {"kind": "lines", "sheet": "csv", "start": 1, "end": 1},
])
def test_malformed_locator_is_not_a_reference(locator):
    from bridgeflow.workflow.discovery import Locator
    with pytest.raises(ValidationError):
        Locator.model_validate(locator)
