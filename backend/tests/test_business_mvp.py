"""Visible demo cases with independent standard answers, never held-out fixtures."""
import importlib.util
import json

import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from bridgeflow import business
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.api.batches import load_batch
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

CASES = REPO_ROOT / "data/business_demo"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "field_dictionary_path", str(CASES / "dictionary.yaml"))
    with TestClient(app) as client:
        yield client


def upload(client, case="risk", replacements=None):
    files = []
    for role in business.ROLES:
        content = (CASES / case / f"{role}.csv").read_bytes()
        if replacements and role in replacements:
            content = replacements[role](content)
        files.append(("files", (f"{role}.csv", content, "text/csv")))
    response = client.post("/batches", data={"period": "2025-11", "departments": list(business.ROLES)}, files=files)
    assert response.status_code == 200, response.text
    return response.json()["batch_id"]


def judgement(packet):
    return {"checks": [{"check_id": c["check_id"], "metric": c["metric"], "value": c["value"],
        "unit": c["unit"], "status": c["expected_status"], "action": c["actions"][c["expected_status"]][0],
        "explanation": "应按本部门权限核实并提交责任人复核。"} for c in packet["checks"]]}


@pytest.mark.parametrize("case", ["risk", "balanced"])
def test_four_departments_match_independent_standard_answers(client, case):
    batch_id = upload(client, case)
    result = client.post("/tools/review-context", json={"batch_id": batch_id})
    assert result.status_code == 200, result.text
    context = result.json()
    expected = json.loads((CASES / "expected.json").read_text())[case]
    assert {k: v["value"] for k, v in context["facts"].items()} == expected["metric_values"]
    assert len(context["roles"]) == 4
    for packet in context["roles"]:
        assert len(packet["checks"]) == 2
        assert packet["responsibility"] and packet["decision_owner"]
        assert all(c["expected_status"] == expected["check_status"] for c in packet["checks"])
        for check in packet["checks"]:
            assert check["sources"] and len(check["sources"]) <= 5
            assert all(ref["filename"] and ref["source_row"] >= 2 and ref["batch"] == batch_id for ref in check["sources"])
    api = client.post("/tools/aggregate-metric", json={"batch_id": batch_id, "period": "2025-11", "metric": "capacity_utilisation"})
    assert api.status_code == 200, api.text
    assert api.json()["unit"] == "%"
    assert api.json()["value"] == expected["metric_values"]["capacity_utilisation"]
    runs = [{"role": p["role"], "session_id": f"child-{p['role']}", "status": "completed", "judgement": judgement(p)} for p in context["roles"]]
    report = client.post("/tools/review-finalize", json={"batch_id": batch_id, "parent_session_id": "parent", "runs": runs}).json()
    assert report["status"] == "validated"
    assert client.get(f"/batches/{batch_id}/review").json() == report
    assert all(c["execution_status"] == "proposed_only" for r in report["roles"] for c in r["checks"])


@pytest.mark.parametrize("field,value", [("value", 999), ("unit", "USD"), ("metric", "invented"),
    ("status", "ok"), ("action", "自动批准授信"), ("explanation", "已批准90天账期")])
def test_numeric_and_responsibility_substitutions_are_refused(client, field, value):
    batch_id = upload(client)
    packet = client.post("/tools/review-context", json={"batch_id": batch_id}).json()["roles"][0]
    candidate = judgement(packet)
    candidate["checks"][0][field] = value
    with pytest.raises(HTTPException):
        business.validate_role(packet, candidate)


def test_failed_child_is_not_reported_as_low_confidence_success(client):
    batch_id = upload(client)
    packets = client.post("/tools/review-context", json={"batch_id": batch_id}).json()["roles"]
    runs = [{"role": p["role"], "session_id": f"child-{p['role']}", "status": "completed", "judgement": judgement(p)} for p in packets]
    runs[1].update(status="max-tokens", judgement=None)
    report = client.post("/tools/review-finalize", json={"batch_id": batch_id, "parent_session_id": "parent", "runs": runs}).json()
    assert report["status"] == "partial"
    assert report["roles"][1]["status"] == "unvalidated"
    assert report["roles"][1]["checks"] == []


def test_positive_margin_cannot_be_used_to_claim_no_loss_provision_is_required(client):
    batch_id = upload(client, "balanced")
    packets = client.post("/tools/review-context", json={"batch_id": batch_id}).json()["roles"]
    packet = next(p for p in packets if p["role"] == "finance")
    candidate = judgement(packet)
    candidate["checks"][0]["explanation"] = "毛利为正，因此无需计提损失。"
    with pytest.raises(HTTPException, match="evidence scope"):
        business.validate_role(packet, candidate)


def test_attention_threshold_is_not_an_approved_credit_limit(client):
    batch_id = upload(client)
    packets = client.post("/tools/review-context", json={"batch_id": batch_id}).json()["roles"]
    packet = next(p for p in packets if p["role"] == "marketing")
    candidate = judgement(packet)
    candidate["checks"][1]["explanation"] = "客户请求账期高于已批准上限。"
    with pytest.raises(HTTPException, match="evidence scope"):
        business.validate_role(packet, candidate)


@pytest.mark.parametrize("replacement", [lambda b: b.replace(b",12,10,SGD", b",,10,SGD", 1),
    lambda b: b.replace(b"SGD", b"USD", 1)])
def test_missing_price_or_currency_mismatch_cannot_produce_a_full_report(client, replacement):
    batch_id = upload(client, replacements={"procurement": replacement})
    assert client.post("/tools/review-context", json={"batch_id": batch_id}).status_code == 409


def test_ambiguity_blocks_review_and_old_batch_does_not_change(client):
    batch_id = upload(client, replacements={"production": lambda b: b.replace(b"2025-11-03", b"03/11/2025", 1)})
    before = load_batch(batch_id).model_dump()
    assert client.post("/tools/review-context", json={"batch_id": batch_id}).status_code == 409
    fixed = upload(client)
    assert client.post("/tools/review-context", json={"batch_id": fixed}).status_code == 200
    assert load_batch(batch_id).model_dump() == before


def test_identical_rows_are_not_silently_treated_as_duplicate_transactions(client):
    batch_id = upload(client, replacements={"procurement": lambda b: b + b.splitlines()[1] + b"\n"})
    response = client.post("/tools/review-context", json={"batch_id": batch_id})
    assert response.status_code == 409
    assert "transaction identity" in response.text


@pytest.mark.parametrize("replacement", [lambda b: b.replace(b",2000,", b",-2000,", 1),
    lambda b: b.replace(b",800,", b",0,", 1).replace(b",600,", b",0,", 1)])
def test_signed_cost_or_zero_ar_denominator_requires_a_new_business_contract(client, replacement):
    batch_id = upload(client, replacements={"finance": replacement})
    assert client.post("/tools/review-context", json={"batch_id": batch_id}).status_code == 409


async def test_source_lineage_survives_blank_duplicate_and_quarantined_rows():
    frame = pd.DataFrame({"sku": ["A", None, "A", "B", "C"],
        "date": ["2025-11-03", None, "2025-11-03", "03/11/2025", "2025-11-05"],
        "qty": [10, None, 10, 20, 30]})
    table = await DataSanitizerAgent().run(SanitizerInput("production", "2025-11", frame))
    assert table.source_rows == [2, 6]
    assert [r["sku"] for r in table.rows] == ["A", "C"]
    assert table.quarantine[0]["date"] == "03/11/2025"


def test_uploaded_csv_blank_record_does_not_shift_original_row_references(client):
    batch_id = upload(client, replacements={"production": lambda b: b.replace(b"\n", b"\n\n", 1)})
    table = next(t for t in load_batch(batch_id).clean_tables if t.department == "production")
    assert table.source_rows == [3, 4, 5, 6]


def test_generator_is_reproducible(tmp_path):
    spec = importlib.util.spec_from_file_location("business_case", REPO_ROOT / "scripts/make_business_case.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate(tmp_path)
    for source in CASES.rglob("*"):
        if source.is_file():
            assert (tmp_path / source.relative_to(CASES)).read_bytes() == source.read_bytes()


def test_exact_report_routes_and_explanation_limit(client):
    batch = upload(client)
    packets = client.post('/tools/review-context', json={'batch_id': batch}).json()['roles']
    runs = [{'role': p['role'], 'session_id': f"child-{p['role']}", 'status': 'completed', 'judgement': judgement(p)} for p in packets]
    first = client.post('/tools/review-finalize', json={'batch_id': batch, 'parent_session_id': 'parent', 'runs': runs}).json()
    runs[0]['judgement']['checks'][0]['explanation'] = '应' * 121
    second = client.post('/tools/review-finalize', json={'batch_id': batch, 'parent_session_id': 'parent', 'runs': runs}).json()
    assert second['status'] == 'partial'
    assert client.get(f'/batches/{batch}/review').json() == second
    assert client.get(f"/batches/{batch}/review?report_id={first['report_id']}").json() == first
    assert client.get(f'/batches/{batch}/review?report_id=../invalid').status_code == 422
    other = upload(client)
    assert client.get(f"/batches/{other}/review?report_id={first['report_id']}").status_code == 404
