import json
import sqlite3
from pathlib import Path

import yaml
from test_discovery import material
from test_employee_approval import grants, native, permit
from test_identity import auth, make_token
from test_identity import client as client  # noqa: PLC0414 -- pytest fixture re-export

from bridgeflow.api.discovery import service, uploads
from bridgeflow.config import settings


def setup(monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", True)
    path = Path(settings.access_control_path)
    acl = yaml.safe_load(path.read_text())
    acl["users"]["ou_alice"]["workflow_departments"] = ["production"]
    acl["users"]["ou_alice"]["operations"] = ["discovery_upload", "discovery_register"]
    path.write_text(yaml.safe_dump(acl))


def upload(client, item=None):
    item = item or material()
    return client.post("/discovery/uploads", headers=auth(make_token()),
        data={"metadata": item.model_dump_json()}, files={"file": (item.filename, b"a,b\n")})


def body(staged):
    return json.dumps({key: staged[key] for key in ("upload_id", "digest", "material")}).encode()


def approve(client, payload):
    allowed = permit(client, payload, "discovery_register", "ou_alice")
    assert allowed.status_code == 200, allowed.text
    return client.post("/tools/discovery-register", content=payload,
        headers={"content-type": "application/json", "x-bridgeflow-approval": native(payload, allowed.json()["permit"])})


def test_upload_is_not_registration_and_approved_version_is_employee_attributed(client, monkeypatch):
    setup(monkeypatch)
    response = upload(client)
    assert response.status_code == 200
    staged = response.json()
    assert staged["status"] == "awaiting_registration"
    assert service().store.streams("discovery:material:") == []
    assert client.post("/tools/discovery-register", json=json.loads(body(staged))).status_code == 403
    registered = approve(client, body(staged))
    assert registered.status_code == 200
    assert registered.json()["actor"] == "ou_alice"
    assert registered.json()["detected_kind"] == "template"
    assert registered.json()["version"] == 1
    assert permit(client, body(staged), "discovery_register", "ou_alice").status_code == 404


def test_registration_rejects_changed_metadata_digest_and_expiry(client, monkeypatch):
    setup(monkeypatch)
    staged = upload(client).json()
    changed = dict(staged, digest="0" * 64)
    assert permit(client, body(changed), "discovery_register", "ou_alice").status_code == 404
    changed = dict(staged, material={**staged["material"], "source_description": "Different source"})
    assert permit(client, body(changed), "discovery_register", "ou_alice").status_code == 404
    with sqlite3.connect(uploads().path) as connection:
        connection.execute("UPDATE uploads SET expires = 0")
    assert permit(client, body(staged), "discovery_register", "ou_alice").status_code == 404
    assert service().store.streams("discovery:material:") == []


def test_upload_scope_operation_and_deployment_switch(client, monkeypatch):
    setup(monkeypatch)
    assert upload(client, material(department="finance")).status_code == 403
    grants("ou_alice", ["discovery_register"])
    assert upload(client).status_code == 403
    grants("ou_alice", ["discovery_upload"])
    assert upload(client).status_code == 200
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", False)
    assert upload(client).status_code == 403


def test_separate_uploads_cannot_overwrite_same_version(client, monkeypatch):
    setup(monkeypatch)
    first, second = upload(client).json(), upload(client).json()
    assert approve(client, body(first)).status_code == 200
    assert approve(client, body(second)).status_code == 409
    assert service().read("material", "project", "source")["version"] == 1
    revised = upload(client, material(expected_seq=1)).json()
    assert approve(client, body(revised)).json()["version"] == 2


def test_upload_quota_returns_recoverable_error_without_registration(client, monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(settings, "discovery_upload_owner_count", 1)
    assert upload(client).status_code == 200
    refused = upload(client)
    assert refused.status_code == 429
    assert "quota" in refused.json()["detail"]
    assert service().store.streams("discovery:material:") == []
