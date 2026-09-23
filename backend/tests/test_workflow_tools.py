"""Workflow tools as a DSH agent calls them: approval-bound writes, bounded reads."""
import json

import pytest
import yaml
from conftest import receipt
from fastapi.testclient import TestClient

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

DEMO = REPO_ROOT / "data/workflow_demo/catalogue.yaml"
FIELDS = yaml.safe_load(DEMO.read_text(encoding="utf-8"))["templates"]["production_record"]["fields"]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "workflow_catalogue_path", str(DEMO))
    with TestClient(app) as client:
        yield client


def post(client, path, payload, approve=True):
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    headers = {"content-type": "application/json"}
    if approve:
        headers["x-bridgeflow-approval"] = receipt(body)
    return client.post(path, content=body, headers=headers)


def said(*pairs):
    return [{"label": label, "value": value, "evidence": evidence} for label, value, evidence in pairs]


def first_submission():
    keys = ["report_month", "plant", "year", "date", "customer", "project", "product", "output_qty", "shipped_qty"]
    values = ["2026-09", "演示厂站", "2026", "2026-09-01", "演示客户", "演示项目A", "演示货品", "100 方", "98 方"]
    return said(*[(FIELDS[k]["label"], v, "") for k, v in zip(keys, values, strict=True)])


def start(client):
    response = post(client, "/tools/workflow-receive",
                    {"template": "production_record", "said": first_submission(), "confirmed_by": "captain", "call_id": "c1"})
    assert response.status_code == 200, response.text
    return response.json()


def test_recording_what_someone_said_needs_approval(client):
    payload = {"template": "production_record", "said": first_submission(), "confirmed_by": "captain", "call_id": "c1"}
    assert post(client, "/tools/workflow-receive", payload, approve=False).status_code == 403
    assert client.post("/tools/workflow-board").json()["total"] == 0


def test_the_draft_asks_its_question_and_records_the_conversation_as_the_source(client):
    draft = start(client)
    assert draft["state"] == "needs_input"
    [question] = draft["open_questions"]
    assert question["field"] == FIELDS["actual_qty"]["label"] and question["question"] == FIELDS["actual_qty"]["question"]
    full = client.get(f"/workflow/artifacts/{draft['artifact_id']}").json()
    assert {v["source"]["kind"] for v in full["values"].values()} == {"reply"}
    assert {v["source"]["ref"] for v in full["values"].values()} == {"dsh-call:c1"}


def test_answer_then_approve_submit_makes_data_ready(client):
    draft = start(client)
    answer = {"artifact_id": draft["artifact_id"], "expected_seq": draft["seq"],
              "said": said((FIELDS["actual_qty"]["label"], "97.5 方", "DEMO-CONFIRM-001")),
              "confirmed_by": "captain", "call_id": "c2"}
    draft = post(client, "/tools/workflow-answer", answer).json()
    assert draft["state"] == "ready_for_review" and draft["open_questions"] == []
    assert any(c["attention"] for c in draft["checks"])

    stale = {"artifact_id": draft["artifact_id"], "digest": "0" * 64, "expected_seq": draft["seq"],
             "confirmed_by": "captain", "call_id": "c3"}
    assert post(client, "/tools/workflow-approve-submit", stale).status_code == 409

    approve = {**stale, "digest": draft["digest"], "call_id": "c4"}
    done = post(client, "/tools/workflow-approve-submit", approve)
    assert done.status_code == 200, done.text
    assert done.json()["state"] == "data_ready" and done.json()["receipt"]["record_id"]
    summaries = [r["summary"] for r in client.post("/tools/workflow-board").json()["rows"]]
    assert any("待市场部处理" in s for s in summaries)


def test_an_unfinished_draft_cannot_be_approved(client):
    draft = start(client)
    approve = {"artifact_id": draft["artifact_id"], "digest": draft["digest"], "expected_seq": draft["seq"],
               "confirmed_by": "captain", "call_id": "c5"}
    assert post(client, "/tools/workflow-approve-submit", approve).status_code == 409


def test_deployment_policy_can_switch_workflow_writes_off(client, monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", False)
    payload = {"template": "production_record", "said": first_submission(), "confirmed_by": "captain", "call_id": "c1"}
    assert post(client, "/tools/workflow-receive", payload).status_code == 403
    assert client.post("/tools/workflow-catalogue").status_code == 200


def submitted_handoff(client):
    draft = start(client)
    draft = post(client, "/tools/workflow-answer", {
        "artifact_id": draft["artifact_id"], "expected_seq": draft["seq"],
        "said": said((FIELDS["actual_qty"]["label"], "97.5 方", "DEMO-CONFIRM-001")),
    }).json()
    result = post(client, "/tools/workflow-approve-submit", {
        "artifact_id": draft["artifact_id"], "expected_seq": draft["seq"], "digest": draft["digest"],
    })
    assert result.status_code == 200, result.text
    return next(r for r in client.post("/tools/workflow-board").json()["rows"] if r["kind"] == "handoff")


def record_settlement(client):
    """The marketing stage's own output for the same project and month, through the same tools."""
    out = yaml.safe_load((REPO_ROOT / "data/workflow_demo/catalogue.yaml").read_text(encoding="utf-8"))["templates"]["settlement_basis"]["fields"]
    draft = post(client, "/tools/workflow-receive", {"template": "settlement_basis", "confirmed_by": "captain", "call_id": "s1",
        "said": said((out["project"]["label"], "演示项目A", ""), (out["period"]["label"], "2026-09", ""),
                     (out["settled_qty"]["label"], "97.5 方", "DEMO-SETTLE-001"))}).json()
    result = post(client, "/tools/workflow-approve-submit", {
        "artifact_id": draft["artifact_id"], "expected_seq": draft["seq"], "digest": draft["digest"]})
    assert result.status_code == 200, result.text


def test_downstream_tool_requires_approval_and_fresh_sequence(client):
    handoff = submitted_handoff(client)
    body = {"handoff_id": handoff["id"], "expected_seq": handoff["seq"], "action": "start"}
    assert "inputs" in handoff and handoff["stale"] is False
    assert post(client, "/tools/workflow-handoff", body, approve=False).status_code == 403
    assert post(client, "/tools/workflow-handoff", {**body, "action": "complete"}).status_code == 409
    started = post(client, "/tools/workflow-handoff", body)
    assert started.status_code == 200, started.text
    assert started.json()["state"] == "in_progress"
    assert post(client, "/tools/workflow-handoff", body).status_code == 409
    early = post(client, "/tools/workflow-handoff", {**body, "expected_seq": started.json()["seq"], "action": "complete"})
    assert early.status_code == 409 and "not recorded" in early.json()["detail"]  # its own output is still owed
    record_settlement(client)
    completed = post(client, "/tools/workflow-handoff", {
        **body, "expected_seq": started.json()["seq"], "action": "complete"})
    assert completed.status_code == 200 and completed.json()["state"] == "completed"


def test_downstream_return_requires_reason_and_respects_write_policy(client, monkeypatch):
    handoff = submitted_handoff(client)
    body = {"handoff_id": handoff["id"], "expected_seq": handoff["seq"], "action": "return"}
    assert post(client, "/tools/workflow-handoff", body).status_code == 409
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", False)
    assert post(client, "/tools/workflow-handoff", {**body, "reason": "Check source"}).status_code == 403
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", True)
    returned = post(client, "/tools/workflow-handoff", {**body, "reason": "Check source"})
    assert returned.status_code == 200 and returned.json()["state"] == "returned"


def test_guidance_uses_declared_role_and_honestly_reports_unconfigured_contact(client, monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", False)
    result = client.post("/tools/workflow-guidance", json={"stage": "market_review"})
    assert result.status_code == 200
    guide = result.json()
    stages = client.post("/tools/workflow-catalogue").json()["stages"]
    stage = next(s for s in stages if s["stage"] == "market_review")
    assert guide["owner_role"] == stage["owner_role"]
    assert guide["destination"] == {"kind": "local_sqlite", "scope": "local_demo"}
    assert guide["help"]["contact"] is None
    assert guide["inputs_total"] == len(stage["inputs"])
    assert "submission receipt" in guide["success_evidence"]
    assert client.post("/tools/workflow-guidance", json={"stage": "invented"}).status_code == 404
    assert client.post("/tools/workflow-board").json()["total"] == 0
