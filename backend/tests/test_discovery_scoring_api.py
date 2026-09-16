import json

from test_discovery import material, opportunity
from test_discovery_api import grant
from test_discovery_scoring import policy, score
from test_employee_approval import grants, native, permit
from test_identity import auth, make_token
from test_identity import client as client  # noqa: PLC0414 -- pytest fixture re-export

from bridgeflow.api.discovery import service
from bridgeflow.config import settings


def prepare(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", True)
    file = tmp_path / "scoring.yaml"
    file.write_text(policy().model_dump_json())
    monkeypatch.setattr(settings, "discovery_scoring_policy_path", str(file))
    grant()
    grants("ou_alice", ["discovery_score_save"])
    domain = service()
    domain.register(material(), b"a,b\n", "employee")
    domain.propose(opportunity(), "employee")
    return file


def write(client, payload, token):
    return client.post("/tools/discovery-score-save", content=payload,
                      headers={"content-type": "application/json", "x-bridgeflow-approval": native(payload, token)})


def test_scoring_policy_and_reads_require_department_scope(client, monkeypatch, tmp_path):
    prepare(monkeypatch, tmp_path)
    path = "/discovery/project/scoring-policy"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=auth(make_token(sub="ou_bob"))).status_code == 404
    response = client.get(path, headers=auth(make_token()))
    assert response.status_code == 200 and response.json()["fingerprint"] == policy().fingerprint
    payload = json.dumps({"score": score().model_dump(mode="json")}).encode()
    assert client.post("/tools/discovery-score-save", json=json.loads(payload)).status_code == 403
    token = permit(client, payload, "discovery_score_save", "ou_alice").json()["permit"]
    saved = write(client, payload, token)
    assert saved.status_code == 200
    assert saved.json()["actor"] == "ou_alice" and saved.json()["approval"] == "not_decided"
    assert saved.json()["coordinates"]["effort"]["side"] == "high"
    assert client.get("/discovery/project/score", headers=auth(make_token(sub="ou_bob"))).json()["total"] == 0
    assert client.get("/discovery/project/score/rating", headers=auth(make_token(sub="ou_bob"))).status_code == 404
    listed = client.get("/discovery/project/score", headers=auth(make_token())).json()
    assert listed["items"][0]["coordinates"] == saved.json()["coordinates"]


def test_policy_changes_between_authorization_and_execution_refuse_write(client, monkeypatch, tmp_path):
    file = prepare(monkeypatch, tmp_path)
    payload = json.dumps({"score": score().model_dump(mode="json")}).encode()
    token = permit(client, payload, "discovery_score_save", "ou_alice").json()["permit"]
    file.write_text(policy().model_copy(update={"version": 2}).model_dump_json())
    assert write(client, payload, token).status_code == 409
    assert service().store.streams("discovery:score:") == []
    file.unlink()
    assert client.get("/discovery/project/scoring-policy", headers=auth(make_token())).status_code == 503


def test_incomplete_rating_has_no_coordinates_and_revocation_prevents_revision(client, monkeypatch, tmp_path):
    prepare(monkeypatch, tmp_path)
    payload = json.dumps({"score": score(value=None).model_dump(mode="json")}).encode()
    token = permit(client, payload, "discovery_score_save", "ou_alice").json()["permit"]
    assert write(client, payload, token).json()["coordinates"] is None
    payload = json.dumps({"score": score(expected_seq=1).model_dump(mode="json")}).encode()
    token = permit(client, payload, "discovery_score_save", "ou_alice").json()["permit"]
    grants("ou_alice", [])
    assert write(client, payload, token).status_code == 403
    assert service().read("score", "project", "rating")["version"] == 1
