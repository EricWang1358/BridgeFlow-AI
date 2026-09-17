"""Self-check before submission shares import's check chain (E14-UC03).

Uses the business side's v1 procurement template (a merged title row above the header) and the
fictional supplier's July "held-out" month, whose marketing sheet has text in a number column.
"""
import pytest
from fastapi.testclient import TestClient

from bridgeflow.api.batches import batch_path, load_batch
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
JULY = REPO_ROOT / "data/mock_business/monthly/2024-07-模拟留出"
LABELS = {"production": "生产部", "procurement": "物资部", "finance": "财务部", "marketing": "市场部"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "field_dictionary_path", str(REPO_ROOT / "data/mock_business/demo/dictionary.yaml"))
    with TestClient(app) as test_client:
        yield test_client


def self_check(client, department, path, name=None, **form):
    response = client.post("/batches/self-check", data={"period": "2024-07", "department": department, **form},
                           files={"file": (name or path.name, path.read_bytes(), XLSX)})
    assert response.status_code == 200, response.text
    return response.json()


def test_a_title_row_above_the_header_is_a_must_fix_with_the_likely_row(client):
    report = self_check(client, "procurement", REPO_ROOT / "data/company_templates/source/procurement-v1.xlsx")
    assert report["accepts"] is False
    [finding] = report["must_fix"]
    assert finding["check"] == "readable" and "row 1 is not a header" in finding["message"] and "row 2" in finding["message"]
    assert report["passed"] == []


def test_choosing_the_header_row_moves_on_to_the_declared_templates(client, tmp_path):
    import openpyxl
    book = openpyxl.load_workbook(REPO_ROOT / "data/company_templates/source/procurement-v1.xlsx")
    book.active.append([f"v{i}" for i in range(book.active.max_column)])  # the template itself has no data rows
    filled = tmp_path / "procurement-v1-filled.xlsx"
    book.save(filled)
    report = self_check(client, "procurement", filled, header_row="2")
    assert "readable" in report["passed"]
    assert any(f["check"] == "declaration:missing_column" for f in report["must_fix"])  # v1 lacks the v2 join keys


def test_text_in_a_number_column_is_located(client):
    report = self_check(client, "marketing", JULY / "市场部.xlsx")
    [finding] = [f for f in report["must_fix"] if f["check"] == "declaration:invalid_number"]
    assert finding["column"] == "市场_可争取" and "row" in finding["message"]
    cleaning = [f for f in report["must_fix"] if f["check"] == "cleaning"]
    assert [(f["row"], f["column"]) for f in cleaning] == [(2, "可争取")]  # the cleaner's own reason, not a guess
    assert "shifted header" in cleaning[0]["message"]


def test_a_clean_department_file_is_accepted(client):
    report = self_check(client, "finance", JULY / "财务部.xlsx")
    assert report["accepts"] is True and report["must_fix"] == []
    assert {"readable", "declaration"} <= set(report["passed"])


def test_self_check_and_import_report_the_same_findings_and_self_check_creates_no_batch(client):
    folder = batch_path("0" * 32).parent
    before = set(folder.glob("*.json")) if folder.exists() else set()
    reports = {d: self_check(client, d, JULY / f"{label}.xlsx", name=f"{label}.xlsx") for d, label in LABELS.items()}
    assert (set(folder.glob("*.json")) if folder.exists() else set()) == before
    files = [("files", (f"{label}.xlsx", (JULY / f"{label}.xlsx").read_bytes(), XLSX)) for label in LABELS.values()]
    batch = client.post("/batches", data={"period": "2024-07", "departments": list(LABELS)}, files=files)
    assert batch.status_code == 200, batch.text
    stored = load_batch(batch.json()["batch_id"]).intake_checks
    for department, report in reports.items():
        assert stored[department] == report, department
