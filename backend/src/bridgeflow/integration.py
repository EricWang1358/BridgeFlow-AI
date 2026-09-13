"""Four department sheets into the 跨部门业务整合总表, exactly as the business dictionary says.

The business side supplied the standard templates, the dictionary (字典 v2) and the master
template on 2026-09-13. `data/company_templates/integration.yaml` transcribes the
dictionary: which department column feeds each master field, the join keys, the
formulas it states, and the one cross-department check it names. This module executes
that declaration and nothing else:

- **Rows meet on the declared grain** (项目编号, 客户代码, 报表年月). Names that the
  dictionary says must agree across departments are checked, never merged by similarity.
- **A formula the dictionary states is computed**, and if a department already filled
  that column, the two are compared. A disagreement is reported with both numbers; the
  cell is left empty rather than picking one.
- **What the dictionary does not state is not invented.** A formula needing an undeclared
  constant (the VAT rate) is refused with the constant's name; several rows for one key
  in one department are refused until a roll-up rule is declared.
- **Every cell says where it came from**: department, file, sheet, row and header, or the
  formula and the fields it used.

No business name is written in this code; all of them come from the declaration.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

import openpyxl
import yaml
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from bridgeflow import business
from bridgeflow.config import REPO_ROOT, settings


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceColumn(_Strict):
    column: str | None = None
    #: Which occurrence of a repeated header (1-based), for templates that repeat one label.
    occurrence: int = Field(1, ge=1)
    #: A period assembled from a year column and a month column, in that order.
    period_from: list[str] | None = None

    @model_validator(mode="after")
    def _one_kind(self) -> SourceColumn:
        if (self.column is None) == (self.period_from is None):
            raise ValueError("a source names either a column or period_from")
        return self


class FieldDecl(_Strict):
    type: Literal["string", "number"]
    sources: dict[str, SourceColumn]


class Check(_Strict):
    id: str
    title: str
    left: str
    right: str
    tolerance: float = 0


class DepartmentDecl(_Strict):
    label: str
    template: str


class IntegrationSpec(_Strict):
    version: str
    source_dictionary: str
    master_template: str
    departments: dict[str, DepartmentDecl]
    grain: list[str]
    agree: list[str] = Field(default_factory=list)
    constants: dict[str, float | None] = Field(default_factory=dict)
    fields: dict[str, FieldDecl]
    derived: dict[str, dict[str, Any]] = Field(default_factory=dict)
    checks: list[Check] = Field(default_factory=list)
    undeclared_rules: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _references(self) -> IntegrationSpec:
        problems = [f"grain field {g} is not declared" for g in self.grain if g not in self.fields]
        problems += [f"agree field {a} is not declared" for a in self.agree if a not in self.fields]
        for name, decl in self.fields.items():
            problems += [f"{name} names unknown department {d}" for d in decl.sources if d not in self.departments]
        for name, tree in self.derived.items():
            if name not in self.fields:
                problems.append(f"derived {name} is not a declared field")
            for key in _inputs(tree):
                if key not in self.fields:
                    problems.append(f"derived {name} uses undeclared field {key}")
            for key in _declared_constants(tree):
                if key not in self.constants:
                    problems.append(f"derived {name} uses constant {key} not listed in constants")
        for check in self.checks:
            problems += [f"check {check.id} uses undeclared field {f}" for f in (check.left, check.right) if f not in self.fields]
        if problems:
            raise ValueError("; ".join(problems))
        return self


def _walk(tree: Any):
    if isinstance(tree, dict):
        yield tree
        for child in tree.get("args", []):
            yield from _walk(child)


def _inputs(tree: dict) -> list[str]:
    return [node["key"] for node in _walk(tree) if node.get("op") == "input"]


def _declared_constants(tree: dict) -> list[str]:
    return [node["key"] for node in _walk(tree) if node.get("op") == "declared"]


def spec_path() -> Path:
    path = Path(settings.integration_spec_path)
    return path if path.is_absolute() else REPO_ROOT / path


def load_spec(path: Path | None = None) -> IntegrationSpec:
    target = path or spec_path()
    if not target.is_file():
        raise HTTPException(503, "Integration declaration is not configured")
    return IntegrationSpec.model_validate(yaml.safe_load(target.read_text(encoding="utf-8")))


# --- reading a department sheet ---------------------------------------------------------


@dataclass
class Sheet:
    department: str
    filename: str
    sheet: str
    header_row: int  # 1-based, as a person counts
    headers: list[str]
    rows: list[list[Any]]  # data rows only, in order
    #: The sheet row each data row came from, 1-based; blank rows in between are skipped.
    row_numbers: list[int] = field(default_factory=list)


def _clean(label: Any) -> str:
    # pandas renames a repeated header to `label.1`; the template's own spelling may carry
    # stray spaces. Neither is part of what the column means.
    return re.sub(r"\.\d+$", "", str(label or "").strip())


def read_sheet(department: str, filename: str, payload: bytes) -> Sheet:
    """The header row is the first row with more than one filled cell; a title row above it is skipped."""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(415, f"{filename}: use the department's XLSX template")
    workbook = openpyxl.load_workbook(io.BytesIO(payload), data_only=True, read_only=True)
    if len(workbook.worksheets) != 1:
        raise HTTPException(422, f"{filename}: multiple sheets require explicit selection")
    ws = workbook.worksheets[0]
    grid = [list(r) for r in ws.iter_rows(values_only=True)]
    header_index = next((i for i, r in enumerate(grid) if sum(c not in (None, "") for c in r) > 1), None)
    if header_index is None:
        raise HTTPException(422, f"{filename}: no header row")
    kept = [(i + 1, r) for i, r in enumerate(grid) if i > header_index and any(c not in (None, "") for c in r)]
    return Sheet(department, filename, ws.title, header_index + 1, [_clean(h) for h in grid[header_index]],
                 [r for _, r in kept], [n for n, _ in kept])


def sheet_from_preview(department: str, source: dict) -> Sheet:
    """A sheet from a batch's retained parsed original (header already in row 1)."""
    return Sheet(department, source.get("filename", ""), source.get("sheet", ""), 1,
                 [_clean(h) for h in source["columns"]], source["rows"], [i + 2 for i in range(len(source["rows"]))])


def _locate(sheet: Sheet, ref: SourceColumn) -> list[int] | None:
    labels = ref.period_from or [ref.column]
    found = []
    for label in labels:
        matches = [i for i, h in enumerate(sheet.headers) if h == _clean(label)]
        occurrence = ref.occurrence if ref.column else 1
        if len(matches) < occurrence:
            return None
        found.append(matches[occurrence - 1])
    return found


# --- integrating -------------------------------------------------------------------------


class Issue(BaseModel):
    kind: Literal["missing_department", "missing_column", "needs_rollup", "disagreement", "invalid_number",
                  "invalid_period", "undeclared_constant", "derived_mismatch", "check_failed", "cannot_compute",
                  "missing_key"]
    field: str = ""
    key: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)
    message: str


class MasterRow(BaseModel):
    key: list[str]
    values: dict[str, Any]
    provenance: dict[str, dict[str, Any]]
    complete: bool


class MasterResult(BaseModel):
    version: str
    columns: list[str]
    rows: list[MasterRow]
    issues: list[Issue]
    departments_read: dict[str, dict[str, Any]]


def _period(year: Any, month: Any) -> str | None:
    y = re.search(r"\d{4}", str(year or ""))
    m = re.search(r"\d{1,2}", str(month or "").replace(str(year or ""), "") if month is not None else "")
    if not y or not m or not 1 <= int(m.group()) <= 12:
        return None
    return f"{y.group()}-{int(m.group()):02d}"


def _number(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return Decimal(str(value))
    text = str(value).strip().replace(",", "")
    percent = text.endswith("%")
    try:
        number = Decimal(text.rstrip("%"))
    except InvalidOperation:
        return None
    return number / 100 if percent else number


def _plain(number: Decimal) -> int | float:
    return int(number) if number == number.to_integral_value() else float(number)


@dataclass
class _Contribution:
    sheet: Sheet
    row_number: int  # 1-based sheet row
    values: dict[str, Any] = field(default_factory=dict)


def integrate(spec: IntegrationSpec, sheets: list[Sheet]) -> MasterResult:
    issues: list[Issue] = []
    columns = list(spec.fields)
    by_department: dict[str, dict[tuple[str, ...], list[_Contribution]]] = {}
    read: dict[str, dict[str, Any]] = {}

    for sheet in sheets:
        if sheet.department not in spec.departments:
            raise HTTPException(422, f"Unknown department {sheet.department}")
        located: dict[str, list[int]] = {}
        missing = []
        for name, decl in spec.fields.items():
            ref = decl.sources.get(sheet.department)
            if ref is None:
                continue
            where = _locate(sheet, ref)
            if where is None:
                missing.append(f"{name}←{'+'.join(ref.period_from or [ref.column or ''])}")
            else:
                located[name] = where
        if missing:
            issues.append(Issue(kind="missing_column", departments=[sheet.department],
                                message=f"{spec.departments[sheet.department].label} template lacks: {', '.join(missing)}"))
        read[sheet.department] = {"filename": sheet.filename, "sheet": sheet.sheet, "header_row": sheet.header_row,
                                  "data_rows": len(sheet.rows), "missing_columns": len(missing)}
        groups: dict[tuple[str, ...], list[_Contribution]] = {}
        for offset, raw in enumerate(sheet.rows):
            number = sheet.row_numbers[offset] if offset < len(sheet.row_numbers) else sheet.header_row + 1 + offset
            contribution = _Contribution(sheet, number)
            for name, where in located.items():
                ref = spec.fields[name].sources[sheet.department]
                cells = [raw[i] if i < len(raw) else None for i in where]
                if ref.period_from:
                    value = _period(*cells)
                    if value is None and any(c not in (None, "") for c in cells):
                        issues.append(Issue(kind="invalid_period", field=name, departments=[sheet.department],
                                            message=f"{sheet.filename} row {contribution.row_number}: year and month do not form a period"))
                else:
                    value = cells[0]
                if value not in (None, ""):
                    contribution.values[name] = value
            key = tuple(str(contribution.values.get(g, "")).strip() for g in spec.grain
                        if spec.fields[g].sources.get(sheet.department))
            if not all(key) or len(key) != sum(1 for g in spec.grain if spec.fields[g].sources.get(sheet.department)):
                issues.append(Issue(kind="missing_key", departments=[sheet.department],
                                    message=f"{sheet.filename} row {contribution.row_number}: a grain field is empty; the row cannot be placed"))
                continue
            groups.setdefault(key, []).append(contribution)
        by_department[sheet.department] = groups

    keys = sorted({k for groups in by_department.values() for k in groups})
    rows: list[MasterRow] = []
    for key in keys:
        values: dict[str, Any] = dict.fromkeys(columns)
        provenance: dict[str, dict[str, Any]] = {}
        complete = True
        present = []
        for department, groups in by_department.items():
            group = groups.get(key)
            if not group:
                continue
            if len(group) > 1:
                complete = False
                issues.append(Issue(kind="needs_rollup", key=list(key), departments=[department],
                                    message=f"{spec.departments[department].label} has {len(group)} rows for this key and no roll-up rule is declared"))
                continue
            present.append(department)
            for name, value in group[0].values.items():
                decl = spec.fields[name]
                where = {"department": department, "file": group[0].sheet.filename, "sheet": group[0].sheet.sheet,
                         "row": group[0].row_number, "column": "+".join(decl.sources[department].period_from or [decl.sources[department].column or ""])}
                if decl.type == "number":
                    number = _number(value)
                    if number is None:
                        complete = False
                        issues.append(Issue(kind="invalid_number", field=name, key=list(key), departments=[department],
                                            message=f"{name}: {where['file']} row {where['row']} is not a number"))
                        continue
                    value = _plain(number)
                if values[name] is None:
                    values[name], provenance[name] = value, where
                elif str(values[name]).strip() != str(value).strip():
                    complete = False
                    issues.append(Issue(kind="disagreement", field=name, key=list(key),
                                        departments=[provenance[name]["department"], department],
                                        message=f"{name} differs between departments; confirm which is right"))
        absent = [d for d in spec.departments if d not in present]
        if absent:
            complete = False
            issues.append(Issue(kind="missing_department", key=list(key), departments=absent,
                                message="No row for this key from: " + ", ".join(spec.departments[d].label for d in absent)))

        for name, tree in spec.derived.items():
            outcome = _derive(spec, name, tree, values)
            supplied = values.get(name)
            if isinstance(outcome, Issue):
                # The formula cannot run. A value the department wrote is kept as written and
                # marked unverified; nothing is filled in where nobody wrote anything.
                outcome.key = list(key)
                issues.append(outcome)
                if supplied is not None:
                    provenance[name] = {**provenance[name], "verified_by_formula": False, "unverified_because": outcome.message}
                continue
            computed, formula_inputs = outcome
            if supplied is None:
                values[name] = computed
                provenance[name] = {"formula": name, "inputs": formula_inputs}
            elif abs(Decimal(str(supplied)) - Decimal(str(computed))) > Decimal("1e-6") * max(Decimal(1), abs(Decimal(str(computed)))):
                complete = False
                issues.append(Issue(kind="derived_mismatch", field=name, key=list(key), departments=[provenance[name]["department"]],
                                    message=f"{name}: department wrote {supplied}, the dictionary formula gives {computed}"))
                values[name] = None
                provenance[name] = {"conflict": {"supplied": supplied, "computed": computed}}
            else:
                provenance[name] = {**provenance[name], "verified_by_formula": True}

        for check in spec.checks:
            left, right = values.get(check.left), values.get(check.right)
            if left is None or right is None:
                continue
            if abs(Decimal(str(left)) - Decimal(str(right))) > Decimal(str(check.tolerance)):
                complete = False
                issues.append(Issue(kind="check_failed", field=check.left, key=list(key),
                                    message=f"{check.title}: {check.left}={left}, {check.right}={right}"))
        rows.append(MasterRow(key=list(key), values=values, provenance=provenance, complete=complete))

    return MasterResult(version=spec.version, columns=columns, rows=rows, issues=issues, departments_read=read)


def _derive(spec: IntegrationSpec, name: str, tree: dict, values: dict[str, Any]) -> tuple[int | float, list[str]] | Issue:
    for constant in _declared_constants(tree):
        if spec.constants.get(constant) is None:
            return Issue(kind="undeclared_constant", field=name,
                         message=f"{name} needs the undeclared constant 「{constant}」")
    resolved = _substitute(tree, spec.constants)
    needed = _inputs(tree)
    missing = [k for k in needed if values.get(k) is None]
    if missing:
        return Issue(kind="cannot_compute", field=name, message=f"{name} needs {', '.join(missing)}")
    inputs = {k: business.Value(Decimal(str(values[k])), [], 1) for k in needed}
    try:
        result = business.expression(resolved, None, inputs=inputs).number
    except HTTPException as exc:
        return Issue(kind="cannot_compute", field=name, message=f"{name}: {exc.detail}")
    return _plain(result), needed


def _substitute(tree: Any, constants: dict[str, float | None]) -> Any:
    if not isinstance(tree, dict):
        return tree
    if tree.get("op") == "declared":
        return {"op": "constant", "value": constants[tree["key"]]}
    return {**tree, **({"args": [_substitute(a, constants) for a in tree["args"]]} if "args" in tree else {})}


def to_xlsx(result: MasterResult) -> bytes:
    """The master template's columns, one row per key; issues on a second sheet."""
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "总表"
    sheet.append(result.columns)
    for row in result.rows:
        sheet.append([row.values.get(c) for c in result.columns])
    notes = book.create_sheet("待确认")
    notes.append(["类型", "字段", "键", "部门", "说明"])
    for issue in result.issues:
        notes.append([issue.kind, issue.field, " / ".join(issue.key), ", ".join(issue.departments), issue.message])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()
