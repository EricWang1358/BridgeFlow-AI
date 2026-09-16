import json

from test_discovery import material, opportunity
from test_discovery_api import grant
from test_discovery_meetings import REF, meeting
from test_employee_approval import grants, native, permit
from test_identity import auth, make_token
from test_identity import client as client  # noqa: PLC0414 -- pytest fixture re-export

from bridgeflow.api.discovery import service
from bridgeflow.config import settings


def prepare(monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", True)
    grant()
    grants("ou_alice", ["discovery_meeting_save"])
    domain = service()
    domain.register(material(), b"a,b\n", "employee")
    domain.propose(opportunity(), "employee")
    return domain


def body(**changes):
    return json.dumps({"meeting": meeting(**changes).model_dump(mode="json")}).encode()


def save(client, payload, token):
    return client.post("/tools/discovery-meeting-save", content=payload,
                       headers={"content-type": "application/json", "x-bridgeflow-approval": native(payload, token)})


def test_meeting_native_save_and_scoped_history(client, monkeypatch):
    domain = prepare(monkeypatch)
    payload = body()
    assert client.post("/tools/discovery-meeting-save", json=json.loads(payload)).status_code == 403
    token = permit(client, payload, "discovery_meeting_save", "ou_alice").json()["permit"]
    saved = save(client, payload, token)
    assert saved.status_code == 200
    assert saved.json()["actor"] == "ou_alice" and saved.json()["approval"] == "not_decided"
    assert "candidate_snapshots" not in saved.json() and "scope" not in saved.json()
    path = "/discovery/project/meeting"
    assert client.get(path).status_code == 401
    bob = auth(make_token(sub="ou_bob"))
    assert client.get(path, headers=bob).json()["total"] == 0
    assert client.get(path + "/workshop", headers=bob).status_code == 404
    alice = auth(make_token())
    summary = client.get(path, headers=alice).json()["items"][0]
    assert summary["phase"] == "preparation" and "candidate_snapshots" not in summary
    payload = body(expected_seq=1, title="Revised agenda", change_reason="Clarify scope")
    token = permit(client, payload, "discovery_meeting_save", "ou_alice").json()["permit"]
    assert save(client, payload, token).status_code == 200
    old = client.get(path + "/workshop?version=1", headers=alice).json()
    assert old["title"] == "Pilot discussion" and old["actor"] == "ou_alice"
    assert client.get(path + "/workshop", headers=alice).json()["title"] == "Revised agenda"
    domain.propose(opportunity(expected_seq=1, title="Candidate changed"), "employee")
    summary = client.get(path, headers=alice).json()["items"][0]
    assert summary["status"] == "needs_review" and summary["stale_candidates"] == ["candidate"]


def test_meeting_approval_checks_all_sources_and_operation_grants(client, monkeypatch):
    domain = prepare(monkeypatch)
    domain.register(material(id="secret", department="finance"), b"a,b\n", "employee")
    payload = body(risks=[{"text": "Unauthorized reference", "basis": "reported",
                         "references": [{**REF, "material_id": "secret"}]}])
    assert permit(client, payload, "discovery_meeting_save", "ou_alice").status_code == 404
    grants("ou_alice", [])
    assert permit(client, body(), "discovery_meeting_save", "ou_alice").status_code == 403
    assert domain.store.streams("discovery:meeting:") == []


def test_meeting_revocation_after_approval_and_stale_sequence_do_not_write(client, monkeypatch):
    domain = prepare(monkeypatch)
    payload = body()
    token = permit(client, payload, "discovery_meeting_save", "ou_alice").json()["permit"]
    grants("ou_alice", [])
    assert save(client, payload, token).status_code == 403
    assert domain.store.streams("discovery:meeting:") == []
    grants("ou_alice", ["discovery_meeting_save"])
    for expected in (200, 409):
        token = permit(client, payload, "discovery_meeting_save", "ou_alice").json()["permit"]
        assert save(client, payload, token).status_code == expected
    assert domain.read("meeting", "project", "workshop")["version"] == 1


def test_meeting_source_change_between_approval_and_execution_preserves_history(client, monkeypatch):
    domain = prepare(monkeypatch)
    payload = body()
    token = permit(client, payload, "discovery_meeting_save", "ou_alice").json()["permit"]
    domain.register(material(expected_seq=1), b"c,d\n", "employee")
    assert save(client, payload, token).status_code == 422
    assert domain.store.streams("discovery:meeting:") == []
