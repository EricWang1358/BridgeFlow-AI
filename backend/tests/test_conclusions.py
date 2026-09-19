"""The one-page monthly brief and evidence grades (E13-UC01, E13-UC06).

Built on the sample notebook's case (data/mock_business/demo), whose dictionary declares the
brief: five key metrics, a severity order for attention items and which metrics rest on an
unconfirmed convention. Reviews are finalized with scripted judgements, as in
test_business_mvp; nothing here calls a model.
"""
import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bridgeflow.api.main import app
from bridgeflow.conclusions import brief as brief_module
from bridgeflow.conclusions import grades
from bridgeflow.config import REPO_ROOT


def judgement(packet):
    return {"checks": [{"check_id": c["check_id"], "metric": c["metric"], "value": c["value"], "unit": c["unit"],
                        "status": c["expected_status"], "action": c["actions"][c["expected_status"]][0],
                        "explanation": "应按本部门权限核实并提交责任人复核。"} for c in packet["checks"]]}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def finalize(client, batch_id, fail=None):
    packets = client.post("/tools/review-context", json={"batch_id": batch_id}).json()["roles"]
    runs = [{"role": p["role"], "session_id": f"child-{p['role']}", "status": "completed", "judgement": judgement(p)} for p in packets]
    for run in runs:
        if run["role"] == fail:
            run.update(status="max-tokens", judgement=None)
    return client.post("/tools/review-finalize", json={"batch_id": batch_id, "parent_session_id": "parent", "runs": runs}).json()


@pytest.fixture
def batch(client):
    return client.post("/batches/demo").json()["batch_id"]


def test_without_a_saved_review_the_brief_is_refused(client, batch):
    response = client.get(f"/conclusions/batches/{batch}")
    assert response.status_code == 409 and "Complete the review" in response.text


def test_attention_items_follow_the_declared_severity_with_owner_and_grade(client, batch):
    report = finalize(client, batch)
    brief = client.get(f"/conclusions/batches/{batch}").json()
    assert brief["report_status"] == "validated" and brief["missing_departments"] == [] and brief["stale"] is False
    assert [a["check_id"] for a in brief["attention"]] == ["net_margin", "collection_gap", "material_cost"]
    assert all(a["decision_owner"] and a["action"] for a in brief["attention"])
    assert [m["metric"] for m in brief["key_metrics"]] == ["net_margin", "material_cost_ratio", "settlement_collection_rate",
                                                         "receivable_months", "sign_rate"]
    grade = {a["check_id"]: a["grade"]["grade"] for a in brief["attention"]}
    assert grade == {"net_margin": "G2", "collection_gap": "G3", "material_cost": "G2"}
    assert {a["advice_grade"]["grade"] for a in brief["attention"]} == {"G4"}
    assert "G3 市场_缺口" in next(a for a in brief["attention"] if a["check_id"] == "collection_gap")["grade"]["chain"]
    assert brief["headline"] == {"attention": 3, "ok": 7, "open_items": brief["open_items"]["total"], "missing_departments": 0}
    assert brief["open_items"]["master_issues"] == 1  # the customer-name disagreement
    assert brief["bound"]["report_id"] == report["report_id"] and brief["bound"]["batch_id"] == batch


def test_a_partial_review_names_the_missing_department_and_excludes_its_metrics(client, batch):
    finalize(client, batch, fail="finance")
    brief = client.get(f"/conclusions/batches/{batch}").json()
    assert brief["report_status"] == "partial" and brief["missing_departments"] == ["finance"]
    assert {"net_margin", "receivable_months"}.isdisjoint(m["metric"] for m in brief["key_metrics"])
    assert "net_margin" not in [a["check_id"] for a in brief["attention"]]
    assert brief["headline"]["missing_departments"] == 1


def test_a_newer_report_marks_the_older_brief_stale(client, batch):
    first = finalize(client, batch)
    second = finalize(client, batch)
    old = client.get(f"/conclusions/batches/{batch}?report_id={first['report_id']}").json()
    assert old["stale"] is True and old["latest_report_id"] == second["report_id"]
    assert client.get(f"/conclusions/batches/{batch}").json()["stale"] is False


def test_building_the_brief_calls_no_model(client, batch, monkeypatch):
    finalize(client, batch)
    import bridgeflow.agents.base as agent_base
    from bridgeflow import llm
    from bridgeflow.agents import evaluator
    from bridgeflow.llm import registry

    def refuse(*_args, **_kwargs):
        raise AssertionError("the brief must not call a model")
    for module in (registry, llm, agent_base, evaluator):
        monkeypatch.setattr(module, "get_provider", refuse)
    assert client.get(f"/conclusions/batches/{batch}").status_code == 200


def test_a_contract_without_a_brief_declaration_is_refused():
    with pytest.raises(Exception) as refused:
        brief_module.declaration({"business_review": {"case": "no brief"}})
    assert refused.value.status_code == 409


def test_master_view_grades_every_cell_and_reports_the_withheld_one(client, batch):
    master = client.get(f"/integration/batches/{batch}").json()
    assert master["grade_summary"]["missing"] == 1  # the customer name departments wrote differently
    rows = {tuple(r["key"]): i for i, r in enumerate(master["rows"])}
    graded = master["grades"][rows[next(k for k in rows if k[0] == "PRJ2024017")]]
    assert graded["客户名称"]["grade"] is None and graded["客户名称"]["missing"]
    margin = master["grades"][0]["物资_单方不含税毛利"]
    assert margin["grade"] == "G3" and margin["chain"][0] == "G3 增值税税率"
    assert master["grades"][0]["项目名称"]["grade"] == "G1"  # identical across daily rows: no convention


def test_the_weakest_node_decides_and_a_missing_source_leaves_no_grade():
    grader = grades.EvidenceGrader()
    formula = grades.FormulaNode("margin", (grades.SourceCell("a"), grades.ConventionNode("vat", grades.SourceCell("b"))))
    assert grader.grade(formula).grade == grades.Grade.CONVENTION
    confirmed = grades.FormulaNode("margin", (grades.SourceCell("a"), grades.ConventionNode("vat", grades.SourceCell("b"), confirmed=True)))
    assert grader.grade(confirmed).grade == grades.Grade.FORMULA
    assert grader.grade(grades.JudgementNode((formula,))).grade == grades.Grade.JUDGEMENT
    broken = grader.grade(grades.FormulaNode("margin", (grades.SourceCell("a"), grades.MissingSource("b: no source"))))
    assert broken.grade is None and broken.missing == ["b: no source"]


def test_no_business_name_is_written_into_the_conclusions_code():
    import yaml
    dictionary = yaml.safe_load((REPO_ROOT / "data/mock_business/demo/dictionary.yaml").read_text(encoding="utf-8"))
    declared = dictionary["business_review"]["brief"]
    names = [*declared["key_metrics"], *declared["severity"], *[k for v in declared["conventions"].values() for k in v]]
    for path in (Path(grades.__file__), Path(brief_module.__file__)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef) and ast.get_docstring(node) is not None:
                node.body = node.body[1:] or [ast.Pass()]
        code = ast.unparse(tree)
        for name in names:
            assert name not in code, (path.name, name)


def test_an_attention_item_cites_where_its_figure_came_from(client, batch):
    """E13-UC01: a reader can go from the item to the cells behind it, by reference (round 11)."""
    finalize(client, batch)
    brief = client.get(f"/conclusions/batches/{batch}").json()
    item = brief["attention"][0]
    assert item["source_count"] > 0 and 0 < len(item["sources"]) <= 5
    first = item["sources"][0]
    assert first["department"] in {"production", "procurement", "finance", "marketing"}
    assert first.get("filename") and (first.get("row") is not None or first.get("source_row") is not None)
    # References only: no cell value travels with the citation.
    assert "value" not in first


def test_the_brief_is_listed_as_a_derived_artifact_of_its_report(client, batch):
    """E13-UC01: management opens it from the artifacts list; it is not a second copy (round 11)."""
    report = finalize(client, batch)
    artifacts = client.get(f"/batches/{batch}/artifacts").json()["artifacts"]
    kinds = {a["kind"] for a in artifacts if a["report_id"] == report["report_id"]}
    assert kinds == {"review", "brief"}
    brief = next(a for a in artifacts if a["kind"] == "brief")
    assert brief["report_id"] == report["report_id"] and brief["period"] == "2024-07"
