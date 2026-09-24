"""The open-item inbox (E14-UC05): one list of what is still waiting, and on whom."""
import json

import pytest
from conftest import receipt
from fastapi.testclient import TestClient
from test_conclusions import finalize
from test_resupply import LABELS, XLSX, original

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.monthly import inbox as inbox_module

DEMO = REPO_ROOT / "data/mock_business/demo"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "field_dictionary_path", str(DEMO / "dictionary.yaml"))
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


def inbox(client, period="2024-07", **params):
    query = "".join(f"&{k}={v}" for k, v in params.items())
    return client.get(f"/monthly/inbox?period={period}{query}").json()


def test_items_from_every_module_appear_once_with_where_to_settle_them(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    result = inbox(client)
    master = client.get(f"/integration/batches/{batch}").json()
    assert result["batch_id"] == batch
    assert sum(v for k, v in result["by_kind"].items() if k.startswith("master_")) == len(master["issues"])
    assert result["total"] == len(result["items"]) >= len(master["issues"])
    assert {item["next_view"] for item in result["items"]} <= {"integration", "quarantine", "columns", "state"}
    # AC-4: the inbox offers a place to go, never a decision.
    assert all(set(item) == {"id", "kind", "source", "batch_id", "period", "departments", "subject", "detail", "next_view"}
               for item in result["items"])


def test_filtering_narrows_the_list_while_the_total_still_counts_everything_visible(client):
    client.post("/batches/demo")
    everything = inbox(client)
    mine = inbox(client, department="production")
    assert mine["total"] == everything["total"] and mine["by_kind"] == everything["by_kind"]
    assert all("production" in item["departments"] for item in mine["items"])
    # A department with nothing waiting gets an empty list, not a different total.
    idle = next((d for d in ("procurement", "finance", "marketing")
                 if d not in everything["by_department"]), "")
    if idle:
        assert inbox(client, department=idle)["items"] == []
    assert inbox(client, kind="quarantined_row")["items"] == []


def test_an_item_outside_the_viewers_departments_is_neither_shown_nor_counted():
    ctx = inbox_module.Context(batch_id="b", period="2024-07")
    items = [inbox_module.OpenItem(id="1", kind="quarantined_row", source="quarantine", departments=["production"]),
             inbox_module.OpenItem(id="2", kind="quarantined_row", source="quarantine", departments=["finance"]),
             inbox_module.OpenItem(id="3", kind="master_disagreement", source="integration",
                                   departments=["production", "finance"])]
    scope = inbox_module.Scope(departments={"production"})
    monkey = {"quarantine": lambda _ctx: items[:2], "integration": lambda _ctx: items[2:]}
    original_sources = dict(inbox_module.SOURCES)
    inbox_module.SOURCES.clear(); inbox_module.SOURCES.update(monkey)
    try:
        result = inbox_module.collect(ctx, scope)
    finally:
        inbox_module.SOURCES.clear(); inbox_module.SOURCES.update(original_sources)
    # Only the production row: the finance row and the cross-department disagreement are out of scope.
    assert result["total"] == 1 and [i["id"] for i in result["items"]] == ["1"]
    assert result["by_department"] == {"production": 1}


def test_settling_an_item_in_its_own_module_removes_it_from_the_inbox(client):
    from test_resupply import abbreviated
    files = [("files", (f"{name}.xlsx", abbreviated(original(name)) if name == "production" else original(name), XLSX))
             for name in LABELS]
    batch = client.post("/batches", data={"period": "2024-07", "departments": list(LABELS)},
                        files=files).json()["batch_id"]
    before = inbox(client)
    spoiled = [i for i in before["items"] if i["kind"] == "master_disagreement"]
    assert len(spoiled) >= 2
    # Correcting the file settles the question in its own module; nothing tells the inbox.
    corrected = client.post(f"/batches/{batch}/departments/production",
                            data={"period": "2024-07", "reason": "客户单位更正"},
                            files={"file": ("production.xlsx", original("production"), XLSX)})
    assert corrected.status_code == 200, corrected.text
    after = inbox(client)
    assert after["batch_id"] == corrected.json()["batch"]["batch_id"]
    assert len([i for i in after["items"] if i["kind"] == "master_disagreement"]) == len(spoiled) - 1


def test_a_report_left_on_corrected_data_shows_up_as_an_item(client):
    files = [("files", (f"{name}.xlsx", original(name), XLSX)) for name in LABELS]
    batch = client.post("/batches", data={"period": "2024-07", "departments": list(LABELS)},
                        files=files).json()["batch_id"]
    finalize(client, batch)
    assert not [i for i in inbox(client)["items"] if i["kind"] == "stale_report"]
    from test_resupply import abbreviated
    derived = client.post(f"/batches/{batch}/departments/production",
                          data={"period": "2024-07", "reason": "更正后再对一次"},
                          files={"file": ("production.xlsx", abbreviated(original("production")), XLSX)})
    assert derived.status_code == 200, derived.text
    result = inbox(client)
    assert result["batch_id"] == derived.json()["batch"]["batch_id"]
    stale = [i for i in result["items"] if i["kind"] == "stale_report"]
    assert len(stale) == 1 and stale[0]["subject"] == batch and stale[0]["next_view"] == "state"


def test_a_review_on_an_unrelated_sample_is_not_a_stale_report(client):
    first = client.post("/batches/demo").json()["batch_id"]
    finalize(client, first)
    other = client.post("/batches/demo?case=clean").json()["batch_id"]
    result = inbox(client, batch_id=other)
    assert result["batch_id"] == other
    assert not [item for item in result["items"] if item["kind"] == "stale_report"]


def test_the_captain_sees_counts_by_kind_and_department(client):
    client.post("/batches/demo")
    result = client.post("/tools/monthly-inbox", json={"period": "2024-07"}).json()
    assert result["by_kind"] and result["by_department"]
    assert "decides nothing" in result["next_step"]


def test_a_broken_provenance_chain_reaches_the_inbox(client):
    """E13-UC06 AC-3: a cell nobody can trace becomes somebody's item (round 11)."""
    batch = client.post("/batches/demo").json()["batch_id"]
    items = {i["subject"]: i for i in inbox(client)["items"] if i["kind"] == "missing_provenance"}
    master = client.get(f"/integration/batches/{batch}").json()
    broken = {field for row in master["grades"] for field, result in row.items() if result["grade"] is None}
    # The demo case's disagreement leaves those cells empty and untraceable; every such field
    # is somebody's item, once per field rather than once per cell.
    assert set(items) == broken and broken
    for field, item in items.items():
        cells = sum(1 for row in master["grades"] if row[field]["grade"] is None)
        assert item["detail"].startswith(f"{cells} cell(s)") and item["next_view"] == "integration"


def test_a_confirmed_convention_is_not_reported_as_a_gap(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    before = len([i for i in inbox(client)["items"] if i["kind"] == "missing_provenance"])
    # Confirming changes a grade from G3 to G2; it never turns a missing chain into a present one.
    payload = {"batch_id": batch, "convention": "增值税税率", "action": "confirm",
               "source": "财务部确认函", "confirmed_by": "captain"}
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    assert client.post("/tools/convention-decide", content=raw,
                       headers={"content-type": "application/json",
                                "x-bridgeflow-approval": receipt(raw)}).status_code == 200
    assert len([i for i in inbox(client)["items"] if i["kind"] == "missing_provenance"]) == before
