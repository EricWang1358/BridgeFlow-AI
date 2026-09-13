"""The sample notebook is the fictional concrete supplier on the business side's v2 templates.

It must come out the way `data/mock_business/README.md` describes: four projects in one month
(not filed under their completion dates, not merged by similar codes), a declared review whose
checks are a mix of ok and attention, and a cross-department table with one open item.
"""
import pytest
from fastapi.testclient import TestClient

from bridgeflow.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_the_sample_notebook_is_the_v2_template_case(client):
    batch = client.post("/batches/demo")
    assert batch.status_code == 200, batch.text
    summary = batch.json()
    assert (summary["period"], summary["status"], summary["master_rows"], summary["demo_case"]) == ("2024-07", "ready", 4, "mock-company-2024-07")
    batch_id = summary["batch_id"]

    context = client.post("/tools/review-context", json={"batch_id": batch_id}).json()
    status = {c["check_id"]: c["expected_status"] for role in context["roles"] for c in role["checks"]}
    assert {k for k, v in status.items() if v == "attention"} == {"material_cost", "net_margin", "collection_gap"}
    assert len(status) == 10

    master = client.get(f"/integration/batches/{batch_id}").json()
    assert len(master["rows"]) == 4
    assert [(i["kind"], i["field"]) for i in master["issues"]] == [("disagreement", "客户名称")]


def test_undeclared_several_dates_do_not_pick_the_first_as_the_month():
    from bridgeflow.agents.semantic_resolver import FieldDictionary
    from bridgeflow.agents.sop_flow import _period_column
    from bridgeflow.schemas import CleanTable, ColumnSpec

    def table(*dates):
        return CleanTable(department="marketing", period="2024-07",
                          columns=[ColumnSpec(name=d, dtype="date") for d in dates], rows=[])
    assert _period_column(table("完工时间", "报表年月"), FieldDictionary({})) is None
    assert _period_column(table("报表年月"), FieldDictionary({})) == "报表年月"
    assert _period_column(table("完工时间", "报表年月"), FieldDictionary({"period_columns": {"marketing": "报表年月"}})) == "报表年月"
