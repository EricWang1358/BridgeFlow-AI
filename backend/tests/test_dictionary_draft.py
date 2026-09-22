"""The dictionary draft walk: transcribe or draft, decide entry by entry, publish (#205).

These tests walk what E05-UC07/UC08 promise, on the real endpoints with the mock LLM:
a batch frozen at `needs_configuration` because no dictionary exists, an OA dictionary
spreadsheet transcribed into a draft with evidence on every entry, a person deciding
each one (a measure only with its rollup named), a publish that writes a new version
and leaves the frozen batch alone, and a re-import that finally joins. The model-draft
road is exercised as plumbing — the mock provider proposes nothing, which is exactly
what AC-4 says mock output is worth.
"""
import io
import json
from pathlib import Path

import openpyxl
import pytest
import yaml
from conftest import receipt
from fastapi.testclient import TestClient

from bridgeflow import business, dictionary_draft
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

CASES = REPO_ROOT / "data/business_demo"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "field_dictionary_path", str(tmp_path / "field-dictionary.yaml"))
    monkeypatch.setattr(settings, "dictionary_draft_path", str(tmp_path / "dictionary-drafts"))
    with TestClient(app) as client:
        yield client


class _FakeDrive:
    def __init__(self, name: str, payload: bytes) -> None:
        self.name, self.payload = name, payload

    async def download(self, token: str) -> tuple[str, bytes]:
        return self.name, self.payload

    async def close(self) -> None:
        pass


def oa_workbook(rows: list[tuple]) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "字典"
    sheet.append(["字段名称", "关联部门", "数据类型", "详细含义与用途描述", "来源表字段", "变更说明"])
    for row in rows:
        sheet.append(list(row))
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


#: Mirrors `data/business_demo/dictionary.yaml`'s entity section so a published draft
#: makes the committed sample files join, without naming any customer column in code.
FULL_ROWS = [
    ("SKU", "公共主键", "String", "the product everything keys on",
     "production.sku / finance.project / marketing.product", "沿用"),
    ("Material", "公共主键（物资部）", "String", "the raw material",
     "procurement.material", "沿用"),
    ("Customer", "公共主键", "String", "the buyer",
     "marketing.customer", "沿用"),
    ("period", "公共主键", "String", "the report month",
     "finance.date / marketing.date", "新增"),
    ("output", "生产部", "Number", "units produced",
     "production.output", "沿用"),
]

THREE_DEPARTMENT_ROWS = [row for row in FULL_ROWS if "procurement." not in row[4]]

JOIN_GAP_ROWS = [
    ("SKU", "公共主键", "String", "the product everything keys on",
     "production.sku / marketing.product", "沿用"),
    ("sales", "财务部", "Number", "sales amount",
     "finance.sales", "沿用"),
]


def upload(client) -> dict:
    files = []
    for role in business.ROLES:
        files.append(("files", (f"{role}.csv", (CASES / "risk" / f"{role}.csv").read_bytes(), "text/csv")))
    response = client.post("/batches", data={"period": "2025-11", "departments": list(business.ROLES)}, files=files)
    assert response.status_code == 200, response.text
    return response.json()


def import_oa(client, monkeypatch, rows) -> dict:
    from bridgeflow.api import dictionary_tools

    monkeypatch.setattr(dictionary_tools, "_client",
                        lambda: _FakeDrive("字典.xlsx", oa_workbook(rows)))
    body = json.dumps({"file_token": "tok-123456", "confirmed_by": "captain", "call_id": "c1"},
                      separators=(",", ":")).encode()
    response = client.post("/tools/dictionary-import", content=body, headers={
        "content-type": "application/json", "x-bridgeflow-approval": receipt(body)})
    assert response.status_code == 200, response.text
    return response.json()


def decide(client, draft_id: str, entry_id: str, decision: str = "accepted", **fields) -> object:
    payload = {"draft_id": draft_id, "entry_id": entry_id, "decision": decision, "reason": "",
               "confirmed_by": "captain", "call_id": "c1", **fields}
    body = json.dumps(payload, separators=(",", ":")).encode()
    return client.post("/tools/dictionary-draft-decide", content=body, headers={
        "content-type": "application/json", "x-bridgeflow-approval": receipt(body)})


def publish(client, draft_id: str):
    body = json.dumps({"draft_id": draft_id, "confirmed_by": "captain", "call_id": "c9"},
                      separators=(",", ":")).encode()
    return client.post("/tools/dictionary-draft-publish", content=body, headers={
        "content-type": "application/json", "x-bridgeflow-approval": receipt(body)})


def decide_all(client, draft_id: str, entries: list[dict], **overrides) -> None:
    for entry in entries:
        fields = dict(overrides.get(entry["entry_id"], {}))
        decision = fields.pop("decision", "accepted")
        response = decide(client, draft_id, entry["entry_id"], decision=decision, **fields)
        assert response.status_code == 200, response.text


def active_dictionary() -> dict:
    raw = yaml.safe_load(open(settings.field_dictionary_path, encoding="utf-8").read())
    return raw or {}


# --- the walk ----------------------------------------------------------------------


def test_profiles_of_a_frozen_batch_carry_no_cell_contents(client):
    batch = upload(client)
    assert batch["status"] == "needs_configuration"
    assert batch["refusal"]

    response = client.post("/tools/dictionary-profiles", json={"batch_id": batch["batch_id"]})
    assert response.status_code == 200
    text = response.text
    rows = (CASES / "risk" / "finance.csv").read_text(encoding="utf-8").splitlines()[1:]
    for cell in {c for line in rows for c in line.split(",") if len(c) > 3}:
        assert cell not in text, f"cell value {cell!r} leaked into the profiling payload"
    departments = {column["department"] for column in response.json()["columns"]}
    assert departments == set(business.ROLES)


def test_the_oa_transcription_carries_evidence_and_marks_the_absent_department(client, monkeypatch):
    result = import_oa(client, monkeypatch, THREE_DEPARTMENT_ROWS)
    assert result["departments"] == ["finance", "marketing", "production"]
    assert result["missing_departments"] == ["procurement"]
    assert any("procurement" in note for note in result["notes"])

    view = client.post("/tools/dictionary-draft-view", json={"draft_id": result["draft_id"]}).json()
    assert view["entries"], "the transcription produced no entries"
    for entry in view["entries"]:
        assert entry["evidence"], f"entry {entry['entry_id']} has no evidence"
        assert entry["decision"] == "pending"
    assert all(not entry["department"] == "procurement" for entry in view["entries"]), \
        "a declaration was invented for a department that never uploaded"
    assert result["pending"] == len(view["entries"])


def test_publish_is_blocked_until_every_entry_has_a_decision(client, monkeypatch):
    draft = import_oa(client, monkeypatch, FULL_ROWS)
    response = publish(client, draft["draft_id"])
    assert response.status_code == 409
    assert f"{draft['entries']} entry(ies) still undecided" in response.json()["detail"]


def test_a_measure_cannot_be_decided_without_its_rollup(client, monkeypatch):
    draft = import_oa(client, monkeypatch, FULL_ROWS)
    view = client.post("/tools/dictionary-draft-view", json={"draft_id": draft["draft_id"]}).json()
    measure = next(entry for entry in view["entries"] if entry["role"].startswith("measure:"))

    refused = decide(client, draft["draft_id"], measure["entry_id"])
    assert refused.status_code == 409
    assert "rollup" in refused.json()["detail"]

    accepted = decide(client, draft["draft_id"], measure["entry_id"], rollup="sum")
    assert accepted.status_code == 200


def test_publish_writes_a_version_the_rejected_stay_out_and_the_frozen_batch_stays(client, monkeypatch):
    frozen = upload(client)
    assert frozen["status"] == "needs_configuration"

    draft = import_oa(client, monkeypatch, FULL_ROWS)
    view = client.post("/tools/dictionary-draft-view", json={"draft_id": draft["draft_id"]}).json()
    entries = view["entries"]
    rejected = next(entry for entry in entries if entry["column"] == "customer")
    measure = next(entry for entry in entries if entry["role"].startswith("measure:"))
    period = next(entry for entry in entries if entry["column"] == "date" and entry["department"] == "marketing")
    finance_date = next(entry for entry in entries if entry["column"] == "date" and entry["department"] == "finance")
    decided = {rejected["entry_id"]: {"decision": "rejected", "reason": "not a join key for this client"},
               finance_date["entry_id"]: {"decision": "rejected", "reason": "the batch period already says the month"},
               measure["entry_id"]: {"rollup": "sum"},
               period["entry_id"]: {"decision": "modified", "role": "period"}}
    decide_all(client, draft["draft_id"], entries, **decided)

    response = publish(client, draft["draft_id"])
    assert response.status_code == 200, response.text
    published = yaml.safe_load(open(settings.field_dictionary_path, encoding="utf-8").read())

    columns = published["columns"]
    assert columns["production"]["sku"] == "sku"
    assert columns["finance"]["project"] == "sku"
    assert columns["procurement"]["material"] == "material"
    assert "customer" not in columns.get("marketing", {}), "a rejected entry reached the dictionary"
    assert published["measures"]["production"]["output"] == "output"
    assert published["rollups"]["output"] == "sum"
    assert published["period_columns"]["marketing"] == "date"

    versions = dictionary_draft.Path(settings.field_dictionary_path).parent / "versions"
    written = list(versions.glob("field-dictionary--*.yaml"))
    assert written, "no dictionary version was archived"

    after = client.get(f"/batches/{frozen['batch_id']}").json()
    assert after["status"] == "needs_configuration"
    assert after["declared_entities"] == frozen["declared_entities"] == {}

    reimported = upload(client)
    assert reimported["status"] != "needs_configuration", reimported["refusal"]
    assert reimported["master_rows"] > 0
    assert reimported["declared_entities"]["finance"] == ["project"]


def test_a_department_with_only_measures_cannot_publish(client, monkeypatch):
    draft = import_oa(client, monkeypatch, JOIN_GAP_ROWS)
    view = client.post("/tools/dictionary-draft-view", json={"draft_id": draft["draft_id"]}).json()
    decide_all(client, draft["draft_id"], view["entries"],
               **{e["entry_id"]: {"rollup": "sum"} for e in view["entries"] if e["role"].startswith("measure:")})
    response = publish(client, draft["draft_id"])
    assert response.status_code == 409
    assert "No column is declared as a joinable entity for: finance" in response.json()["detail"]
    assert not dictionary_draft.Path(settings.field_dictionary_path).exists(), "a refused publish wrote anyway"


def test_publish_refuses_when_the_dictionary_moved_under_the_draft(client, monkeypatch):
    draft = import_oa(client, monkeypatch, FULL_ROWS)
    view = client.post("/tools/dictionary-draft-view", json={"draft_id": draft["draft_id"]}).json()
    decide_all(client, draft["draft_id"], view["entries"],
               **{e["entry_id"]: {"rollup": "sum"} for e in view["entries"] if e["role"].startswith("measure:")})
    dictionary_draft._write_text(dictionary_draft.Path(settings.field_dictionary_path),
                                 yaml.safe_dump({"columns": {"production": {"sku": "sku"}}}))
    response = publish(client, draft["draft_id"])
    assert response.status_code == 409
    assert "changed since this draft" in response.json()["detail"]


# --- the model-drafted road ----------------------------------------------------------


def test_admit_proposals_drops_what_it_cannot_stand_behind():
    departments = {"finance": ["project", "sales"], "marketing": ["product", "customer"]}
    proposals = [
        {"department": "finance", "column": "Project", "role": "entity:sku",
         "evidence": "string; 100% overlap with marketing.product"},
        {"department": "finance", "column": "ghost", "role": "entity:sku", "evidence": "not there"},
        {"department": "finance", "column": "sales", "role": "entity:sku", "evidence": ""},
        {"department": "finance", "column": "sales", "role": "wat", "evidence": "unparseable role"},
        {"department": "logistics", "column": "project", "role": "entity:sku", "evidence": "not a department here"},
        {"department": "finance", "column": "PROJECT", "role": "measure:amount", "evidence": "duplicate after cleaning"},
        {"department": "finance", "column": "sales", "role": "measure:amount",
         "evidence": "numeric; folds by sum"},
    ]
    admitted, dropped = dictionary_draft.admit_proposals(proposals, departments)
    assert [entry.entry_id for entry in admitted] == [
        "finance::project::entity:sku", "finance::sales::measure:amount"]
    assert len(dropped) == 5


def test_model_drafting_records_the_billed_call_and_honest_notes(client):
    batch = upload(client)
    body = json.dumps({"batch_id": batch["batch_id"], "confirmed_by": "captain", "call_id": "c2"},
                      separators=(",", ":")).encode()
    response = client.post("/tools/dictionary-draft", content=body, headers={
        "content-type": "application/json", "x-bridgeflow-approval": receipt(body)})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["source"] == "model"
    assert result["model_call"]["provider"] == "mock", "the call was not recorded"
    assert result["model_call"]["started_at"] and result["model_call"]["finished_at"]
    if result["entries"] == 0:
        assert any("evidence check" in note or "Dropped" in note for note in result["notes"]), \
            "an empty mock draft must say so rather than look decided"


def test_drafting_without_uploads_is_refused(client):
    body = json.dumps({"batch_id": "0" * 32, "confirmed_by": "captain", "call_id": "c3"},
                      separators=(",", ":")).encode()
    response = client.post("/tools/dictionary-draft", content=body, headers={
        "content-type": "application/json", "x-bridgeflow-approval": receipt(body)})
    assert response.status_code == 404
