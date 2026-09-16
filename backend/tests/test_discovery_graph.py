import pytest
from pydantic import ValidationError
from test_discovery import domain as domain  # noqa: PLC0414 -- pytest fixture re-export
from test_discovery import material, opportunity

from bridgeflow.workflow.discovery import DiscoveryError
from bridgeflow.workflow.discovery_graph import DiscoveryGraphs, FlowGraph
from bridgeflow.workflow.store import ConcurrencyError


def graph(**changes):
    ref = {"material_id": "source", "version": 1, "locator": {"kind": "header", "sheet": "csv"}}
    nodes = [{"id": identifier, "title": identifier, "department": "production", "role": "reviewer",
              "trigger": "Person requests review", "references": [ref]} for identifier in ["receive", "review", "parallel"]]
    edges = [{"id": "forward", "source": "receive", "target": "review", "kind": "document",
              "status": "inferred", "rationale": "Needs human confirmation", "references": [ref]},
             {"id": "back", "source": "review", "target": "receive", "kind": "information",
              "status": "missing", "rationale": "Return process is unknown", "rework": True},
             {"id": "branch", "source": "receive", "target": "parallel", "kind": "information",
              "status": "confirmed", "rationale": "Explicit branch", "references": [ref],
              "confirmation": "Owner explicitly described this branch"}]
    return FlowGraph.model_validate({"id": "diagram", "project_id": "project", "opportunity_id": "candidate",
        "opportunity_version": 1, "title": "Draft flow", "departments": ["production"],
        "expected_seq": 0, "nodes": nodes, "edges": edges, **changes})


def prepared(domain):
    domain.register(material(), b"a,b\n", "employee")
    domain.propose(opportunity(), "employee")
    return DiscoveryGraphs(domain)


def test_graph_preserves_branches_rework_and_uncertainty_without_executing(domain):
    graphs = prepared(domain)
    saved = graphs.save(graph(), "reviewer")
    assert saved["version"] == 1 and saved["status"] == "draft"
    assert [edge["status"] for edge in saved["edges"]] == ["inferred", "missing", "confirmed"]
    assert saved["edges"][1]["rework"]
    assert domain.store.streams("handoff:") == []
    assert domain.store.notifications() == []
    assert domain.opportunity("project", "candidate")["approval"] == "not_decided"
    graphs.save(graph(expected_seq=1, title="Updated diagram"), "other-reviewer")
    assert DiscoveryGraphs(domain).read("project", "diagram", 1)["title"] == "Draft flow"


def test_graph_rejects_bad_topology_or_unsupported_confirmation():
    data = graph().model_dump()
    data["edges"][0]["target"] = "absent"
    with pytest.raises(ValidationError):
        FlowGraph.model_validate(data)
    data = graph().model_dump()
    data["edges"][0]["status"] = "confirmed"
    with pytest.raises(ValidationError):
        FlowGraph.model_validate(data)
    data["edges"][0]["status"] = "conflict"
    with pytest.raises(ValidationError):
        FlowGraph.model_validate(data)


def test_graph_exposes_stale_materials_and_refuses_new_stale_revisions(domain):
    graphs = prepared(domain)
    graphs.save(graph(), "employee")
    domain.register(material(expected_seq=1), b"c,d\n", "employee")
    read = graphs.read("project", "diagram")
    assert read["stale_sources"] == ["source"] and read["opportunity_stale"]
    with pytest.raises(DiscoveryError, match="revised"):
        graphs.save(graph(expected_seq=1), "employee")
    assert graphs.read("project", "diagram")["version"] == 1


def test_graph_guards_candidate_revision_during_commit(domain, monkeypatch):
    graphs = prepared(domain)
    commit = domain.store.commit
    def race(pending, *args, **kwargs):
        monkeypatch.setattr(domain.store, "commit", commit)
        domain.propose(opportunity(expected_seq=1, title="changed"), "employee")
        return commit(pending, *args, **kwargs)
    monkeypatch.setattr(domain.store, "commit", race)
    with pytest.raises(ConcurrencyError):
        graphs.save(graph(), "employee")
    assert domain.store.streams("discovery:graph:") == []


def test_graph_scope_and_stale_graph_sequence_are_enforced(domain):
    graphs = prepared(domain)
    graphs.save(graph(), "employee")
    with pytest.raises(ConcurrencyError):
        graphs.save(graph(), "employee")
    with pytest.raises(DiscoveryError, match="scope"):
        graphs.save(graph(expected_seq=1, departments=["production", "finance"]), "employee")
