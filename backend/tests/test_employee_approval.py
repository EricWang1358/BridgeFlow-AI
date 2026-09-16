"""A verified employee permit is necessary but not sufficient for a native write."""
import hashlib
import hmac
import json
import sqlite3
import time
from pathlib import Path

import pytest
import yaml
from conftest import receipt
from test_identity import auth, make_token, workflow_setup
from test_identity import client as client  # noqa: PLC0414 -- pytest fixture re-export
from test_workflow_tools import first_submission

from bridgeflow.config import settings
from bridgeflow.store import _root


def grants(subject, operations):
    path = Path(settings.access_control_path)
    config = yaml.safe_load(path.read_text())
    config["users"][subject]["operations"] = operations
    path.write_text(yaml.safe_dump(config))


def body():
    return json.dumps({"template": "production_record", "said": first_submission(),
                       "confirmed_by": "a-name-the-model-invented", "call_id": "employee-test"},
                      separators=(",", ":"), ensure_ascii=False).encode()


def permit(client, payload, operation="workflow_record", subject="ou_bob"):
    return client.post("/identity/authorize-write", headers=auth(make_token(sub=subject)),
                       json={"operation": operation, "body": payload.decode()})


def native(payload, employee_permit):
    stamp, nonce, _ = receipt(payload).split(".")
    message = f"{stamp}.{nonce}.{hashlib.sha256(payload).hexdigest()}.{employee_permit}"
    signature = hmac.new(settings.bridgeflow_service_token.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{stamp}.{nonce}.{signature}.{employee_permit}"


def execute(client, payload, proof):
    return client.post("/tools/workflow-receive", content=payload,
                       headers={"content-type": "application/json", "x-bridgeflow-approval": proof})


def test_employee_permit_requires_identity_operation_and_data_scope(client, monkeypatch):
    workflow_setup(monkeypatch)
    payload = body()
    assert client.post("/identity/authorize-write", json={"operation": "workflow_record", "body": payload.decode()}).status_code == 401
    assert permit(client, payload).status_code == 403
    grants("ou_bob", ["workflow_record"])
    assert permit(client, payload).status_code == 200
    path = Path(settings.access_control_path)
    config = yaml.safe_load(path.read_text())
    config["users"]["ou_bob"]["workflow_departments"] = []
    path.write_text(yaml.safe_dump(config))
    assert permit(client, payload).status_code == 404


@pytest.mark.parametrize("department", [[], {}, None, ""])
def test_import_permit_rejects_malformed_department(client, department):
    grants("ou_bob", ["feishu_import"])
    payload = json.dumps({"files": [{"department": department}]}).encode()
    assert permit(client, payload, operation="feishu_import").status_code == 422


def test_native_receipt_and_employee_permit_are_both_required_and_consumed_once(client, monkeypatch):
    workflow_setup(monkeypatch)
    grants("ou_bob", ["workflow_record"])
    payload = body()
    employee_permit = permit(client, payload).json()["permit"]
    assert execute(client, payload, employee_permit).status_code == 403
    assert execute(client, payload, receipt(payload)).status_code == 403
    proof = native(payload, employee_permit)
    assert execute(client, payload, proof).status_code == 200
    assert execute(client, payload, proof).status_code == 403
    # A newly signed native receipt cannot reuse the employee permit either.
    assert execute(client, payload, native(payload, employee_permit)).status_code == 403
    with sqlite3.connect(_root() / "approval-receipts.sqlite3") as connection:
        rows = connection.execute("SELECT subject, operation, call_id FROM employee_authorizations").fetchall()
    assert rows == [("ou_bob", "workflow_record", "employee-test")]


def test_employee_authorization_binds_exact_body_and_operation(client, monkeypatch):
    workflow_setup(monkeypatch)
    grants("ou_bob", ["workflow_record", "workflow_approve_submit"])
    payload = body()
    employee_permit = permit(client, payload).json()["permit"]
    changed = payload.replace(b'employee-test', b'other-call')
    assert execute(client, changed, native(changed, employee_permit)).status_code == 403
    # Even a host signature on altered content cannot make the employee's permit match.
    assert execute(client, payload, native(payload, "0" * 64)).status_code == 403
    from fastapi import HTTPException

    from bridgeflow.security import consume_approval
    with pytest.raises(HTTPException) as failure:
        consume_approval(native(payload, employee_permit), payload, "workflow_approve_submit")
    assert failure.value.status_code == 403


def test_expired_or_revoked_employee_authorization_refuses_execution(client, monkeypatch):
    workflow_setup(monkeypatch)
    grants("ou_bob", ["workflow_record"])
    payload = body()
    employee_permit = permit(client, payload).json()["permit"]
    grants("ou_bob", [])
    assert execute(client, payload, native(payload, employee_permit)).status_code == 403
    grants("ou_bob", ["workflow_record"])
    with sqlite3.connect(_root() / "approval-receipts.sqlite3") as connection:
        connection.execute("UPDATE employee_permits SET expires = ?", (time.time() - 1,))
    assert execute(client, payload, native(payload, employee_permit)).status_code == 403


def test_employee_identity_is_saved_as_the_actual_workflow_reviewer(client, monkeypatch):
    _, artifact_id = workflow_setup(monkeypatch)
    from test_workflow_foundation import actual_answer

    from bridgeflow.api.workflow import service

    domain = service()
    draft = domain.artifact(artifact_id)
    draft = domain.answer(artifact_id, actual_answer("96 方"), draft.seq)
    grants("ou_bob", ["workflow_approve_submit"])
    payload = json.dumps({"artifact_id": artifact_id, "digest": draft.draft.digest,
                          "expected_seq": draft.seq, "confirmed_by": "not-the-employee"}, separators=(",", ":")).encode()
    employee_permit = permit(client, payload, "workflow_approve_submit").json()["permit"]
    result = client.post("/tools/workflow-approve-submit", content=payload,
                        headers={"content-type": "application/json", "x-bridgeflow-approval": native(payload, employee_permit)})
    assert result.status_code == 200, result.text
    reviews = [e for e in domain.store.read(f"artifact:{artifact_id}") if e.type == "reviewed"]
    assert reviews[-1].data["by"] == "ou_bob"
