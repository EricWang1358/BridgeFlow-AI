"""This month against a base period (E13-UC02).

Two batches of the fictional supplier: 2024-06 (imported here) and 2024-07 (the sample
notebook case). Nothing calls a model; every figure comes from the frozen declarations.
"""
import pytest
from fastapi.testclient import TestClient

from bridgeflow.api.main import app
from bridgeflow.conclusions import comparison
from bridgeflow.config import REPO_ROOT, settings

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
LABELS = {"production": "生产部", "procurement": "物资部", "finance": "财务部", "marketing": "市场部"}
JUNE = REPO_ROOT / "data/mock_business/monthly/2024-06-调优B"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "field_dictionary_path", str(REPO_ROOT / "data/mock_business/demo/dictionary.yaml"))
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


def import_june(client):
    files = [("files", (f"{label}.xlsx", (JUNE / f"{label}.xlsx").read_bytes(), XLSX)) for label in LABELS.values()]
    response = client.post("/batches", data={"period": "2024-06", "departments": list(LABELS)}, files=files)
    assert response.status_code == 200, response.text
    return response.json()["batch_id"]


def test_the_period_shift_wraps_years():
    assert comparison.shift("2024-01", -1) == "2023-12"
    assert comparison.shift("2024-07", -12) == "2023-07"


def test_without_a_base_batch_the_comparison_says_so_rather_than_showing_zero(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    result = client.get(f"/conclusions/batches/{batch}/comparison").json()
    assert result["status"] == "no_base" and result["base_period"] == "2024-06"
    assert result["metrics"] == [] and "2024-06" in result["reason"]


def test_a_plan_comparison_is_refused_until_a_plan_source_is_declared(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    result = client.get(f"/conclusions/batches/{batch}/comparison?base=plan").json()
    assert result["status"] == "unavailable" and "plan" in result["reason"].lower()


def test_entity_changes_decompose_into_new_gone_and_continuing(client):
    import_june(client)
    batch = client.post("/batches/demo").json()["batch_id"]
    result = client.get(f"/conclusions/batches/{batch}/comparison").json()
    assert result["status"] == "compared" and result["base_period"] == "2024-06"
    for total in result["totals"]:
        parts = total["new_entities"] + total["discontinued"] + total["continuing"]
        assert abs(parts - total["absolute"]) < 1e-6, total["field"]
    signed = next(t for t in result["totals"] if t["field"] == "生产_实际量")
    assert signed["current"] > 0 and signed["base"] > 0


def test_a_decline_past_the_declared_threshold_is_flagged_with_both_periods(client):
    import_june(client)
    batch = client.post("/batches/demo").json()["batch_id"]
    result = client.get(f"/conclusions/batches/{batch}/comparison").json()
    breach = [b for b in result["breaches"] if b["field"] == "生产_实际量"]
    assert [b["key"][0] for b in breach] == ["PRJ2023098"]  # −40% against a declared −20%
    assert breach[0]["current"] is not None and breach[0]["base"] is not None and breach[0]["relative"] < -0.2


def test_key_metrics_carry_their_change_into_the_brief(client):
    import_june(client)
    batch = client.post("/batches/demo").json()["batch_id"]
    packets = client.post("/tools/review-context", json={"batch_id": batch}).json()["roles"]
    runs = [{"role": p["role"], "session_id": f"c-{p['role']}", "status": "completed", "judgement": {"checks": [
        {"check_id": c["check_id"], "metric": c["metric"], "value": c["value"], "unit": c["unit"],
         "status": c["expected_status"], "action": c["actions"][c["expected_status"]][0],
         "explanation": "应按本部门权限核实并提交责任人复核。"} for c in p["checks"]]}} for p in packets]
    client.post("/tools/review-finalize", json={"batch_id": batch, "parent_session_id": "p", "runs": runs})
    brief = client.get(f"/conclusions/batches/{batch}").json()
    assert brief["comparison"]["status"] == "compared"
    changes = {m["metric"]: m["change"] for m in brief["key_metrics"]}
    assert all(c and c["state"] in {"compared", "not_computable"} for c in changes.values())
    net = changes["net_margin"]
    assert net["base"] is not None and abs(net["absolute"] - (net["current"] - net["base"])) < 1e-9
    # A ratio metric changes by points; a ratio of two ratios is not reported (D7).
    assert net["basis"] == "percentage_points" and net["relative"] is None
    assert len(brief["comparison"]["breaches"]) >= 1


def test_a_changed_field_declaration_refuses_the_comparison(client, monkeypatch):
    import_june(client)
    batch = client.post("/batches/demo").json()["batch_id"]
    from bridgeflow.api.batches import batch_path, load_batch
    from bridgeflow.store import _write
    base_id = comparison.periods.batches_for("2024-06")[0]["batch_id"]
    snapshot = load_batch(base_id)
    snapshot.integration_snapshot["fields"].pop("生产_实际量")
    _write(batch_path(base_id), snapshot.model_dump(mode="json"))
    result = client.get(f"/conclusions/batches/{batch}/comparison").json()
    assert result["status"] == "declaration_changed" and result["changed_fields"] == ["生产_实际量"]


def test_a_zero_base_is_not_computable_rather_than_an_infinite_percentage():
    assert comparison._delta(5.0, 0.0) == (5.0, None, "not_computable")
    assert comparison._delta(5.0, None) == (None, None, "missing_in_base")
    assert comparison._delta(4.0, 2.0) == (2.0, 1.0, "compared")
