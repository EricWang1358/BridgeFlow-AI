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
from bridgeflow.config import REPO_ROOT, settings


class Tenant:
    """A fake Feishu: one token endpoint, a drive with files, an upload endpoint."""

    def __init__(self):
        self.files = {f"tok{role}": (f"{role}.csv", (CASES / "risk" / f"{role}.csv").read_bytes()) for role in business.ROLES}
        self.uploaded: dict[str, bytes] = {}
        self.token_calls = 0
        # Wiki side (docs/31): one space, a two-level node tree, and the calls in order.
        self.wiki_spaces = [{"space_id": "spc1", "name": "生产知识库", "description": "d",
                             "secret_cell": "must-not-leak"}]
        self.wiki_nodes = [{"node_token": "wikinode1", "obj_token": "tokproduction", "obj_type": "file",
                            "title": "production.csv", "has_child": False, "secret_cell": "must-not-leak"},
                           {"node_token": "wikidir1", "obj_token": "dirdoc", "obj_type": "docx",
                            "title": "子目录", "has_child": True}]
        self.moves: list[dict] = []
        self.calls: list[str] = []
        self.fail_move = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/tenant_access_token/internal"):
            self.token_calls += 1
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t-1", "expire": 7200})
        if request.headers.get("authorization") not in ("Bearer t-1", "Bearer u-1"):
            return httpx.Response(401, json={"code": 99991663, "msg": "invalid token"})
        self.calls.append(f"{request.method} {path}")
        if path.endswith("/move_docs_to_wiki"):
            if self.fail_move:
                return httpx.Response(200, json={"code": 131006, "msg": "no permission to add nodes"})
            self.moves.append(json.loads(request.content))
            return httpx.Response(200, json={"code": 0, "data": {"node": {"token": "wikinew1"}}})
        if path.endswith("/root_folder/meta"):
            return httpx.Response(200, json={"code": 0, "data": {"token": "rootfld"}})
        if path.endswith("/nodes"):
            return httpx.Response(200, json={"code": 0, "data": {"items": self.wiki_nodes, "has_more": False, "page_token": ""}})
        if path.endswith("/wiki/v2/spaces"):
            return httpx.Response(200, json={"code": 0, "data": {"items": self.wiki_spaces, "has_more": False, "page_token": ""}})
        if path.endswith("/files"):
            files = [{"token": token, "name": name, "type": "file", "size": len(content), "modified_time": "1700000000",
                      "secret_cell": "must-not-leak"} for token, (name, content) in self.files.items()]
            return httpx.Response(200, json={"code": 0, "data": {"files": files, "has_more": False, "next_page_token": ""}})
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
                        lambda: feishu.FeishuDrive("app", "secret", "https://feishu.test", transport=httpx.MockTransport(fake)))
    monkeypatch.setattr(feishu_tools, "user_client_factory",
                        lambda token: feishu.FeishuDrive.for_user(token, "https://feishu.test", transport=httpx.MockTransport(fake)))
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


def test_the_live_check_script_round_trips_against_a_tenant(monkeypatch, capsys):
    import asyncio
    import importlib.util
    import json

    spec = importlib.util.spec_from_file_location("feishu_live_check", REPO_ROOT / "scripts" / "feishu_live_check.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    fake = Tenant()

    class Drive(feishu.FeishuDrive):
        def __init__(self, app_id, secret, base_url):
            super().__init__(app_id, secret, base_url, transport=httpx.MockTransport(fake))

        async def upload(self, folder_token, filename, payload):
            token = await super().upload(folder_token, filename, payload)
            fake.files[token] = (filename, payload)  # the tenant keeps what was sent
            return token

    for name in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_TEST_FOLDER"):
        monkeypatch.delenv(name, raising=False)
    assert asyncio.run(script.main()) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "not_configured"

    monkeypatch.setattr(script.feishu, "FeishuDrive", Drive)
    for name in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_TEST_FOLDER"):
        monkeypatch.setenv(name, "value-" + name.lower())
    assert asyncio.run(script.main()) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "passed" and "value-" not in json.dumps(report)


# --- User-identity endpoints (docs/30): the browser relays the user's own token. -------

USER = {"content-type": "application/json", "x-feishu-user-token": "u-1"}


def test_user_endpoints_require_a_user_token(client, tenant):
    for path in ("/tools/feishu-list", "/tools/feishu-import-user", "/tools/feishu-upload-user"):
        payload = import_payload() if "import" in path else {"batch_id": "a" * 32, "folder_token": "fldcn123456"}
        response = client.post(path, content=json.dumps(payload), headers={"content-type": "application/json"})
        assert response.status_code == 401, path
    assert tenant.token_calls == 0  # a missing user token never falls back to the tenant


def test_listing_returns_metadata_only(client, tenant):
    response = client.post("/tools/feishu-list", content=json.dumps({"folder_token": ""}), headers=USER)
    assert response.status_code == 200, response.text
    body = response.json()
    assert {f["name"] for f in body["files"]} == {f"{r}.csv" for r in business.ROLES}
    assert "secret_cell" not in json.dumps(body)  # metadata only: no cell content, ever
    assert body["has_more"] is False


def test_user_import_needs_no_model_approval_but_sets_owner(client, tenant):
    payload = import_payload(files=[{"department": "production", "file_token": "tokproduction"}])
    response = client.post("/tools/feishu-import-user", content=json.dumps(payload), headers=USER)
    assert response.status_code == 200, response.text
    batch = response.json()["batch"]
    assert batch["master_rows"] > 0
    sources = client.get(f"/batches/{batch['batch_id']}/sources").json()["sources"]
    assert [s["filename"] for s in sources] == ["production.csv"]


def test_user_upload_round_trip(client, tenant):
    batch_id = client.post("/tools/feishu-import-user", content=json.dumps(import_payload()), headers=USER).json()["batch"]["batch_id"]
    context = client.post("/tools/review-context", json={"batch_id": batch_id}).json()
    runs = [{"role": p["role"], "session_id": p["role"], "status": "completed", "judgement": judgement(p)} for p in context["roles"]]
    report = client.post("/tools/review-finalize", json={"batch_id": batch_id, "parent_session_id": "p", "runs": runs}).json()
    response = client.post("/tools/feishu-upload-user", headers=USER,
                           content=json.dumps({"batch_id": batch_id, "folder_token": "fldcn123456", "report_id": report["report_id"]}))
    assert response.status_code == 200, response.text
    assert report["report_id"].encode() in tenant.uploaded["new-file-token"]


# --- Wiki endpoints (docs/31): browse is metadata only; upload lands in Drive, then attaches. ---


def test_wiki_endpoints_require_a_user_token(client, tenant):
    for path, payload in (("/tools/feishu-wiki-spaces", {}),
                          ("/tools/feishu-wiki-list", {"space_id": "spc1"})):
        response = client.post(path, content=json.dumps(payload), headers={"content-type": "application/json"})
        assert response.status_code == 401, path
    upload = client.post("/tools/feishu-wiki-upload", data={"space_id": "spc1"},
                         files={"file": ("a.csv", b"x")})
    assert upload.status_code == 401
    assert tenant.token_calls == 0  # a missing user token never falls back to the tenant


def test_wiki_spaces_and_nodes_are_metadata_only(client, tenant):
    spaces = client.post("/tools/feishu-wiki-spaces", content="{}", headers=USER)
    assert spaces.status_code == 200, spaces.text
    assert spaces.json()["spaces"][0]["space_id"] == "spc1"
    nodes = client.post("/tools/feishu-wiki-list", content=json.dumps({"space_id": "spc1"}), headers=USER)
    assert nodes.status_code == 200, nodes.text
    body = nodes.json()
    assert {n["obj_type"] for n in body["nodes"]} == {"file", "docx"}
    assert body["nodes"][0]["token"] == "wikinode1"
    assert body["nodes"][0]["obj_token"] == "tokproduction"
    assert "secret_cell" not in json.dumps(spaces.json()) + json.dumps(body)  # metadata only, ever


def test_wiki_upload_lands_in_drive_then_attaches(client, tenant):
    response = client.post("/tools/feishu-wiki-upload", data={"space_id": "spc1", "parent_wiki_token": "wikidir1"},
                           files={"file": ("notes.csv", b"a,b\n1,2")}, headers={"x-feishu-user-token": "u-1"})
    assert response.status_code == 200, response.text
    assert response.json() == {"wiki_token": "wikinew1", "name": "notes.csv"}
    paths = [call.split(" ", 1)[1] for call in tenant.calls]
    assert paths.index("/open-apis/drive/v1/files/upload_all") < paths.index(
        "/open-apis/wiki/v2/spaces/spc1/nodes/move_docs_to_wiki")  # land first, attach second
    assert tenant.moves == [{"obj_type": "file", "obj_token": "new-file-token", "parent_wiki_token": "wikidir1"}]


def test_wiki_upload_attach_failure_says_where_the_file_is(client, tenant):
    tenant.fail_move = True
    response = client.post("/tools/feishu-wiki-upload", data={"space_id": "spc1"},
                           files={"file": ("notes.csv", b"a,b\n1,2")}, headers={"x-feishu-user-token": "u-1"})
    assert response.status_code == 502
    assert "My Space root" in response.json()["detail"]  # the leftover is named, never silent


def test_wiki_upload_rejects_oversized_files(client, tenant):
    response = client.post("/tools/feishu-wiki-upload", data={"space_id": "spc1"},
                           files={"file": ("big.csv", b"x" * (feishu.MAX_FILE_BYTES + 1))},
                           headers={"x-feishu-user-token": "u-1"})
    assert response.status_code == 413
    assert tenant.uploaded == {}


def _saved_report(client) -> tuple[str, str]:
    batch_id = client.post("/tools/feishu-import-user", content=json.dumps(import_payload()), headers=USER).json()["batch"]["batch_id"]
    context = client.post("/tools/review-context", json={"batch_id": batch_id}).json()
    runs = [{"role": p["role"], "session_id": p["role"], "status": "completed", "judgement": judgement(p)} for p in context["roles"]]
    report = client.post("/tools/review-finalize", json={"batch_id": batch_id, "parent_session_id": "p", "runs": runs}).json()
    return batch_id, report["report_id"]


def test_user_upload_report_to_wiki(client, tenant):
    batch_id, report_id = _saved_report(client)
    response = client.post("/tools/feishu-upload-user", headers=USER,
                           content=json.dumps({"batch_id": batch_id, "report_id": report_id,
                                               "wiki_space_id": "spc1", "parent_wiki_token": "wikidir1"}))
    assert response.status_code == 200, response.text
    assert response.json()["wiki_token"] == "wikinew1"
    assert report_id.encode() in tenant.uploaded["new-file-token"]
    assert tenant.moves[0]["parent_wiki_token"] == "wikidir1"


def test_user_upload_needs_exactly_one_target(client, tenant):
    batch_id, report_id = _saved_report(client)
    both = {"batch_id": batch_id, "report_id": report_id,
            "folder_token": "fldcn123456", "wiki_space_id": "spc1"}
    neither = {"batch_id": batch_id, "report_id": report_id}
    for payload in (both, neither):
        response = client.post("/tools/feishu-upload-user", headers=USER, content=json.dumps(payload))
        assert response.status_code == 422, payload
