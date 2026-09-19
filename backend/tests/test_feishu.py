"""Feishu Drive shortcuts (#140), tested against a simulated tenant — no real Feishu call."""
import copy
import csv as csvlib
import io
import json
import re

import httpx
import pytest
import yaml
from conftest import receipt
from fastapi.testclient import TestClient
from test_access_resolver import ROLES, SPACES
from test_business_mvp import CASES, judgement

from bridgeflow import business, feishu, store
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
        # Sheet & bitable side (docs/33): the production CSV served two ways — as a sheet
        # with a title row above the header, and as a bitable table with complex fields.
        production_rows = list(csvlib.reader(io.StringIO((CASES / "risk" / "production.csv").read_text())))
        self.sheet_rows = {"shtok1": [["月度生产总表"]] + production_rows}
        self.sheet_meta = {"shtok1": [{"sheet_id": "s1sheet", "title": "生产数据",
                                       "grid_properties": {"row_count": 6, "column_count": 6},
                                       "secret_cell": "must-not-leak"}]}
        self.flaky_values = False
        self.values_calls = 0
        header = production_rows[0]
        self.bitable_tables = {"bitok1": [{"table_id": "tbl1main", "name": "生产台账",
                                           "secret_cell": "must-not-leak"}]}
        self.bitable_fields = [{"field_name": h, "type": 1, "ui_type": "Text"} for h in header] + [
            {"field_name": "负责人", "type": 11, "ui_type": "User"},
            {"field_name": "凭证", "type": 17, "ui_type": "Attachment"},
            {"field_name": "校验", "type": 20, "ui_type": "Formula"},
            {"field_name": "关联原料", "type": 21, "ui_type": "Link"}]
        self.bitable_records = [
            {"record_id": f"rec{i}", "fields": {**dict(zip(header, row)),
                                                "负责人": [{"name": "张三"}],
                                                "凭证": [{"name": "发票.pdf"}],
                                                "校验": 42,
                                                "关联原料": {"record_ids": ["rec9"], "table_id": "tbl2"}}}
            for i, row in enumerate(production_rows[1:])]

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
        parts = path.split("/")
        if path.endswith("/sheets/query"):  # /open-apis/sheets/v3/spreadsheets/{token}/sheets/query
            if parts[5] == "denied1":
                return httpx.Response(403, json={"code": 99991679, "msg": "forbidden"})
            return httpx.Response(200, json={"code": 0, "data": {"sheets": self.sheet_meta.get(parts[5], [])}})
        if "/values/" in path:  # /open-apis/sheets/v2/spreadsheets/{token}/values/{sheet!A1:C6}
            self.values_calls += 1
            if self.flaky_values and self.values_calls == 1:
                return httpx.Response(429, json={"code": 99991400, "msg": "frequency limit"})
            bounds = re.search(r"!A(\d+):[A-Z]+(\d+)", parts[7])
            rows = self.sheet_rows.get(parts[5], [])[int(bounds.group(1)) - 1:int(bounds.group(2))]
            return httpx.Response(200, json={"code": 0, "data": {"valueRange": {"values": rows}}})
        if "/bitable/v1/apps/" in path:  # /open-apis/bitable/v1/apps/{token}/tables[/{id}/fields|records]
            if path.endswith("/tables"):
                return httpx.Response(200, json={"code": 0, "data": {"items": self.bitable_tables.get(parts[5], [])}})
            if path.endswith("/fields"):
                return httpx.Response(200, json={"code": 0, "data": {"items": self.bitable_fields, "has_more": False}})
            if path.endswith("/records"):
                page = 1 if request.url.params.get("page_token") else 0
                items = self.bitable_records[page * 2:page * 2 + 2]
                has_more = (page + 1) * 2 < len(self.bitable_records)
                return httpx.Response(200, json={"code": 0, "data": {
                    "items": items, "has_more": has_more, "page_token": "p2" if has_more else ""}})
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
def acl(monkeypatch, tmp_path):
    """A declared space -> department mapping whose production space is the fake tenant's spc1."""
    spaces = copy.deepcopy(SPACES)
    spaces["departments"]["production"]["space_id"] = "spc1"
    path = tmp_path / "access-control.yaml"
    path.write_text(yaml.safe_dump({"spaces": spaces, "roles": ROLES}), encoding="utf-8")
    monkeypatch.setattr(settings, "access_control_path", str(path))
    return path


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


def test_wiki_spaces_and_nodes_are_metadata_only(client, tenant, acl):
    tenant.wiki_spaces.append({"space_id": "spc-personal", "name": "我的文档库", "description": "personal"})
    spaces = client.post("/tools/feishu-wiki-spaces", content="{}", headers=USER)
    assert spaces.status_code == 200, spaces.text
    assert spaces.json()["spaces"][0]["space_id"] == "spc1"
    assert spaces.json()["spaces"][0]["department"] == "production"  # the declared mapping, annotated server-side
    assert spaces.json()["spaces"][1]["department"] is None  # unmapped spaces stay manual in the browser
    nodes = client.post("/tools/feishu-wiki-list", content=json.dumps({"space_id": "spc1"}), headers=USER)
    assert nodes.status_code == 200, nodes.text
    body = nodes.json()
    assert {n["obj_type"] for n in body["nodes"]} == {"file", "docx"}
    assert body["nodes"][0]["token"] == "wikinode1"
    assert body["nodes"][0]["obj_token"] == "tokproduction"
    assert "secret_cell" not in json.dumps(spaces.json()) + json.dumps(body)  # metadata only, ever


def test_wiki_spaces_fail_closed_without_a_structure_file(client, tenant, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "access_control_path", str(tmp_path / "missing.yaml"))
    response = client.post("/tools/feishu-wiki-spaces", content="{}", headers=USER)
    assert response.status_code == 503 and "not configured" in response.json()["detail"]


def test_a_wiki_import_contradicting_the_declared_mapping_is_rejected(client, tenant, acl):
    payload = import_payload(files=[{"department": "finance", "file_token": "tokproduction",
                                     "wiki_space_id": "spc1"}])
    response = client.post("/tools/feishu-import-user", content=json.dumps(payload), headers=USER)
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert "production" in detail and "finance" in detail


def test_a_wiki_import_matching_or_outside_the_mapping_imports(client, tenant, acl):
    matching = import_payload(files=[{"department": "production", "file_token": "tokproduction",
                                      "wiki_space_id": "spc1"}])
    assert client.post("/tools/feishu-import-user", content=json.dumps(matching), headers=USER).status_code == 200
    # Unmapped spaces keep the hand-picked department: spc1 is production's, spc-personal declares none.
    unmapped = import_payload(files=[{"department": "finance", "file_token": "tokfinance",
                                      "wiki_space_id": "spc-personal"}])
    assert client.post("/tools/feishu-import-user", content=json.dumps(unmapped), headers=USER).status_code == 200


def test_the_tenant_path_ignores_the_wiki_space_hint(client, tenant, acl):
    payload = import_payload(files=[{"department": "finance", "file_token": "tokproduction",
                                     "wiki_space_id": "spc1"}])
    response = post(client, "/tools/feishu-import", payload)
    assert response.status_code == 200, response.text


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


# --- Sheet & bitable reads (docs/33): metadata is metadata; reads import as batches. ----


def sheet_import_payload(**change):
    return {"period": "2025-11", "files": [{"department": "production", "file_token": "shtok1",
                                            "kind": "sheet", "sheet_id": "s1sheet", "header_row": 2}],
            **change}


def test_sheet_and_bitable_meta_require_a_user_token(client, tenant):
    for path, payload in (("/tools/feishu-sheet-meta", {"token": "shtok1"}),
                          ("/tools/feishu-bitable-meta", {"token": "bitok1"})):
        response = client.post(path, content=json.dumps(payload), headers={"content-type": "application/json"})
        assert response.status_code == 401, path
    assert tenant.token_calls == 0  # a missing user token never falls back to the tenant


def test_sheet_meta_is_metadata_only(client, tenant):
    response = client.post("/tools/feishu-sheet-meta", content=json.dumps({"token": "shtok1"}), headers=USER)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sheets"] == [{"sheet_id": "s1sheet", "title": "生产数据", "rows": 6, "cols": 6}]
    assert "must-not-leak" not in json.dumps(body)  # metadata only: no cell content, ever


def test_bitable_meta_lists_tables_then_fields(client, tenant):
    tables = client.post("/tools/feishu-bitable-meta", content=json.dumps({"token": "bitok1"}), headers=USER)
    assert tables.status_code == 200, tables.text
    assert tables.json() == {"tables": [{"table_id": "tbl1main", "name": "生产台账"}]}
    fields = client.post("/tools/feishu-bitable-meta", headers=USER,
                         content=json.dumps({"token": "bitok1", "table_id": "tbl1main"}))
    body = fields.json()
    assert {f["name"] for f in body["fields"]} >= {"sku", "负责人", "关联原料"}
    assert all(set(f) == {"name", "ui_type"} for f in body["fields"])  # definitions, never record content
    assert "must-not-leak" not in json.dumps(tables.json()) + json.dumps(body)


def test_meta_refusal_is_passed_through(client, tenant):
    response = client.post("/tools/feishu-sheet-meta", content=json.dumps({"token": "denied1"}), headers=USER)
    # A user-side authorization refusal (Feishu 403) stays a 403 (docs/32 FR-7);
    # 502 is reserved for backend/upstream failures.
    assert response.status_code == 403
    assert "99991679" in response.json()["detail"]


def test_sheet_import_uses_the_chosen_header_row(client, tenant):
    response = client.post("/tools/feishu-import-user", content=json.dumps(sheet_import_payload()), headers=USER)
    assert response.status_code == 200, response.text
    batch = response.json()["batch"]
    assert batch["master_rows"] > 0
    assert batch["departments"][0]["rows"] == 4  # title row skipped, header at row 2
    sources = client.get(f"/batches/{batch['batch_id']}/sources").json()["sources"]
    assert sources[0]["filename"] == "feishu-sheet-shtok1-生产数据.csv"
    assert "SKU-A1" not in json.dumps(response.json())  # cell content never crosses into a response


def test_sheet_import_retries_frequency_control_once(client, tenant):
    tenant.flaky_values = True
    response = client.post("/tools/feishu-import-user", content=json.dumps(sheet_import_payload()), headers=USER)
    assert response.status_code == 200, response.text
    assert tenant.values_calls == 2  # one 429, then the retried read


def test_bitable_import_flattens_complex_fields(client, tenant):
    payload = {"period": "2025-11", "files": [{"department": "production", "file_token": "bitok1",
                                               "kind": "bitable", "table_id": "tbl1main"}]}
    response = client.post("/tools/feishu-import-user", content=json.dumps(payload), headers=USER)
    assert response.status_code == 200, response.text
    batch = response.json()["batch"]
    assert batch["departments"][0]["rows"] == 4
    assert batch["master_rows"] > 0
    # FR-5: the link column has no display text, so it is dropped with a reason, not silently.
    assert batch["dropped_columns"] == [{"department": "production", "column": "关联原料",
                                         "field_type": "Link",
                                         "reason": "no representable value; column dropped"}]
    stored = json.loads((store._root() / "batches" / "sources" / batch["batch_id"] / "production.json")
                        .read_text(encoding="utf-8"))
    assert "张三" in json.dumps(stored, ensure_ascii=False)  # person field imports as its display name
    assert "发票.pdf" in json.dumps(stored, ensure_ascii=False)  # attachment as its file name
    assert "rec9" not in json.dumps(stored, ensure_ascii=False)  # link record ids never imported
    assert "张三" not in json.dumps(response.json(), ensure_ascii=False)  # and never in a response


def test_oversized_sheet_is_refused_with_counts(client, tenant, monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_max_batch_rows", 3)
    before = set((store._root() / "batches").glob("*.json"))
    response = client.post("/tools/feishu-import-user", content=json.dumps(sheet_import_payload()), headers=USER)
    assert response.status_code == 413
    detail = response.json()["detail"]
    assert "3-row import limit" in detail and "nothing was imported" in detail
    assert set((store._root() / "batches").glob("*.json")) == before  # no partial batch persisted


def test_kind_declares_its_addressing_exactly(client, tenant):
    bad = [
        {"department": "production", "file_token": "shtok1", "kind": "sheet"},  # no sheet_id, no header_row
        {"department": "production", "file_token": "shtok1", "kind": "sheet", "sheet_id": "s1sheet"},  # no header_row
        {"department": "production", "file_token": "bitok1", "kind": "bitable"},  # no table_id
        {"department": "production", "file_token": "bitok1", "kind": "bitable", "table_id": "tbl1main", "header_row": 1},
        {"department": "production", "file_token": "tokproduction", "kind": "file", "sheet_id": "s1sheet"},
    ]
    for item in bad:
        response = client.post("/tools/feishu-import-user", headers=USER,
                               content=json.dumps({"period": "2025-11", "files": [item]}))
        assert response.status_code == 422, item


def test_tenant_endpoint_refuses_sheets_and_bitables(client, tenant):
    response = post(client, "/tools/feishu-import",
                    sheet_import_payload(confirmed_by="captain", call_id="c1"))
    assert response.status_code == 422
    assert "user endpoint" in response.json()["detail"]
