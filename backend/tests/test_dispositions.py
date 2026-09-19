"""Taking a declared action on a risk finding (E07-UC07). The machine is declared, not invented."""
import json

import pytest
from conftest import receipt
from fastapi.testclient import TestClient
from test_conclusions import finalize

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.monthly import dispositions

DEMO = REPO_ROOT / "data/mock_business/demo"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "field_dictionary_path", str(DEMO / "dictionary.yaml"))
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def batch(client):
    batch_id = client.post("/batches/demo").json()["batch_id"]
    finalize(client, batch_id)
    return batch_id


def act(client, batch_id, check_id, action, note="", approve=True, **extra):
    payload = {"batch_id": batch_id, "check_id": check_id, "action": action, "note": note,
               "confirmed_by": "captain", **extra}
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    headers = {"content-type": "application/json"}
    if approve:
        headers["x-bridgeflow-approval"] = receipt(body)
    return client.post("/tools/risk-disposition-record", content=body, headers=headers)


def listed(client, batch_id):
    return {d["check_id"]: d for d in client.get(f"/reviews/{batch_id}/dispositions").json()["dispositions"]}


def test_every_attention_finding_starts_in_the_declared_initial_state(client, batch):
    found = listed(client, batch)
    assert set(found) == {"net_margin", "collection_gap", "material_cost"}
    assert all(item["state"] == "待确认" and item["version"] == 0 for item in found.values())
    assert found["net_margin"]["available"] == ["confirm", "reject"]


def test_a_finding_moves_only_where_the_declaration_allows_and_only_with_approval(client, batch):
    assert act(client, batch, "net_margin", "close", note="直接关掉").status_code == 409
    assert act(client, batch, "net_margin", "confirm", approve=False).status_code == 403
    assert act(client, batch, "net_margin", "confirm").status_code == 200
    assert listed(client, batch)["net_margin"]["state"] == "已确认"
    # A transition the declaration says needs a reason is refused without one.
    assert act(client, batch, "net_margin", "assign").status_code == 422
    assert act(client, batch, "net_margin", "assign", note="交生产部本周核对").status_code == 200
    closed = act(client, batch, "net_margin", "close", note="已按核对结果调整下月计划")
    assert closed.status_code == 200 and closed.json()["closed"] is True
    assert "unchanged" in closed.json()["next_step"]


def test_the_log_is_append_only_and_a_stale_decision_is_refused(client, batch):
    assert act(client, batch, "collection_gap", "confirm").status_code == 200
    stale = act(client, batch, "collection_gap", "reject", note="其实不成立", expected_version=0)
    assert stale.status_code == 409
    report_id = client.get(f"/reviews/{batch}/dispositions").json()["report_id"]
    moves = dispositions.history(batch, report_id)
    assert [m.action for m in moves] == ["confirm"]
    assert act(client, batch, "collection_gap", "assign", note="市场部跟进", expected_version=1).status_code == 200
    moves = dispositions.history(batch, report_id)
    assert [(m.from_state, m.to_state) for m in moves] == [("待确认", "已确认"), ("已确认", "处理中")]
    assert all(m.decided_by for m in moves) and all(m.at for m in moves)


def test_a_finding_the_report_does_not_name_is_refused(client, batch):
    assert act(client, batch, "sign_rate", "confirm").status_code == 404


def test_without_a_declared_process_nothing_is_offered_and_nothing_is_recorded(client, batch):
    from bridgeflow.api.batches import batch_path, load_batch
    from bridgeflow.store import _write
    snapshot = load_batch(batch)
    snapshot.dictionary_snapshot.pop("risk_disposition")
    _write(batch_path(batch), snapshot.model_dump(mode="json"))
    result = client.get(f"/reviews/{batch}/dispositions").json()
    assert result["dispositions"] == [] and "declares states" in result["refusal"]
    assert act(client, batch, "net_margin", "confirm").status_code == 409


def test_the_captain_sees_states_and_what_the_declaration_allows(client, batch):
    assert act(client, batch, "material_cost", "confirm").status_code == 200
    result = client.post("/tools/risk-dispositions", json={"batch_id": batch}).json()
    assert result["open"] == 3  # confirmed is not closed
    material = next(d for d in result["dispositions"] if d["check_id"] == "material_cost")
    assert material["state"] == "已确认" and material["available"] == ["assign"]
    assert "approval" in result["next_step"]
