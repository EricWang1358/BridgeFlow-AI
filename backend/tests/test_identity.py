"""Portal identity and department-scoped batch visibility (docs/27).

Offline: JWKS comes from a stub, tokens are signed with a throwaway test key.
"""
import json
import time
from pathlib import Path

import jwt
import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from bridgeflow import business, identity
from bridgeflow.api.batches import load_batch
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

CASES = REPO_ROOT / "data/business_demo"
PRIVATE = Ed25519PrivateKey.generate()
OTHER_PRIVATE = Ed25519PrivateKey.generate()
JWK = json.loads(jwt.algorithms.OKPAlgorithm.to_jwk(PRIVATE.public_key())) | {
    "kid": "k1", "use": "sig", "alg": "EdDSA"}


def make_token(sub="ou_alice", key=PRIVATE, kid="k1", **claims):
    now = int(time.time())
    payload = {"iss": "http://portal.test", "aud": "bridgeflow", "iat": now, "exp": now + 900,
               "sub": sub, "name": "测试", "email": "t@example.com", **claims}
    return jwt.encode(payload, key, algorithm="EdDSA", headers={"kid": kid})


def auth(token: str) -> dict:
    return {"x-bridgeflow-user": token}


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Identity layer ON: portal settings plus a two-user access-control file."""
    monkeypatch.setattr(settings, "field_dictionary_path", str(CASES / "dictionary.yaml"))
    monkeypatch.setattr(settings, "portal_base_url", "http://portal.test")
    monkeypatch.setattr(settings, "portal_audience", "bridgeflow")
    acl = tmp_path / "access-control.yaml"
    acl.write_text(yaml.safe_dump({"users": {
        "ou_alice": {"name": "Alice", "departments": list(business.ROLES), "operations": ["batch_import"]},
        "ou_bob": {"name": "Bob", "departments": ["production"], "operations": ["batch_import"]},
    }}), encoding="utf-8")
    monkeypatch.setattr(settings, "access_control_path", str(acl))

    async def fake_jwks(url):
        return [JWK]

    identity.reset_cache()
    monkeypatch.setattr(identity, "_fetch_jwks", fake_jwks)
    with TestClient(app) as client:
        yield client
    identity.reset_cache()


def upload(client, headers=None):
    files = [("files", (f"{role}.csv", (CASES / "risk" / f"{role}.csv").read_bytes(), "text/csv"))
             for role in business.ROLES]
    response = client.post("/batches", data={"period": "2025-11", "departments": list(business.ROLES), "operations": ["batch_import"]},
                           files=files, headers=headers or {})
    assert response.status_code == 200, response.text
    return response.json()["batch_id"]


def test_identity_off_behaves_exactly_as_before(monkeypatch):
    monkeypatch.setattr(settings, "field_dictionary_path", str(CASES / "dictionary.yaml"))
    with TestClient(app) as plain:
        batch_id = upload(plain)  # no token anywhere
        assert plain.get(f"/batches/{batch_id}").status_code == 200
        assert load_batch(batch_id).owner == ""


def test_browser_routes_need_a_token_once_the_layer_is_on(client):
    batch_id = upload(client, auth(make_token()))
    assert client.get(f"/batches/{batch_id}").status_code == 401
    assert client.get(f"/batches/{batch_id}/view").status_code == 401
    assert client.get(f"/batches/{batch_id}/sources").status_code == 401


def test_a_forged_or_misaddressed_token_is_refused(client):
    batch_id = upload(client, auth(make_token()))
    assert client.get(f"/batches/{batch_id}", headers=auth(make_token(key=OTHER_PRIVATE))).status_code == 401
    assert client.get(f"/batches/{batch_id}", headers=auth(make_token(aud="other-app"))).status_code == 401
    assert client.get(f"/batches/{batch_id}", headers=auth(make_token(kid="k-rotated"))).status_code == 401
    assert client.get(f"/batches/{batch_id}", headers=auth(make_token(sub=""))).status_code == 401


def test_the_importer_sees_their_own_batch(client):
    batch_id = upload(client, auth(make_token()))
    assert load_batch(batch_id).owner == "ou_alice"
    assert client.get(f"/batches/{batch_id}", headers=auth(make_token())).status_code == 200


def test_an_under_authorized_colleague_cannot_even_learn_the_batch_exists(client):
    batch_id = upload(client, auth(make_token()))
    bob = auth(make_token(sub="ou_bob"))  # production only; the batch spans four departments
    assert client.get(f"/batches/{batch_id}", headers=bob).status_code == 404
    assert client.get(f"/batches/{batch_id}/view", headers=bob).status_code == 404
    assert client.get(f"/batches/{batch_id}/sources/production", headers=bob).status_code == 404
    assert client.get(f"/batches/{batch_id}/artifacts", headers=bob).status_code == 404


def test_an_unlisted_user_sees_nothing(client):
    batch_id = upload(client, auth(make_token()))
    assert client.get(f"/batches/{batch_id}", headers=auth(make_token(sub="ou_carol"))).status_code == 404


def test_upload_is_limited_to_departments_you_may_see(client):
    files = [("files", ("finance.csv", (CASES / "risk" / "finance.csv").read_bytes(), "text/csv"))]
    response = client.post("/batches", data={"period": "2025-11", "departments": ["finance"]},
                           files=files, headers=auth(make_token(sub="ou_bob")))
    assert response.status_code == 403 and "finance" in response.json()["detail"]
    assert client.post("/batches/demo", headers=auth(make_token(sub="ou_bob"))).status_code == 403


def test_a_missing_access_control_file_fails_loudly(client, monkeypatch, tmp_path):
    batch_id = upload(client, auth(make_token()))
    monkeypatch.setattr(settings, "access_control_path", str(tmp_path / "missing.yaml"))
    # The owner is unaffected; anyone else's visibility question gets "not configured".
    assert client.get(f"/batches/{batch_id}", headers=auth(make_token())).status_code == 200
    response = client.get(f"/batches/{batch_id}", headers=auth(make_token(sub="ou_carol")))
    assert response.status_code == 503 and "not configured" in response.json()["detail"]


@pytest.mark.parametrize("suffix", ["", "/xlsx"])
def test_integration_views_enforce_identity_before_loading_business_content(client, suffix):
    batch_id = upload(client, auth(make_token()))
    path = f"/integration/batches/{batch_id}{suffix}"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=auth(make_token(key=OTHER_PRIVATE))).status_code == 401
    assert client.get(path, headers=auth(make_token(sub="ou_bob"))).status_code == 404
    assert client.get(path, headers=auth(make_token(sub="ou_unknown"))).status_code == 404
    # The same frozen batch remains usable by its authorized owner.
    response = client.get(path, headers=auth(make_token()))
    assert response.status_code == 200
    assert ("base64" if suffix else "rows") in response.json()


@pytest.mark.parametrize("missing", ["exp", "iat", "iss", "aud", "sub"])
def test_signed_tokens_require_all_identity_and_lifetime_claims(client, missing):
    payload = {"iss": "http://portal.test", "aud": "bridgeflow", "iat": int(time.time()),
               "exp": int(time.time()) + 900, "sub": "ou_alice"}
    del payload[missing]
    token = jwt.encode(payload, PRIVATE, algorithm="EdDSA", headers={"kid": "k1"})
    assert client.get("/batches/" + "a" * 32, headers=auth(token)).status_code == 401


@pytest.mark.parametrize("subject", ["   ", 123])
def test_identity_subject_must_be_a_nonempty_string(client, subject):
    assert client.get("/batches/" + "a" * 32,
                      headers=auth(make_token(sub=subject))).status_code == 401


def workflow_setup(monkeypatch):
    from test_workflow_foundation import actual_answer, employee_submission

    from bridgeflow.api.workflow import service

    demo = REPO_ROOT / "data/workflow_demo/catalogue.yaml"
    monkeypatch.setattr(settings, "workflow_catalogue_path", str(demo))
    declared = yaml.safe_load(demo.read_text())
    acl_path = settings.access_control_path
    acl = yaml.safe_load(Path(acl_path).read_text())
    acl["users"]["ou_alice"]["workflow_departments"] = sorted(
        {t["department"] for t in declared["templates"].values()}
        | {s["department"] for s in declared["stages"].values()})
    acl["users"]["ou_bob"]["workflow_departments"] = [declared["templates"]["production_record"]["department"]]
    with open(acl_path, "w") as stream:
        yaml.safe_dump(acl, stream)
    domain = service()
    draft = domain.receive("production_record", employee_submission())
    draft = domain.answer(draft.id, actual_answer(), draft.seq)
    draft = domain.review(draft.id, draft.draft.digest, "reviewer", draft.seq)
    domain.submit(draft.id)
    return declared, draft.id


def test_workflow_browser_views_require_login_and_explicit_catalogue_grants(client, monkeypatch):
    declared, artifact_id = workflow_setup(monkeypatch)
    for path in ["/workflow/catalogue", "/workflow/board", "/workflow/adoption",
                 f"/workflow/artifacts/{artifact_id}", "/workflow/lineage/production_record/actual_qty"]:
        assert client.get(path).status_code == 401
    stranger = auth(make_token(sub="ou_unknown"))
    catalogue = client.get("/workflow/catalogue", headers=stranger).json()
    assert catalogue["templates"] == {} and catalogue["stages"] == {} and catalogue["lineage"] == []
    assert catalogue["mvp"] == {"status": "restricted"}
    assert client.get("/workflow/board", headers=stranger).json()["rows"] == []
    assert client.get("/workflow/adoption", headers=stranger).json() == []
    assert client.get(f"/workflow/artifacts/{artifact_id}", headers=stranger).status_code == 404
    assert client.get("/workflow/lineage/production_record/actual_qty", headers=stranger).status_code == 404
    alice = auth(make_token())
    assert client.get(f"/workflow/artifacts/{artifact_id}", headers=alice).status_code == 200
    assert set(client.get("/workflow/catalogue", headers=alice).json()["templates"]) == set(declared["templates"])
    assert any(r["kind"] == "handoff" for r in client.get("/workflow/board", headers=alice).json()["rows"])


def test_workflow_department_scope_filters_cross_department_dependencies(client, monkeypatch):
    declared, artifact_id = workflow_setup(monkeypatch)
    bob = auth(make_token(sub="ou_bob"))
    catalogue = client.get("/workflow/catalogue", headers=bob).json()
    production = declared["templates"]["production_record"]["department"]
    assert all(t["department"] == production for t in catalogue["templates"].values())
    assert "market_review" not in catalogue["stages"]
    assert catalogue["lineage"] == []
    rows = client.get("/workflow/board", headers=bob).json()["rows"]
    assert rows and all(r["kind"] == "artifact" and r["department"] == production for r in rows)
    assert client.get(f"/workflow/artifacts/{artifact_id}", headers=bob).status_code == 200


@pytest.mark.parametrize("grant", ["production", [123], [" "], None])
def test_malformed_access_grants_fail_closed(client, grant):
    acl_path = settings.access_control_path
    acl = yaml.safe_load(Path(acl_path).read_text())
    acl["users"]["ou_bob"]["workflow_departments"] = grant
    with open(acl_path, "w") as stream:
        yaml.safe_dump(acl, stream)
    # Access rules are validated before data is exposed, independently of which
    # employee owns another batch. A list-shaped contract cannot become a string.
    from fastapi import HTTPException

    from bridgeflow.access import workflow_departments_for
    with pytest.raises(HTTPException) as failure:
        workflow_departments_for("ou_bob")
    assert failure.value.status_code == 503


@pytest.mark.parametrize("payload", [{}, {"keys": []}, {"keys": "bad"}, {"keys": [None]}, []])
async def test_invalid_portal_key_sets_report_configuration_failure(monkeypatch, payload):
    import httpx
    from fastapi import HTTPException

    class PortalClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            return httpx.Response(200, json=payload)

    monkeypatch.setattr(identity.httpx, "AsyncClient", lambda **kwargs: PortalClient())
    with pytest.raises(HTTPException) as failure:
        await identity._fetch_jwks("http://portal.test")
    assert failure.value.status_code == 503


def test_read_scope_does_not_grant_batch_import_permission(client):
    batch_id = upload(client, auth(make_token()))
    path = Path(settings.access_control_path)
    acl = yaml.safe_load(path.read_text())
    acl["users"]["ou_alice"]["operations"] = []
    path.write_text(yaml.safe_dump(acl))
    assert client.get(f"/batches/{batch_id}", headers=auth(make_token())).status_code == 200
    assert client.post("/batches/demo", headers=auth(make_token())).status_code == 403


def test_review_notes_require_identity_write_grant_and_scope(client):
    from bridgeflow.api.batches import batch_path
    from bridgeflow.review_runs import notes

    batch_id = upload(client, auth(make_token()))
    report_id = "b" * 32
    folder = batch_path(batch_id).parent / "reviews" / batch_id
    folder.mkdir(parents=True)
    (folder / f"{report_id}.json").write_text('{}')
    body = {"batch_id": batch_id, "report_id": report_id, "parent_session_id": "session",
            "note_id": "note-identity", "note": "Needs business confirmation"}
    assert client.post("/tools/review-note", json=body).status_code == 401
    assert client.post("/tools/review-note", json=body, headers=auth(make_token(sub="ou_bob"))).status_code == 404
    assert client.post("/tools/review-note", json=body, headers=auth(make_token())).status_code == 403
    path = Path(settings.access_control_path)
    acl = yaml.safe_load(path.read_text())
    acl["users"]["ou_alice"]["operations"].append("review_note")
    path.write_text(yaml.safe_dump(acl))
    assert client.post("/tools/review-note", json=body, headers=auth(make_token())).status_code == 200
    assert notes(batch_id, report_id)[0].author == "ou_alice"
    assert (folder / f"{report_id}.json").read_text() == '{}'
