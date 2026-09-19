"""Declared charts over declared numbers (E13-UC03). Nothing here calls a model."""
import pytest
from fastapi.testclient import TestClient
from test_comparison import JUNE, LABELS, XLSX

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

DEMO = REPO_ROOT / "data/mock_business/demo"
MAY = REPO_ROOT / "data/mock_business/monthly/2024-05-调优A"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "field_dictionary_path", str(DEMO / "dictionary.yaml"))
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


def import_month(client, folder, period):
    files = [("files", (f"{label}.xlsx", (folder / f"{label}.xlsx").read_bytes(), XLSX)) for label in LABELS.values()]
    response = client.post("/batches", data={"period": period, "departments": list(LABELS)}, files=files)
    assert response.status_code == 200, response.text
    return response.json()["batch_id"]


def charts_of(client, batch):
    return {c["id"]: c for c in client.get(f"/conclusions/batches/{batch}/charts").json()["charts"]}


def test_one_period_is_an_explanation_not_a_line_with_one_dot(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    trend = charts_of(client, batch)["sign_rate_trend"]
    assert trend["status"] == "needs_more_periods" and "two periods" in trend["reason"]
    assert [p for p in trend["points"] if p["value"] is not None] == trend["points"][-1:]


def test_three_periods_draw_a_line_with_the_declared_threshold_and_drillable_points(client):
    import_month(client, MAY, "2024-05")
    import_month(client, JUNE, "2024-06")
    batch = client.post("/batches/demo").json()["batch_id"]
    trend = charts_of(client, batch)["sign_rate_trend"]
    assert trend["status"] == "ready" and trend["unit"] == "%"
    measured = [p for p in trend["points"] if p["value"] is not None]
    assert [p["period"] for p in measured] == ["2024-05", "2024-06", "2024-07"]
    # AC-1: the threshold comes from the same declaration as the conclusion's judgement.
    assert trend["threshold"] == 97 and trend["threshold_label"] == "below"
    # Every point says which batch it came from, so it can be drilled.
    assert all(p["batch_id"] for p in measured)
    assert client.get(f"/batches/{measured[-1]['batch_id']}").status_code == 200


def test_a_month_without_a_batch_is_a_gap_and_never_interpolated(client):
    import_month(client, MAY, "2024-05")
    batch = client.post("/batches/demo").json()["batch_id"]  # June is missing
    trend = charts_of(client, batch)["sign_rate_trend"]
    june = next(p for p in trend["points"] if p["period"] == "2024-06")
    assert june["value"] is None and june["batch_id"] == ""
    assert trend["status"] == "ready"  # two measured periods are still a line


def test_the_variance_waterfall_parts_add_up_to_the_change(client):
    import_month(client, JUNE, "2024-06")
    batch = client.post("/batches/demo").json()["batch_id"]
    chart = charts_of(client, batch)["output_variance"]
    assert chart["status"] == "ready"
    points = {p["label"]: p["value"] for p in chart["points"]}
    parts = points["new_entities"] + points["discontinued"] + points["continuing"]
    assert abs(points["base"] + parts - points["current"]) < 1e-6


def test_without_a_base_period_the_waterfall_says_so_instead_of_drawing_zero(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    chart = charts_of(client, batch)["output_variance"]
    assert chart["status"] == "unavailable" and chart["points"] == []


def test_entity_bars_are_declared_fields_largest_first_and_mark_declared_breaches(client):
    import_month(client, JUNE, "2024-06")
    batch = client.post("/batches/demo").json()["batch_id"]
    chart = charts_of(client, batch)["project_output_bars"]
    values = [p["value"] for p in chart["points"]]
    assert values == sorted(values, key=abs, reverse=True) and len(values) <= 8
    assert [p["key"][0] for p in chart["points"] if p["breach"]] == ["PRJ2023098"]
    master = client.get(f"/integration/batches/{batch}").json()
    first = chart["points"][0]
    row = next(r for r in master["rows"] if r["key"] == first["key"])
    assert row["values"]["生产_实际量"] == first["value"]


def test_a_dictionary_without_chart_declarations_shows_tables_instead(client, monkeypatch):
    batch = client.post("/batches/demo").json()["batch_id"]
    from bridgeflow.api.batches import batch_path, load_batch
    from bridgeflow.store import _write
    snapshot = load_batch(batch)
    snapshot.dictionary_snapshot["business_review"].pop("charts")
    _write(batch_path(batch), snapshot.model_dump(mode="json"))
    result = client.get(f"/conclusions/batches/{batch}/charts").json()
    assert result["charts"] == [] and "table" in result["refusal"]
