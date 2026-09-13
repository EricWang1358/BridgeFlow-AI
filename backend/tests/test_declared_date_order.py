"""A slashed date is read the way the dictionary says the department writes it (#79)."""
import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient

from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

FRAME = pd.DataFrame({"date": ["03/11/2025", "13/11/2025", "2025-11-20"], "output_qty": [10, 20, 30]})


async def clean(order):
    return await DataSanitizerAgent().run(SanitizerInput("production", "2025-11", FRAME.copy(), order))


async def test_undeclared_order_keeps_the_ambiguous_date_quarantined():
    table = await clean(None)
    assert any(row["date"] == "03/11/2025" for row in table.quarantine)
    assert all(row["date"] != "2025-03-11" for row in table.rows)


async def test_day_first_declaration_reads_every_slashed_date_day_first():
    table = await clean("day_first")
    assert [row["date"] for row in table.rows] == ["2025-11-03", "2025-11-13", "2025-11-20"]
    assert not table.quarantine
    declared = [c for c in table.corrections if c.rule == "date_parse_declared"]
    assert {c.after for c in declared} == {"2025-11-03", "2025-11-13"} and all(c.confidence == 1.0 for c in declared)


async def test_a_value_that_contradicts_the_declaration_is_quarantined_not_read_the_other_way():
    table = await clean("month_first")
    assert [row["date"] for row in table.rows] == ["2025-03-11", "2025-11-20"]
    assert [row["date"] for row in table.quarantine] == ["13/11/2025"]
    [conflict] = [c for c in table.corrections if c.rule == "date_conflicts_declared_order"]
    assert conflict.after is None and conflict.confidence == 0.0


@pytest.fixture
def dictionary(tmp_path, monkeypatch):
    raw = yaml.safe_load((REPO_ROOT / "data/business_demo/dictionary.yaml").read_text(encoding="utf-8"))
    path = tmp_path / "dictionary.yaml"

    def write(order):
        path.write_text(yaml.safe_dump({**raw, "date_order": order}, allow_unicode=True), encoding="utf-8")
        monkeypatch.setattr(settings, "field_dictionary_path", str(path))
    return write


def upload(client, content):
    return client.post("/batches", data={"period": "2025-11", "departments": "production"},
                       files={"files": ("production.csv", content, "text/csv")})


def test_import_applies_the_declared_order_and_refuses_an_invalid_declaration(dictionary):
    content = "sku,date,output,used_hrs,available_hrs\nSKU-A1,03/11/2025,10,1,2\n"
    with TestClient(app) as client:
        dictionary({"production": "day_first"})
        batch = upload(client, content).json()
        assert batch["departments"][0] == {"department": "production", "rows": 1, "quarantined": 0, "corrections": batch["departments"][0]["corrections"]}
        dictionary({"production": "sideways"})
        assert upload(client, content).status_code == 503
