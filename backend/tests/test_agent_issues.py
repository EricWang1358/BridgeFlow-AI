"""The captain can read what the right-hand panel shows — and one held row on request (#245).

The walk these tests take: a batch with sanitizer corrections, quarantined rows, a
column question and unresolved mappings; `batch-issues` projects every open item with
its settling tool and nothing beyond them; `quarantine-row` returns exactly one held
row — values, provenance, current checks — capped, attributed, and logged; a proposed
fix records who proposed it and still revalidates. The boundary #245 revised holds:
cell contents enter the context bound to one open item at a time, never in bulk.
"""
import json
from pathlib import Path

import pytest
from conftest import receipt
from fastapi.testclient import TestClient
from test_business_mvp import CASES, upload
from test_quarantine_dispositions import with_bad_rows

from bridgeflow.api.main import app
from bridgeflow.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "field_dictionary_path", str(CASES / "dictionary.yaml"))
    with TestClient(app) as client:
        yield client


def with_renamed_project(content: bytes) -> bytes:
    """Finance uploads under a header the dictionary does not know: a column question."""
    header, rest = content.split(b"\n", 1)
    names = header.decode().split(",")
    return (",".join("project_code" if name == "project" else name for name in names) + "\n").encode() + rest


def a_bad_batch(client) -> str:
    """A batch carrying corrections, two quarantined rows and a renamed column."""
    return upload(client, replacements={"production": with_bad_rows, "finance": with_renamed_project})


def test_batch_issues_lists_every_kind_with_its_settling_tool(client):
    batch_id = a_bad_batch(client)
    response = client.post("/tools/batch-issues", json={"batch_id": batch_id})
    assert response.status_code == 200, response.text
    issues = response.json()
    assert issues["counts"]["quarantined_row"] == 2, "the two held rows are missing"
    assert issues["counts"]["intake_correction"] >= 1, "sanitizer corrections are not listed"
    assert issues["counts"]["column_question"] >= 1, "the renamed column is not asking"

    by_kind: dict[str, list[dict]] = {}
    for item in issues["items"]:
        by_kind.setdefault(item["kind"], []).append(item)
    assert all(item["next_step"] for items in by_kind.values() for item in items), \
        "an issue without a way forward is a dead end"
    quarantined = by_kind["quarantined_row"][0]
    assert quarantined["checks"] and quarantined["releasable"] is False
    correction = by_kind["intake_correction"][0]
    assert correction["rule"] and correction["detail"]


def test_batch_issues_leaks_nothing_beyond_the_listed_items(client):
    batch_id = a_bad_batch(client)
    text = client.post("/tools/batch-issues", json={"batch_id": batch_id}).text
    # Cells of healthy rows have no open item, so they must not appear: the boundary
    # is per-item, and this is the byte-retrieval check the AC demands.
    healthy = (CASES / "risk" / "marketing.csv").read_text(encoding="utf-8").splitlines()[1]
    for cell in {c for c in healthy.split(",") if len(c) > 3}:
        assert cell not in text, f"unlisted cell value {cell!r} leaked into batch-issues"
    # A held row's own cells are absent — they live behind quarantine-row. The
    # ambiguous date DOES appear: it is the listed correction item's own `before`,
    # exactly the per-item allowance the revised boundary makes.
    assert "SKU-B2" not in text, "a held row's unlisted values leaked"


def test_quarantine_row_returns_one_rows_values_provenance_and_checks(client):
    batch_id = a_bad_batch(client)
    listing = client.post("/tools/quarantine-list", json={"batch_id": batch_id}).json()
    target = next(e for e in listing["entries"] if any("date" in c for c in e["failing_checks"]))

    response = client.post("/tools/quarantine-row",
                           json={"batch_id": batch_id, "department": target["department"], "index": target["index"]})
    assert response.status_code == 200, response.text
    row = response.json()
    assert "03/11/2025" in json.dumps(row["values"], ensure_ascii=False), "the row's values are the point"
    assert set(row["original_columns"]) == set(row["values"])
    assert any("date" in check for check in row["failing_checks"])
    assert row["releasable"] is False and row["next_step"]


def test_quarantine_row_404s_off_the_open_items_and_caps_wide_cells(client):
    batch_id = a_bad_batch(client)
    assert client.post("/tools/quarantine-row",
                       json={"batch_id": batch_id, "department": "production", "index": 99}).status_code == 404
    assert client.post("/tools/quarantine-row",
                       json={"batch_id": batch_id, "department": "logistics", "index": 0}).status_code == 404

    def with_wide_cell(content: bytes) -> bytes:
        # The ambiguous-date row is quarantined regardless of its other cells; park a
        # 6 KB value in one of them and the read must cap it, not pass it through.
        return with_bad_rows(content).replace(b"30,20,20", b"30,20," + b"x" * 6000)

    batch = upload(client, replacements={"production": with_wide_cell})
    listing = client.post("/tools/quarantine-list", json={"batch_id": batch}).json()
    target = next(e for e in listing["entries"] if any("date" in c for c in e["failing_checks"]))
    row = client.post("/tools/quarantine-row",
                      json={"batch_id": batch, "department": target["department"], "index": target["index"]}).json()
    truncated = [name for name, value in row["values"].items()
                 if isinstance(value, str) and value.endswith("…(truncated)")]
    assert truncated, "a wide cell slipped through uncapped"
    assert set(truncated) == set(row["cells_truncated"])


def test_every_cell_read_lands_in_the_access_log(client):
    batch_id = a_bad_batch(client)
    client.post("/tools/quarantine-row", json={"batch_id": batch_id, "department": "production", "index": 0})
    files = list(Path(settings.cell_access_log_path).glob("*.jsonl"))
    assert files, "a cell read went unwritten"
    entry = json.loads(files[0].read_text(encoding="utf-8").splitlines()[-1])
    assert entry["batch_id"] == batch_id and entry["department"] == "production"
    assert entry["item"] == "quarantine:production:0" and isinstance(entry["columns"], list)


def test_a_proposed_fix_is_attributed_and_still_revalidates(client):
    batch_id = a_bad_batch(client)
    payload = {"batch_id": batch_id, "department": "production", "index": 1,
               "action": "release", "reason": "负责人确认日期为 2025-11-03",
               "fixes": [{"column": "date", "value": "2025-11-03",
                          "proposed_by": "captain", "evidence": "同行 sku 与其他行一致；03/11 为交接日"}],
               "confirmed_by": "captain", "call_id": "c1"}
    body = json.dumps(payload, ensure_ascii=False).encode()
    headers = {"content-type": "application/json"}
    assert client.post("/tools/quarantine-decide", content=body, headers=headers).status_code == 403, \
        "a proposal without approval must not land"
    headers["x-bridgeflow-approval"] = receipt(body)
    assert client.post("/tools/quarantine-decide", content=body, headers=headers).status_code == 200

    from bridgeflow import quarantine as dispositions
    decision = dispositions.ledger(batch_id).decisions[0]
    assert decision.fixes[0].proposed_by == "captain" and decision.fixes[0].evidence

    applied_body = json.dumps({"batch_id": batch_id, "confirmed_by": "captain", "call_id": "a1"},
                              separators=(",", ":")).encode()
    response = client.post("/tools/quarantine-apply", content=applied_body, headers={
        "content-type": "application/json", "x-bridgeflow-approval": receipt(applied_body)})
    assert response.status_code == 200, response.text
    from bridgeflow.api.batches import load_batch
    derived_snapshot = load_batch(response.json()["batch"]["batch_id"])
    assert derived_snapshot.dispositions[0]["fixes"][0]["proposed_by"] == "captain", \
        "attribution did not survive the derived batch"


def test_inbox_carries_corrections_as_aggregated_items(client):
    from bridgeflow.api.batches import load_batch
    from bridgeflow.monthly import inbox

    batch_id = a_bad_batch(client)
    batch = load_batch(batch_id)
    items = inbox._intake_corrections(inbox.Context(batch_id=batch_id, period=batch.period, batch=batch))
    assert items, "corrections did not reach the open-item inbox"
    assert {item.kind for item in items} == {"intake_correction"}
    assert all(item.next_view == "corrections" for item in items)
    columns = [item.subject for item in items]
    assert len(columns) == len(set(columns)), "items are not aggregated per column"
