"""The business side's templates and dictionary (2026-09-13) drive the master table.

The golden case is theirs: the worked example row in `master-v2.xlsx`, split back into
the four department templates by `scripts/make_template_example.py`. Every other test
changes one thing in those sheets and checks the system refuses to guess.
"""
import ast
import io
from pathlib import Path

import openpyxl

from bridgeflow import integration
from bridgeflow.config import REPO_ROOT

BASE = REPO_ROOT / "data" / "company_templates"
SPEC = integration.load_spec(BASE / "integration.yaml")


def workbook_bytes(department: str, edit=None, extra_rows=0) -> bytes:
    book = openpyxl.load_workbook(BASE / "example" / f"{department}.xlsx")
    sheet = book.active
    if edit:
        edit(sheet)
    for _ in range(extra_rows):
        sheet.append([c.value for c in sheet[2]])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def column(sheet, label, occurrence=1):
    matches = [c.column_letter for c in sheet[1] if str(c.value or "").strip() == label]
    return matches[occurrence - 1]


def sheets(**changes):
    result = []
    for department in SPEC.departments:
        if changes.get(department) == "absent":
            continue
        edit, extra = changes.get(department, (None, 0))
        result.append(integration.read_sheet(department, f"{department}.xlsx", workbook_bytes(department, edit, extra)))
    return result


def expected_row():
    master = openpyxl.load_workbook(BASE / SPEC.master_template).active
    return dict(zip([c.value for c in master[1]], [c.value for c in master[2]], strict=True))


def kinds(result):
    return sorted({i.kind for i in result.issues})


# --- the declaration is a faithful transcription ---------------------------------------


def test_declared_fields_are_the_dictionary_and_the_master_template_in_order():
    dictionary = openpyxl.load_workbook(BASE / SPEC.source_dictionary).active
    names = [r[0] for r in dictionary.iter_rows(min_row=2, values_only=True) if r[0]]
    master = [c.value for c in openpyxl.load_workbook(BASE / SPEC.master_template).active[1]]
    assert list(SPEC.fields) == names == master


def test_every_declared_source_column_exists_in_its_department_template():
    for department, decl in SPEC.departments.items():
        headers = [str(c.value or "").strip() for c in openpyxl.load_workbook(BASE / decl.template).active[1]]
        for name, field in SPEC.fields.items():
            ref = field.sources.get(department)
            if ref is None:
                continue
            for label in ref.period_from or [ref.column]:
                count = headers.count(label)
                assert count >= (ref.occurrence if ref.column else 1), f"{department}: {name} → {label} not in template"


# --- golden case --------------------------------------------------------------------------


def test_the_business_example_is_reproduced_column_for_column():
    result = integration.integrate(SPEC, sheets())
    [row] = result.rows
    assert row.values == expected_row()
    assert row.complete
    assert kinds(result) == ["undeclared_constant"]  # the VAT rate is not in the dictionary
    assert row.provenance["生产_实际签收率"]["verified_by_formula"] is True
    assert row.provenance["物资_单方不含税毛利"]["verified_by_formula"] is False
    assert row.provenance["客户名称"]["column"] in {"客户名称", "客户单位"}


def test_once_the_vat_rate_is_declared_the_margin_is_verified():
    declared = SPEC.model_copy(update={"constants": {"增值税税率": 0.13}})
    result = integration.integrate(declared, sheets())
    assert result.issues == []
    assert result.rows[0].provenance["物资_单方不含税毛利"]["verified_by_formula"] is True


# --- refusing to guess -------------------------------------------------------------------


def test_a_department_figure_that_contradicts_its_formula_is_withheld_with_both_numbers():
    def wrong_rate(sheet):
        sheet[f"{column(sheet, '实际签收率')}2"] = 0.5
    result = integration.integrate(SPEC, sheets(production=(wrong_rate, 0)))
    [mismatch] = [i for i in result.issues if i.kind == "derived_mismatch"]
    assert mismatch.field == "生产_实际签收率" and "0.5" in mismatch.message
    assert result.rows[0].values["生产_实际签收率"] is None and not result.rows[0].complete


def test_the_declared_cross_department_check_catches_different_volumes():
    def other_volume(sheet):
        sheet[f"{column(sheet, '当月生产量')}2"] = 4000
    result = integration.integrate(SPEC, sheets(procurement=(other_volume, 0)))
    assert "check_failed" in kinds(result)


def test_names_that_must_agree_are_checked_not_merged():
    def renamed(sheet):
        sheet[f"{column(sheet, '项目名称')}2"] = "项目B"
    result = integration.integrate(SPEC, sheets(marketing=(renamed, 0)))
    [issue] = [i for i in result.issues if i.kind == "disagreement"]
    assert issue.field == "项目名称"


def test_a_missing_department_leaves_a_partial_row_that_says_so():
    result = integration.integrate(SPEC, sheets(finance="absent"))
    assert result.rows[0].complete is False
    [issue] = [i for i in result.issues if i.kind == "missing_department"]
    assert issue.departments == ["finance"]
    assert result.rows[0].values["财务_期初金额"] is None


def test_several_rows_for_one_key_need_a_declared_rollup():
    result = integration.integrate(SPEC, sheets(production=(None, 1)))
    assert "needs_rollup" in kinds(result)
    assert result.rows[0].values["生产_生产量"] is None


def test_the_v1_templates_lack_the_join_keys_the_dictionary_added_in_v2():
    """字典 v2 upgraded 项目编号/客户代码 to keys for all four departments; v1 sheets cannot be placed."""
    v1 = [integration.read_sheet(d, f"{d}-v1.xlsx", (BASE / "source" / f"{d}-v1.xlsx").read_bytes()) for d in SPEC.departments]
    result = integration.integrate(SPEC, v1)
    assert result.rows == []
    assert {i.departments[0] for i in result.issues if i.kind == "missing_column"} == set(SPEC.departments)
    procurement = result.departments_read["procurement"]
    assert procurement["header_row"] == 2  # the v1 sheet has a merged title row above its header


def test_the_master_workbook_keeps_template_columns_and_lists_open_items():
    result = integration.integrate(SPEC, sheets())
    book = openpyxl.load_workbook(io.BytesIO(integration.to_xlsx(result)))
    assert [c.value for c in book["总表"][1]] == list(SPEC.fields)
    assert book["待确认"].max_row == 1 + len(result.issues)


def test_the_example_generator_is_reproducible(tmp_path):
    import subprocess
    import sys
    before = {p.name: p.read_bytes() for p in (BASE / "example").glob("*.xlsx")}
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "make_template_example.py")], check=True, capture_output=True)
    after = {p.name: openpyxl.load_workbook(BASE / "example" / p.name).active for p in (BASE / "example").glob("*.xlsx")}
    for name, sheet in after.items():
        original = openpyxl.load_workbook(io.BytesIO(before[name])).active
        assert [[c.value for c in r] for r in sheet.iter_rows()] == [[c.value for c in r] for r in original.iter_rows()]


def test_no_business_name_is_written_into_the_integration_code():
    tree = ast.parse(Path(integration.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        holder = isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        if holder and ast.get_docstring(node) is not None:
            node.body = node.body[1:] or [ast.Pass()]
    code = ast.unparse(tree)
    for name in [*SPEC.fields, *SPEC.constants]:
        assert name not in code, name


def test_an_imported_batch_of_the_templates_produces_the_master_table_over_http(monkeypatch):
    import base64

    from fastapi.testclient import TestClient

    from bridgeflow.api.main import app
    from bridgeflow.config import settings
    monkeypatch.setattr(settings, "field_dictionary_path", str(REPO_ROOT / "data/business_demo/dictionary.yaml"))
    with TestClient(app) as client:
        files = [("files", (f"{d}.xlsx", (BASE / "example" / f"{d}.xlsx").read_bytes(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")) for d in SPEC.departments]
        batch = client.post("/batches", data={"period": "2024-05", "departments": list(SPEC.departments)}, files=files)
        assert batch.status_code == 200, batch.text
        batch_id = batch.json()["batch_id"]
        view = client.get(f"/integration/batches/{batch_id}").json()
        assert view["rows"][0]["values"] == expected_row()
        summary = client.post("/tools/integration-summary", json={"batch_id": batch_id}).json()
        assert (summary["rows"], summary["complete_rows"], summary["issues_by_kind"]) == (1, 1, {"undeclared_constant": 1})
        assert "项目A" not in str(summary) and "1485000" not in str(summary)
        workbook = client.get(f"/integration/batches/{batch_id}/xlsx").json()
        book = openpyxl.load_workbook(io.BytesIO(base64.b64decode(workbook["base64"])))
        assert [c.value for c in book["总表"][2]] == list(expected_row().values())
