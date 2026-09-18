import json

from test_discovery_api import grant
from test_discovery_decisions import policy, prepared, proposal
from test_discovery_meetings import REF
from test_employee_approval import grants, native, permit
from test_identity import auth, edit_role, make_token
from test_identity import client as client  # noqa: PLC0414 -- pytest fixture re-export

from bridgeflow.api.discovery import DECISION_OPERATIONS, service
from bridgeflow.config import settings


def setup(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", True)
    grant()
    edit_role("ou_bob", "workflow_departments", ["production"])
    for sub in ("ou_alice", "ou_bob"):
        grants(sub, list(DECISION_OPERATIONS))
    rules = policy(proposers=["ou_alice"], voters=["ou_alice", "ou_bob"],
                   approvers=["ou_alice"], condition_confirmers=["ou_alice"])
    path = tmp_path / "decision-policy.json"
    path.write_text(rules.model_dump_json())
    monkeypatch.setattr(settings, "discovery_decision_policy_path", str(path))
    prepared(service(), rules)
    draft = proposal(policy_fingerprint=rules.fingerprint,
                     conditions=[{"id": "check", "description": "Check source", "confirmer": "ou_alice"}])
    return path, {"proposal": draft.model_dump(mode="json")}


def payload(data):
    return json.dumps(data).encode()


def post(client, action, data, actor="ou_alice"):
    body = payload(data)
    operation = "discovery_decision_" + action
    response = permit(client, body, operation, actor)
    assert response.status_code == 200, response.text
    return client.post("/tools/discovery-decision-" + action, content=body,
                       headers={"content-type": "application/json",
                                "x-bridgeflow-approval": native(body, response.json()["permit"])})


def act(seq, **extra):
    return {"project_id": "project", "id": "mvp", "expected_seq": seq,
            "proposal_version": 1, "rationale": "Synthetic explicit action", **extra}


def test_native_decision_lifecycle_and_scoped_handoff(client, monkeypatch, tmp_path):
    _, draft = setup(monkeypatch, tmp_path)
    assert client.post("/tools/discovery-decision-propose", json=draft).status_code == 403
    assert post(client, "propose", draft).status_code == 200
    assert post(client, "vote", act(1, choice="yes")).status_code == 200
    assert post(client, "vote", act(2, choice="yes"), "ou_bob").status_code == 200
    conditional = post(client, "finalize", act(3, outcome="approve"))
    assert conditional.status_code == 200 and conditional.json()["status"] == "conditional"
    path = "/discovery/project/decision/mvp"
    alice = auth(make_token())
    assert client.get(path, headers=alice).json()["agent2_handoff"] is None
    assert post(client, "resolve", act(4, condition_id="check", references=[REF])).status_code == 200
    final = post(client, "finalize", act(5, outcome="approve"))
    assert final.status_code == 200 and final.json()["last_actor"] == "ou_alice"
    assert "meeting_snapshot" not in final.json() and "agent2_handoff" not in final.json()
    view = client.get(path, headers=alice).json()
    assert view["agent2_handoff"]["decision_seq"] == 6
    assert set(view["votes"]) == {"ou_alice", "ou_bob"}
    assert client.get(path + "?version=4", headers=alice).json()["agent2_handoff"] is None
    assert client.get(path, headers=auth(make_token(sub="outsider"))).status_code == 404
    assert client.get("/discovery/project/decision", headers=auth(make_token(sub="outsider"))).json()["total"] == 0
    summary = client.get("/discovery/project/decision", headers=alice).json()["items"][0]
    assert summary["status"] == "approved" and "votes" not in summary


def test_role_policy_is_additional_to_operation_acl_and_identity_cannot_be_supplied(client, monkeypatch, tmp_path):
    _, draft = setup(monkeypatch, tmp_path)
    assert permit(client, payload(draft), "discovery_decision_propose", "ou_bob").status_code == 403
    assert post(client, "propose", draft).status_code == 200
    assert permit(client, payload(act(1, outcome="approve")), "discovery_decision_finalize", "ou_bob").status_code == 403
    assert permit(client, payload(act(1, choice="yes", actor="ou_bob")), "discovery_decision_vote", "ou_alice").status_code == 422


def test_policy_changes_or_acl_revocation_after_permit_deny_execution(client, monkeypatch, tmp_path):
    path, draft = setup(monkeypatch, tmp_path)
    body = payload(draft)
    token = permit(client, body, "discovery_decision_propose", "ou_alice").json()["permit"]
    rules = json.loads(path.read_text())
    path.write_text(json.dumps({**rules, "version": 2}))
    result = client.post("/tools/discovery-decision-propose", content=body,
        headers={"content-type": "application/json", "x-bridgeflow-approval": native(body, token)})
    assert result.status_code == 409
    assert service().store.streams("discovery:decision:") == []
    path.write_text(json.dumps(rules))
    token = permit(client, body, "discovery_decision_propose", "ou_alice").json()["permit"]
    grants("ou_alice", [])
    result = client.post("/tools/discovery-decision-propose", content=body,
        headers={"content-type": "application/json", "x-bridgeflow-approval": native(body, token)})
    assert result.status_code == 403
    assert service().store.streams("discovery:decision:") == []


def test_missing_policy_and_wrong_project_do_not_default_to_votes(client, monkeypatch, tmp_path):
    path, _ = setup(monkeypatch, tmp_path)
    headers = auth(make_token())
    assert client.get("/discovery/other/decision-policy", headers=headers).status_code == 404
    assert client.get("/discovery/project/decision-policy", headers=headers).json()["quorum"] == 2
    path.unlink()
    assert client.get("/discovery/project/decision-policy", headers=headers).status_code == 503
