"""Discovery → workflow: accepting an approved MVP decision as the workflow's scope.

The HANDOFF rule for this seam: a decision read once is never a standing licence. Every
test here is about that — acceptance checks the decision as it stands, and the scope goes
stale (and new records stop) when the decision changes underneath.
"""
import json

import pytest
import yaml
from conftest import receipt
from fastapi.testclient import TestClient

from bridgeflow.api.discovery import service as discovery_service
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.workflow.discovery_decisions import (
    DecisionProposal,
    DiscoveryDecisions,
    load_decision_policy,
)

DEMO = REPO_ROOT / "data/discovery_demo"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "workflow_catalogue_path", str(REPO_ROOT / "data/workflow_demo/catalogue.yaml"))
    monkeypatch.setattr(settings, "discovery_scoring_policy_path", str(DEMO / "scoring-policy.yaml"))
    monkeypatch.setattr(settings, "discovery_decision_policy_path", str(DEMO / "decision-policy.yaml"))
    return TestClient(app)


def accept(client, seq, decision="mvp"):
    body = json.dumps({"project_id": "demo-handoff", "decision_id": decision, "decision_seq": seq},
                      separators=(",", ":")).encode()
    return client.post("/tools/workflow-accept-scope", content=body,
                       headers={"content-type": "application/json", "x-bridgeflow-approval": receipt(body)})


def test_without_a_decision_policy_there_is_nothing_to_accept(client, monkeypatch):
    monkeypatch.setattr(settings, "discovery_decision_policy_path", "")
    state = client.get("/workflow/scope").json()
    assert state["accepted"] is None and state["pending"] == []


def test_the_sample_decision_is_offered_accepted_and_current(client):
    decision = client.post("/discovery/sample")
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "approved"
    offered = client.get("/workflow/scope").json()["pending"]
    assert [(p["decision_id"], p["candidates"]) for p in offered] == [("mvp", ["production_to_marketing_handoff"])]
    accepted = accept(client, offered[0]["decision_seq"])
    assert accepted.status_code == 200, accepted.text
    state = client.get("/workflow/scope").json()
    assert state["current"] is True and state["accepted"]["scope"] == decision.json()["agent2_handoff"]["scope"]
    assert client.post("/workflow/sample").status_code == 200  # records run under a current scope


def test_acceptance_needs_the_version_the_person_was_shown(client):
    seq = client.post("/discovery/sample").json()["seq"]
    stale = accept(client, seq - 1)
    assert stale.status_code == 409 and "read it again" in stale.json()["detail"]


def test_a_revised_decision_makes_the_scope_stale_and_stops_new_records(client):
    decision = client.post("/discovery/sample").json()
    assert accept(client, decision["seq"]).status_code == 200
    policy = load_decision_policy(str(DEMO / "decision-policy.yaml"))
    DiscoveryDecisions(discovery_service(), policy).propose(DecisionProposal.model_validate({
        "id": "mvp", "project_id": "demo-handoff", "meeting_id": "kickoff", "meeting_version": 1,
        "selected_candidates": ["production_to_marketing_handoff"], "scope": ["A narrower pilot"],
        "exclusions": [], "rationale": "Revised after the pilot review", "expected_seq": decision["seq"],
        "policy_fingerprint": policy.fingerprint}), "示例-立项负责人")
    state = client.get("/workflow/scope").json()
    assert state["current"] is False and state["stale_reasons"] == ["decision_proposed"]
    refused = client.post("/workflow/sample")
    assert refused.status_code == 409 and "accept the current decision" in refused.json()["detail"]


def test_a_decision_for_a_scenario_the_catalogue_cannot_run_is_refused(client, monkeypatch, tmp_path):
    raw = yaml.safe_load((REPO_ROOT / "data/workflow_demo/catalogue.yaml").read_text(encoding="utf-8"))
    raw["mvp"]["candidates"] = ["some_other_scenario"]
    raw["mvp"]["selected"] = "some_other_scenario"
    path = tmp_path / "catalogue.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(settings, "workflow_catalogue_path", str(path))
    seq = client.post("/discovery/sample").json()["seq"]
    refused = accept(client, seq)
    assert refused.status_code == 409 and "not scenarios this workflow catalogue declares" in refused.json()["detail"]


def test_accepting_needs_a_fresh_approval(client):
    seq = client.post("/discovery/sample").json()["seq"]
    body = json.dumps({"project_id": "demo-handoff", "decision_id": "mvp", "decision_seq": seq}).encode()
    unapproved = client.post("/tools/workflow-accept-scope", content=body, headers={"content-type": "application/json"})
    assert unapproved.status_code == 403


def test_the_sample_score_lands_on_the_quadrant_chart(client):
    client.post("/discovery/sample")
    [score] = client.get("/discovery/demo-handoff/score?offset=0&limit=50").json()["items"]
    assert score["coordinates"] is not None and score["not_plotted_reasons"] == []
    policy = client.get("/discovery/demo-handoff/scoring-policy").json()
    assert score["policy_fingerprint"] == policy["fingerprint"]


def test_the_sample_project_carries_its_flow_graph_with_every_edge_state(client):
    client.post("/discovery/sample")
    graph = client.get("/discovery/demo-handoff/graph/current-flow").json()
    assert {e["kind"] for e in graph["edges"]} == {"information", "document"}
    assert {e["status"] for e in graph["edges"]} >= {"confirmed", "inferred", "missing"}
    assert all(e["confirmation"] for e in graph["edges"] if e["status"] == "confirmed")
    again = client.post("/discovery/sample")  # idempotent: nothing duplicated, still approved
    assert again.status_code == 200 and client.get("/discovery/demo-handoff/graph").json()["total"] == 1
