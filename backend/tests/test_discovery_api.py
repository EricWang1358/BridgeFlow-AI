
from test_discovery import material, opportunity
from test_identity import auth, edit_role, make_token
from test_identity import client as client  # noqa: PLC0414 -- pytest fixture re-export

from bridgeflow.api.discovery import service
from bridgeflow.config import settings


def grant():
    edit_role("ou_alice", "workflow_departments", ["production"])


def test_inventory_filters_before_counting_and_pagination(client):
    grant()
    domain = service()
    for i, department in enumerate(["finance", "production", "production"]):
        domain.register(material(id=f"m{i}", department=department), b"a,b\n", "employee")
    route = "/discovery/project/material"
    assert client.get(route).status_code == 401
    response = client.get(route + "?limit=1", headers=auth(make_token()))
    assert response.status_code == 200
    assert response.json()["total"] == 2 and response.json()["has_more"]
    assert response.json()["items"][0]["id"] == "m1"
    page = client.get(route + "?limit=1&offset=1", headers=auth(make_token())).json()
    assert page["items"][0]["id"] == "m2" and not page["has_more"]
    assert client.get(route, headers=auth(make_token(sub="ou_bob"))).json()["total"] == 0
    assert client.get(route + "/m0", headers=auth(make_token())).status_code == 404
    assert client.get(route + "?limit=51", headers=auth(make_token())).status_code == 422


def test_detail_retains_authorized_history_and_stale_references(client):
    grant()
    domain = service()
    domain.register(material(), b"a,b\n", "employee")
    domain.propose(opportunity(), "employee")
    domain.register(material(expected_seq=1), b"c,d\n", "employee")
    headers = auth(make_token())
    view = client.get("/discovery/project/opportunity/candidate", headers=headers)
    assert view.status_code == 200 and view.json()["stale_sources"] == ["source"]
    old = client.get("/discovery/project/material/source?version=1", headers=headers)
    assert old.json()["version"] == 1
    assert client.get("/discovery/project/material/source?version=9", headers=headers).status_code == 404
    assert client.get("/discovery/project/opportunity/candidate", headers=auth(make_token(sub="ou_bob"))).status_code == 404


def test_project_prefix_is_literal_not_a_sql_pattern(client):
    grant()
    domain = service()
    domain.register(material(project_id="a_b"), b"a,b\n", "employee")
    domain.register(material(project_id="axb", id="elsewhere"), b"a,b\n", "employee")
    domain.register(material(project_id="A_b", id="uppercase"), b"a,b\n", "employee")
    result = client.get("/discovery/a_b/material", headers=auth(make_token()))
    assert result.status_code == 200
    assert result.json()["total"] == 1
    assert result.json()["items"][0]["project_id"] == "a_b"


def test_proposal_write_requires_employee_and_native_approval(client, monkeypatch):
    import json

    from test_employee_approval import grants, native, permit

    grant()
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", True)
    domain = service()
    domain.register(material(), b"a,b\n", "employee")
    payload = json.dumps({"proposal": opportunity().model_dump(), "call_id": "proposal-test"}).encode()
    route = "/tools/discovery-propose"
    assert client.post(route, content=payload, headers={"content-type": "application/json"}).status_code == 403
    assert permit(client, payload, "discovery_propose", "ou_alice").status_code == 403
    grants("ou_alice", ["discovery_propose"])
    authorized = permit(client, payload, "discovery_propose", "ou_alice")
    assert authorized.status_code == 200
    proof = native(payload, authorized.json()["permit"])
    result = client.post(route, content=payload, headers={"content-type": "application/json", "x-bridgeflow-approval": proof})
    assert result.status_code == 200
    assert result.json()["actor"] == "ou_alice"
    assert result.json()["status"] == "proposed"
    assert domain.opportunity("project", "candidate")["approval"] == "not_decided"
    assert client.post(route, content=payload, headers={"content-type": "application/json", "x-bridgeflow-approval": proof}).status_code == 403


def test_proposal_cannot_hide_unauthorized_sources_or_execute_after_revocation(client, monkeypatch):
    import json

    from test_employee_approval import grants, native, permit

    grant()
    grants("ou_alice", ["discovery_propose"])
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", True)
    domain = service()
    domain.register(material(department="finance"), b"a,b\n", "employee")
    payload = json.dumps({"proposal": opportunity().model_dump(), "call_id": "proposal-test"}).encode()
    assert permit(client, payload, "discovery_propose", "ou_alice").status_code == 404
    domain.register(material(id="allowed"), b"a,b\n", "employee")
    proposed = opportunity().model_dump()
    proposed["claims"][0]["references"][0]["material_id"] = "allowed"
    payload = json.dumps({"proposal": proposed, "call_id": "proposal-test"}).encode()
    token = permit(client, payload, "discovery_propose", "ou_alice").json()["permit"]
    grants("ou_alice", [])
    result = client.post("/tools/discovery-propose", content=payload,
        headers={"content-type": "application/json", "x-bridgeflow-approval": native(payload, token)})
    assert result.status_code == 403
    assert domain.store.streams("discovery:opportunity:") == []


def test_model_material_catalogue_is_bounded_and_excludes_source_content(client):
    import json

    domain = service()
    secret = "private-customer-and-meeting-text"
    for i in range(12):
        domain.register(material(id=f"source{i}"), f"{secret},amount\n{secret},1\n".encode(), "employee")
    domain.register(material(id="meeting", filename="meeting.txt", declared_kind="meeting"),
                    secret.encode(), "employee")
    response = client.post("/tools/discovery-materials", json={"project_id": "project", "limit": 10})
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 13 and result["has_more"]
    assert len(result["items"]) == 10
    assert secret not in json.dumps(result)
    assert result["items"][0]["sheets"][0] == {
        "name": "csv", "header_row": 1, "physical_rows": 2, "data_rows": 1}
    last = client.post("/tools/discovery-materials", json={"project_id": "project", "offset": 10}).json()
    assert not last["has_more"] and last["items"][-1]["text_lines"] == 1
    assert secret not in json.dumps(last)
    assert client.post("/tools/discovery-materials", json={"project_id": "project", "limit": 11}).status_code == 422
    assert client.post("/tools/discovery-materials", json={"project_id": "../project"}).status_code == 422
    # This is a trusted-host endpoint, not a public employee browser route.
    assert client.post("/tools/discovery-materials", json={"project_id": "project"},
                       headers={"authorization": "Bearer invalid"}).status_code == 401


def test_model_sheet_truncation_reports_actual_sheet_count(client):
    import io

    from openpyxl import Workbook

    book = Workbook()
    for i in range(8):
        sheet = book.active if i == 0 else book.create_sheet()
        sheet.title = f"sheet{i}"
        sheet.append(["a", "b"])
    payload = io.BytesIO()
    book.save(payload)
    service().register(material(filename="many.xlsx"), payload.getvalue(), "employee")
    result = client.post("/tools/discovery-materials", json={"project_id": "project"}).json()["items"][0]
    assert result["sheet_count"] == 8
    assert result["sheets_truncated"] and len(result["sheets"]) == 5
    remaining = client.post("/tools/discovery-materials", json={
        "project_id": "project", "material_id": "source", "sheet_offset": 5}).json()["items"][0]
    assert len(remaining["sheets"]) == 3 and remaining["sheets"][0]["name"] == "sheet5"
    assert not remaining["sheets_has_more"] and not remaining["inspection_truncated"]


def test_original_download_checks_scope_version_and_integrity(client):
    import base64

    grant()
    domain = service()
    first = domain.register(material(), b"a,b\n", "employee")
    domain.register(material(expected_seq=1), b"c,d\n", "employee")
    route = "/discovery/project/material/source/original?version=1"
    assert client.get(route).status_code == 401
    assert client.get(route, headers=auth(make_token(sub="ou_bob"))).status_code == 404
    original = client.get(route, headers=auth(make_token()))
    assert original.status_code == 200
    assert original.json()["version"] == 1
    assert base64.b64decode(original.json()["base64"]) == b"a,b\n"
    (domain.blobs / first["digest"]).write_bytes(b"corrupted")
    assert client.get(route, headers=auth(make_token())).status_code == 409
    (domain.blobs / first["digest"]).unlink()
    assert client.get(route, headers=auth(make_token())).status_code == 503
