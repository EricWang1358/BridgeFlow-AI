import json

from test_discovery import material, opportunity
from test_discovery_graph import graph
from test_employee_approval import grants, native, permit
from test_identity import auth, make_token
from test_identity import client as client  # noqa: PLC0414 -- pytest fixture re-export

from bridgeflow.api.discovery import service
from bridgeflow.config import settings
from bridgeflow.workflow.discovery_graph import DiscoveryGraphs


def prepare(monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", True)
    grants("ou_alice", ["discovery_graph_save"])
    domain = service()
    domain.register(material(), b"a,b\n", "employee")
    domain.propose(opportunity(), "employee")
    return domain


def save(client, payload):
    allowed = permit(client, payload, "discovery_graph_save", "ou_alice")
    assert allowed.status_code == 200, allowed.text
    return client.post("/tools/discovery-graph-save", content=payload, headers={
        "content-type": "application/json", "x-bridgeflow-approval": native(payload, allowed.json()["permit"])})


def test_graph_native_write_and_scoped_historical_reads(client, monkeypatch):
    domain = prepare(monkeypatch)
    payload = json.dumps({"graph": graph().model_dump(), "call_id": "graph-test"}).encode()
    assert client.post("/tools/discovery-graph-save", json=json.loads(payload)).status_code == 403
    result = save(client, payload)
    assert result.status_code == 200 and result.json()["actor"] == "ou_alice"
    assert result.json()["status"] == "draft"
    assert "nodes" not in result.json()
    base = "/discovery/project/graph"
    assert client.get(base).status_code == 401
    assert client.get(base, headers=auth(make_token(sub="ou_bob"))).json()["total"] == 1  # any signed-in employee
    assert client.get(base + "/diagram", headers=auth(make_token(sub="ou_bob"))).status_code == 200
    assert client.get(base, headers=auth(make_token())).json()["total"] == 1
    detail = client.get(base + "/diagram?version=1", headers=auth(make_token()))
    assert detail.status_code == 200 and len(detail.json()["edges"]) == 3
    domain.register(material(expected_seq=1), b"c,d\n", "employee")
    assert client.get(base + "/diagram", headers=auth(make_token())).json()["stale_sources"] == ["source"]


def test_graph_write_rejects_missing_sources_and_revoked_permission(client, monkeypatch):
    domain = prepare(monkeypatch)
    value = graph().model_dump()
    value["nodes"][0]["references"][0]["material_id"] = "never-registered"
    payload = json.dumps({"graph": value}).encode()
    assert permit(client, payload, "discovery_graph_save", "ou_alice").status_code == 404
    payload = json.dumps({"graph": graph().model_dump()}).encode()
    token = permit(client, payload, "discovery_graph_save", "ou_alice").json()["permit"]
    grants("ou_alice", [])
    result = client.post("/tools/discovery-graph-save", content=payload, headers={
        "content-type": "application/json", "x-bridgeflow-approval": native(payload, token)})
    assert result.status_code == 403
    assert domain.store.streams("discovery:graph:") == []


def test_graph_edit_conflict_preserves_existing_draft(client, monkeypatch):
    domain = prepare(monkeypatch)
    payload = json.dumps({"graph": graph().model_dump()}).encode()
    assert save(client, payload).status_code == 200
    assert save(client, payload).status_code == 409
    assert DiscoveryGraphs(domain).read("project", "diagram")["version"] == 1
