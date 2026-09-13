"""Quarantined rows leave through a recorded, revalidated decision and a new batch (#88)."""
import json

import pytest
from conftest import receipt
from fastapi.testclient import TestClient
from test_business_mvp import CASES, upload

from bridgeflow.api.batches import load_batch
from bridgeflow.api.main import app
from bridgeflow.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "field_dictionary_path", str(CASES / "dictionary.yaml"))
    with TestClient(app) as client:
        yield client


def with_bad_rows(content: bytes) -> bytes:
    text = content.decode()
    return (text.rstrip("\n") + "\nSKU-B2,LINE-B,03/11/2025,30,20,20\n,,,,,7\n").encode()


def approved(client, path, payload, approve=True):
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    headers = {"content-type": "application/json"}
    if approve:
        headers["x-bridgeflow-approval"] = receipt(body)
    return client.post(path, content=body, headers=headers)


def decide(client, batch_id, index, action, reason="负责人确认", fixes=None, approve=True):
    return approved(client, "/tools/quarantine-decide", {"batch_id": batch_id, "department": "production", "index": index,
        "action": action, "reason": reason, "fixes": fixes or [], "confirmed_by": "captain", "call_id": f"c{index}{action}"}, approve)


def test_the_listing_names_failing_checks_without_cell_values(client):
    batch_id = upload(client, replacements={"production": with_bad_rows})
    listing = client.post("/tools/quarantine-list", json={"batch_id": batch_id}).json()
    assert listing["total"] == 2 and not any(e["releasable"] for e in listing["entries"])
    text = json.dumps(listing, ensure_ascii=False)
    assert "03/11/2025" not in text and "SKU-B2" not in text
    assert any("date" in check for e in listing["entries"] for check in e["failing_checks"])


def test_release_requires_revalidation_and_approval(client):
    batch_id = upload(client, replacements={"production": with_bad_rows})
    ambiguous, blank = 1, 0
    assert decide(client, batch_id, ambiguous, "release").status_code == 409
    assert decide(client, batch_id, ambiguous, "release", fixes=[{"column": "date", "value": "2025-11-03"}], approve=False).status_code == 403
    assert decide(client, batch_id, ambiguous, "release", fixes=[{"column": "date", "value": "2025-11-03"}]).status_code == 200
    assert decide(client, batch_id, blank, "release").status_code == 409  # mostly blank: cannot be released
    assert decide(client, batch_id, blank, "discard", fixes=[{"column": "output", "value": "1"}]).status_code == 422


def test_applying_creates_a_derived_batch_and_leaves_the_original_frozen(client):
    batch_id = upload(client, replacements={"production": with_bad_rows})
    before = load_batch(batch_id)
    assert client.post("/tools/review-context", json={"batch_id": batch_id}).status_code == 409
    assert decide(client, batch_id, 1, "release", fixes=[{"column": "date", "value": "2025-11-03"}]).status_code == 200
    assert decide(client, batch_id, 0, "discard", reason="空行，来源文件录入错误").status_code == 200
    applied = approved(client, "/tools/quarantine-apply", {"batch_id": batch_id, "confirmed_by": "captain", "call_id": "a1"})
    assert applied.status_code == 200, applied.text
    derived = applied.json()["batch"]
    assert derived["derived_from"] == batch_id and derived["batch_id"] != batch_id
    production = next(d for d in derived["departments"] if d["department"] == "production")
    assert production["quarantined"] == 0
    table = next(t for t in load_batch(derived["batch_id"]).clean_tables if t.department == "production")
    assert {c.rule for c in table.corrections} >= {"quarantine_released", "quarantine_discarded"}
    assert any(row.get("date") == "2025-11-03" and row.get("sku") == "SKU-B2" for row in table.rows)

    assert client.post("/tools/review-context", json={"batch_id": derived["batch_id"]}).status_code == 200
    assert load_batch(batch_id) == before  # frozen
    again = approved(client, "/tools/quarantine-apply", {"batch_id": batch_id, "confirmed_by": "captain", "call_id": "a2"}).json()
    assert again["replayed"] is True and again["batch"]["batch_id"] == derived["batch_id"]
    assert decide(client, batch_id, 0, "discard").status_code == 409
    view = client.get(f"/batches/{batch_id}/view?section=quarantine").json()["rows"]
    assert [r["decision"] for r in view] == ["discard", "release"]


def test_a_row_shifted_by_one_column_is_offered_as_repairable_and_released_only_by_decision(client):
    def shifted_row(content: bytes) -> bytes:
        return (content.decode().rstrip("\n") + "\n,SKU-C3,LINE-C,2025-11-05,12,10\n").encode()

    batch_id = upload(client, replacements={"production": shifted_row})
    [entry] = [e for e in client.post("/tools/quarantine-list", json={"batch_id": batch_id}).json()["entries"]
               if e["department"] == "production"]
    assert (entry["releasable"], entry["shift_suggestion"]) == (False, "left")
    assert decide(client, batch_id, entry["index"], "release").status_code == 409  # as written it still fails
    response = approved(client, "/tools/quarantine-decide", {"batch_id": batch_id, "department": "production",
        "index": entry["index"], "action": "release", "reason": "整行右移一格", "fixes": [], "shift": "left",
        "confirmed_by": "captain", "call_id": "shift"})
    assert response.status_code == 200, response.text
    applied = approved(client, "/tools/quarantine-apply", {"batch_id": batch_id, "confirmed_by": "captain", "call_id": "apply"}).json()
    table = next(t for t in load_batch(applied["batch"]["batch_id"]).clean_tables if t.department == "production")
    assert any(r.get("sku") == "SKU-C3" and r.get("date") == "2025-11-05" and r.get("available_hrs") is None for r in table.rows)
