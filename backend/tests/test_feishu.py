"""Feishu Drive shortcuts (#140), tested against a simulated tenant — no real Feishu call."""
import json

import httpx
import pytest
from conftest import receipt
from fastapi.testclient import TestClient
from test_business_mvp import CASES, judgement

from bridgeflow import business, feishu
from bridgeflow.api import feishu_tools
from bridgeflow.api.main import app
from bridgeflow.config import settings


class Tenant:
    """A fake Feishu: one token endpoint, a drive with files, an upload endpoint."""

    def __init__(self):
        self.files = {f"tok{role}": (f"{role}.csv", (CASES / "risk" / f"{role}.csv").read_bytes()) for role in business.ROLES}
        self.uploaded: dict[str, bytes] = {}
        self.token_calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/tenant_access_token/internal"):
            self.token_calls += 1
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t-1", "expire": 7200})
        if request.headers.get("authorization") != "Bearer t-1":
            return httpx.Response(401, json={"code": 99991663, "msg": "invalid token"})
        if path.endswith("/download"):
            token = path.split("/")[-2]
            if token not in self.files:
                return httpx.Response(404, json={"code": 1061004, "msg": "file not found"})
            name, content = self.files[token]
            return httpx.Response(200, content=content, headers={"content-disposition": f'attachment; filename="{name}"'})
        if path.endswith("/upload_all"):
            self.uploaded["new-file-token"] = request.content
            return httpx.Response(200, json={"code": 0, "data": {"file_token": "new-file-token"}})
        return httpx.Response(404, json={"code": 404, "msg": "unknown"})


@pytest.fixture
def tenant(monkeypatch):
    fake = Tenant()
    monkeypatch.setattr(feishu_tools, "client_factory",
                        lambda: feishu.FeishuDrive("app", "secret", "https://feishu.test", httpx.MockTransport(fake)))
    monkeypatch.setattr(settings, "field_dictionary_path", str(CASES / "dictionary.yaml"))
    return fake


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def post(client, path, payload, approve=True):
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"content-type": "application/json"}
    if approve:
        headers["x-bridgeflow-approval"] = receipt(body)
    return client.post(path, content=body, headers=headers)


def import_payload(**change):
    return {"period": "2025-11", "files": [{"department": r, "file_token": f"tok{r}"} for r in business.ROLES],
            "confirmed_by": "captain", "call_id": "c1", **change}


def test_without_credentials_the_shortcuts_say_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "feishu_app_id", "")
    monkeypatch.setattr(settings, "feishu_app_secret", "")
    monkeypatch.setattr(feishu_tools, "client_factory", feishu.from_settings)
    response = post(client, "/tools/feishu-import", import_payload())
    assert response.status_code == 503 and "not configured" in response.json()["detail"]


def test_importing_from_feishu_needs_approval_and_produces_a_normal_batch(client, tenant):
    assert post(client, "/tools/feishu-import", import_payload(), approve=False).status_code == 403
    response = post(client, "/tools/feishu-import", import_payload())
    assert response.status_code == 200, response.text
    batch = response.json()["batch"]
    assert batch["master_rows"] > 0 and {d["department"] for d in batch["departments"]} == set(business.ROLES)
    sources = client.get(f"/batches/{batch['batch_id']}/sources").json()["sources"]
    assert {s["filename"] for s in sources} == {f"{r}.csv" for r in business.ROLES}
    assert tenant.token_calls == 1  # the tenant token is reused within its lifetime


def test_a_feishu_refusal_is_reported_and_nothing_is_imported(client, tenant):
    payload = import_payload(files=[{"department": "production", "file_token": "tokmissing"}])
    response = post(client, "/tools/feishu-import", payload)
    assert response.status_code == 502 and "file not found" in response.json()["detail"]


def test_a_saved_report_is_uploaded_as_saved(client, tenant):
    batch_id = post(client, "/tools/feishu-import", import_payload()).json()["batch"]["batch_id"]
    context = client.post("/tools/review-context", json={"batch_id": batch_id}).json()
    runs = [{"role": p["role"], "session_id": p["role"], "status": "completed", "judgement": judgement(p)} for p in context["roles"]]
    report = client.post("/tools/review-finalize", json={"batch_id": batch_id, "parent_session_id": "p", "runs": runs}).json()
    response = post(client, "/tools/feishu-upload-report", {"batch_id": batch_id, "folder_token": "fldcn123456",
                                                            "report_id": report["report_id"], "confirmed_by": "captain", "call_id": "u1"})
    assert response.status_code == 200, response.text
    assert response.json()["file_token"] == "new-file-token"
    assert report["report_id"].encode() in tenant.uploaded["new-file-token"]
