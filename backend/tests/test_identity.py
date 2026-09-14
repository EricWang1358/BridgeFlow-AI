"""Portal identity and department-scoped batch visibility (docs/27).

Offline: JWKS comes from a stub, tokens are signed with a throwaway test key.
"""
import json
import time

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
        "ou_alice": {"name": "Alice", "departments": list(business.ROLES)},
        "ou_bob": {"name": "Bob", "departments": ["production"]},
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
    response = client.post("/batches", data={"period": "2025-11", "departments": list(business.ROLES)},
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
