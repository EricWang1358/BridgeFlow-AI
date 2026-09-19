"""Confirming or replacing a convention the business side never signed off (E13-UC05).

The demo batch rests on four conventions declared in `integration.yaml`. Nothing here calls a
model: a decision is a recorded fact with a source, and what it changes is the evidence grade.
"""
import json

import pytest
from conftest import receipt
from fastapi.testclient import TestClient
from test_conclusions import finalize

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

VAT, GAP, ROLLUP = "增值税税率", "市场_缺口", "rollup.production"
MARGIN = "物资_单方不含税毛利"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "field_dictionary_path", str(REPO_ROOT / "data/mock_business/demo/dictionary.yaml"))
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def batch(client):
    return client.post("/batches/demo").json()["batch_id"]


def decide(client, batch_id, convention, action, approve=True, **extra):
    payload = {"batch_id": batch_id, "convention": convention, "action": action,
               "confirmed_by": "captain", **extra}
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    headers = {"content-type": "application/json"}
    if approve:
        headers["x-bridgeflow-approval"] = receipt(body)
    return client.post("/tools/convention-decide", content=body, headers=headers)


def grade_of(client, batch_id, column):
    master = client.get(f"/integration/batches/{batch_id}").json()
    return master["grades"][0][column]["grade"]


def test_every_declared_convention_is_listed_with_what_it_governs(client, batch):
    listing = client.get(f"/conventions/batches/{batch}").json()
    kinds = {item["id"]: item["kind"] for item in listing["conventions"]}
    assert kinds == {VAT: "constant", GAP: "derived", "生产_客户合作状态诊断": "classification", ROLLUP: "rollup"}
    vat = next(item for item in listing["conventions"] if item["id"] == VAT)
    assert MARGIN in vat["affected_fields"] and vat["state"] == "unconfirmed"
    assert listing["unconfirmed"] == 4


def test_a_decision_needs_approval_and_a_source(client, batch):
    assert decide(client, batch, VAT, "confirm", approve=False, source="财务部确认函").status_code == 403
    assert decide(client, batch, VAT, "confirm", source=" ").status_code == 422
    assert decide(client, batch, "没有这条口径", "confirm", source="x").status_code == 404


def test_confirming_lifts_the_figures_that_rest_on_it_from_g3_to_g2(client, batch):
    assert grade_of(client, batch, MARGIN) == "G3"
    response = decide(client, batch, VAT, "confirm", source="财务部 2024-07-05 确认函：一般纳税人 13%")
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "confirmed" and response.json()["version"] == 1
    assert response.json()["decided_by"]
    assert grade_of(client, batch, MARGIN) == "G2"
    master = client.get(f"/integration/batches/{batch}").json()
    chain = master["grades"][0][MARGIN]["chain"]
    assert any(VAT in step and "confirmed" in step for step in chain), chain
    # The captain hears about it too, and still gets no cell values.
    summary = client.post("/tools/integration-summary", json={"batch_id": batch}).json()
    assert summary["convention_states"][VAT] == "confirmed"


def test_a_stale_reader_cannot_overwrite_a_newer_decision(client, batch):
    assert decide(client, batch, VAT, "confirm", source="财务部确认函").status_code == 200
    stale = decide(client, batch, VAT, "confirm", source="另一位同事凭印象", expected_version=0)
    assert stale.status_code == 409
    fresh = decide(client, batch, VAT, "replace", source="财务部更正：6%", requested_value="0.06",
                   expected_version=1)
    assert fresh.status_code == 200 and fresh.json()["version"] == 2


def test_replacing_a_formula_asks_for_a_declaration_change_rather_than_reinterpreting_it(client, batch):
    response = decide(client, batch, GAP, "replace", source="市场部会议纪要 2024-07-08",
                      note="目标应取年度预算而非累计结算")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "replacement_requested"
    assert body["declaration_change"].startswith("integration.yaml: derived.市场_缺口")
    # Nothing is recomputed, and a requested replacement does not pass as a confirmation.
    assert grade_of(client, batch, GAP) == "G3"
    assert decide(client, batch, VAT, "replace", source="口头说的", expected_version=0).status_code == 422


def test_a_constant_can_be_previewed_and_the_captain_sees_counts_not_cells(client, batch):
    preview = client.get(f"/conventions/batches/{batch}/preview",
                         params={"convention": VAT, "requested_value": "0.06"}).json()
    assert preview["changed_cells"] > 0 and MARGIN in preview["changed_fields"] and preview["sample"]
    for_captain = client.post("/tools/convention-preview",
                              json={"batch_id": batch, "convention": VAT, "requested_value": "0.06"}).json()
    assert "sample" not in for_captain and for_captain["changed_cells"] == preview["changed_cells"]
    assert client.post("/tools/convention-preview",
                       json={"batch_id": batch, "convention": ROLLUP, "requested_value": "什么"}).status_code == 422
    assert client.post("/tools/convention-preview",
                       json={"batch_id": batch, "convention": VAT, "requested_value": "六个点"}).status_code == 422


def test_the_brief_counts_confirmed_conventions_as_formula_evidence(client, batch):
    finalize(client, batch)
    before = client.get(f"/conclusions/batches/{batch}").json()
    assert decide(client, batch, VAT, "confirm", source="财务部确认函").status_code == 200
    after = client.get(f"/conclusions/batches/{batch}").json()
    assert after["completeness"]["cells_G3"] < before["completeness"]["cells_G3"]
    assert after["completeness"]["cells_G2"] > before["completeness"]["cells_G2"]
