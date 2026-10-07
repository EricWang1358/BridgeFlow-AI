"""Long-term memory (#303): saved only with approval, found by search, retired but never erased."""
import json

import pytest
from conftest import receipt
from fastapi.testclient import TestClient
from test_employee_approval import grants, native, permit
from test_identity import client as identity_client  # noqa: F401 -- pytest fixture re-export

from bridgeflow import memory
from bridgeflow.api.main import app
from bridgeflow.config import settings

FREIGHT = {"title": "采购单运费列混入单价", "problem": "供应商 A 的采购单把运费写在单价列，材料成本虚高",
           "solution": "导入前按备注列识别运费行，单独记入运费科目；与采购部王经理 9 月例会确认",
           "source": "2026-09 采购部例会纪要", "departments": ["procurement"], "tags": ["运费", "采购单"]}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def post(client, path, payload, approve=True):
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    headers = {"content-type": "application/json"}
    if approve:
        headers["x-bridgeflow-approval"] = receipt(body)
    return client.post(path, content=body, headers=headers)


def search(client, query, **extra):
    return client.post("/tools/memory-search", json={"query": query, **extra}).json()["memories"]


def test_a_memory_is_saved_only_with_approval_and_names_its_approver(client):
    assert post(client, "/tools/memory-save", FREIGHT, approve=False).status_code == 403
    assert memory.history() == []
    saved = post(client, "/tools/memory-save", FREIGHT | {"confirmed_by": "a-name-the-model-invented"})
    assert saved.status_code == 200
    body = saved.json()
    assert body["id"].startswith("mem-") and body["version"] == 1 and body["status"] == "active"
    # The actor is who the approval verified, never what the model wrote into the call.
    assert body["created_by"] == "dsh-authenticated-session"
    assert "memory_search" in body["next_step"]


def test_search_finds_chinese_and_latin_text_and_ranks_the_title_first(client):
    post(client, "/tools/memory-save", FREIGHT)
    post(client, "/tools/memory-save", {"title": "应收账款账龄口径", "problem": "财务和市场对账龄起算日不一致",
                                        "solution": "统一按发票日期起算，运费不计入应收", "source": "财务部书面说明",
                                        "departments": ["finance"]})
    found = search(client, "运费怎么处理")
    assert [m["title"] for m in found] == ["采购单运费列混入单价", "应收账款账龄口径"]
    assert found[0]["score"] > found[1]["score"]
    assert search(client, "SKU mismatch") == []
    post(client, "/tools/memory-save", FREIGHT | {"title": "SKU code mismatch between ERP and POS",
                                                  "tags": [], "departments": []})
    assert search(client, "sku")[0]["title"].startswith("SKU")
    # A department filter keeps that department's memories and the company-wide ones.
    assert {m["title"] for m in search(client, "运费", department="finance")} == {
        "应收账款账龄口径", "SKU code mismatch between ERP and POS"}


def test_a_revision_needs_the_version_it_was_read_at_and_keeps_the_history(client):
    first = post(client, "/tools/memory-save", FREIGHT).json()
    revise = FREIGHT | {"memory_id": first["id"], "solution": "改为在导入映射里把运费列单独声明", "note": "流程改了"}
    assert post(client, "/tools/memory-save", revise).status_code == 409  # no expected_version
    assert post(client, "/tools/memory-save", revise | {"expected_version": 0}).status_code == 409
    revised = post(client, "/tools/memory-save", revise | {"expected_version": 1}).json()
    assert revised["version"] == 2 and revised["created_at"] == first["created_at"]
    assert [r.action for r in memory.history()] == ["create", "revise"]
    assert memory.history()[0].content.solution == FREIGHT["solution"]
    assert post(client, "/tools/memory-save", FREIGHT | {"memory_id": "mem-missing", "expected_version": 1}).status_code == 404


def test_a_retired_memory_is_no_longer_found_but_stays_readable(client):
    saved = post(client, "/tools/memory-save", FREIGHT).json()
    assert post(client, "/tools/memory-retire", {"memory_id": saved["id"], "reason": "x"}, approve=False).status_code == 403
    assert post(client, "/tools/memory-retire", {"memory_id": saved["id"], "reason": "x", "expected_version": 3}).status_code == 409
    retired = post(client, "/tools/memory-retire", {"memory_id": saved["id"], "reason": "供应商已改用新模板"})
    assert retired.status_code == 200 and retired.json()["status"] == "retired"
    assert search(client, "运费") == []
    listed = client.get("/memories").json()
    assert listed == {"memories": [], "active": 0}
    every = client.get("/memories", params={"include_retired": True}).json()["memories"]
    assert every[0]["retired_reason"] == "供应商已改用新模板"
    assert post(client, "/tools/memory-retire", {"memory_id": saved["id"], "reason": "again"}).status_code == 409
    assert post(client, "/tools/memory-save", FREIGHT | {"memory_id": saved["id"], "expected_version": 2}).status_code == 409


@pytest.mark.parametrize("change", [
    {"departments": ["legal"]},
    {"title": ""},
    {"source": ""},
    {"tags": ["x" * 25]},
    {"solution": "按下表处理：\n客户\t金额\t账期\t备注\nA 公司\t12000\t30\t\nB 公司\t8000\t60\t\n"},
])
def test_what_a_memory_may_not_hold_is_refused(client, change):
    assert post(client, "/tools/memory-save", FREIGHT | change).status_code == 422
    assert memory.history() == []


def test_writes_follow_the_deployment_switch(client, monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_allow_workflow_write", False)
    assert post(client, "/tools/memory-save", FREIGHT).status_code == 403


def test_an_employee_files_memories_only_within_their_departments(identity_client):  # noqa: F811
    """ou_bob sits in production: company-wide and production memories yes, procurement no."""
    def body(payload):
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()

    company = body(FREIGHT | {"departments": []})
    assert permit(identity_client, company, operation="memory_save").status_code == 403  # no grant yet
    grants("ou_bob", ["memory_save", "memory_retire"])
    assert permit(identity_client, company, operation="memory_save").status_code == 200
    assert permit(identity_client, body(FREIGHT), operation="memory_save").status_code == 403
    production = body(FREIGHT | {"departments": ["production"]})
    proof = native(production, permit(identity_client, production, operation="memory_save").json()["permit"])
    saved = identity_client.post("/tools/memory-save", content=production,
                                 headers={"content-type": "application/json", "x-bridgeflow-approval": proof})
    assert saved.status_code == 200 and saved.json()["created_by"] == "ou_bob"
    # Another department's memory cannot be retired from outside it.
    other = memory.save(memory.Content(**FREIGHT), actor="ou_alice")
    retire = body({"memory_id": other.id, "reason": "过时"})
    assert permit(identity_client, retire, operation="memory_retire").status_code == 403
