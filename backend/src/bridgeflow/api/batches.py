"""Immutable uploaded batches. Row-bearing views are browser-only, never tools."""

from __future__ import annotations

import io
import re
import uuid
import zipfile
from typing import Annotated

import pandas as pd
import yaml
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import FieldDictionary, SemanticResolverAgent
from bridgeflow.agents.sop_flow import MissingRollup, SOPFlowEngine, SOPInput, UnjoinableTables
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.metrics import dictionary_path
from bridgeflow.schemas import Department, PipelineResult
from bridgeflow.store import _root, _write

router = APIRouter(prefix="/batches", tags=["batches"])


def batch_path(batch_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", batch_id):
        raise HTTPException(422, "Invalid batch id")
    return _root() / "batches" / f"{batch_id}.json"


class BatchSnapshot(PipelineResult):
    dictionary_snapshot: dict | None = None
    refusal: str = ""


def load_batch(batch_id: str) -> BatchSnapshot:
    path = batch_path(batch_id)
    if not path.is_file():
        raise HTTPException(404, "Batch not found")
    return BatchSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def batch_dictionary(batch: BatchSnapshot) -> FieldDictionary:
    if batch.dictionary_snapshot is None:
        raise HTTPException(409, "Batch has no dictionary snapshot; import a new batch")
    return FieldDictionary(batch.dictionary_snapshot)


class BatchRef(BaseModel):
    batch_id: str


class DepartmentSummary(BaseModel):
    department: str
    rows: int
    quarantined: int
    corrections: int


class BatchSummary(BaseModel):
    batch_id: str
    period: str
    departments: list[DepartmentSummary]
    master_rows: int
    unresolved: int
    status: str
    refusal: str = ""
    #: The dictionary this batch was frozen against, and what it declares as a
    #: joinable entity per department.
    #:
    #: A refusal names the department that has no joinable column, which is the right
    #: half of the answer and useless on its own: somebody staring at
    #: `needs_configuration` cannot tell whether the dictionary is wrong or whether
    #: they are simply pointed at a different dictionary than they think. Measured on
    #: `data/business_demo/risk`: its finance sheet declares `project`, the default
    #: dictionary declares `gl_account`, and nothing on screen said which file was in
    #: force — so the walkthrough's step 1 passed and step 2 was impossible.
    dictionary: str = ""
    declared_entities: dict[str, list[str]] = Field(default_factory=dict)


def _declared_entities(snapshot: dict | None) -> dict[str, list[str]]:
    """Which columns each department declares as an entity, straight from the snapshot.

    Column names only — never a value out of anybody's sheet. This is what the
    dictionary says, not what the data holds.
    """
    columns = (snapshot or {}).get("columns") or {}
    if not isinstance(columns, dict):
        return {}
    return {
        str(department): sorted(str(name) for name in declared)
        for department, declared in columns.items()
        if isinstance(declared, dict) and declared
    }


def summary(batch_id: str, result: BatchSnapshot) -> BatchSummary:
    return BatchSummary(
        batch_id=batch_id, period=result.period,
        departments=[DepartmentSummary(
            department=t.department, rows=len(t.rows), quarantined=len(t.quarantine),
            corrections=len(t.corrections),
        ) for t in result.clean_tables],
        master_rows=len(result.master_table.rows) if result.master_table else 0,
        unresolved=len(result.graph.unresolved) if result.graph else 0,
        status=("needs_configuration" if result.refusal else "needs_review"
                if result.graph.unresolved or any(t.quarantine for t in result.clean_tables)
                else "ready" if result.master_table.rows else "empty"),
        refusal=result.refusal,
        dictionary=_relative_dictionary(),
        declared_entities=_declared_entities(result.dictionary_snapshot),
    )


def _relative_dictionary() -> str:
    """The dictionary path as somebody would type it, not as the process sees it."""
    path = dictionary_path()
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


@router.post("", response_model=BatchSummary)
async def upload_batch(
    period: Annotated[str, Form(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
    departments: Annotated[list[Department], Form()],
    files: Annotated[list[UploadFile], File()],
) -> BatchSummary:
    if len(files) != len(departments) or not 1 <= len(files) <= 4:
        raise HTTPException(422, "Provide one file per department (1–4 departments)")
    if len(set(departments)) != len(departments):
        raise HTTPException(422, "Duplicate department; combine its sheets explicitly first")
    batch_id = uuid.uuid4().hex
    path = dictionary_path()
    try:
        dictionary_raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
        if dictionary_raw is None:
            dictionary_raw = {}
        if not isinstance(dictionary_raw, dict):
            raise TypeError("Dictionary root must be a mapping")
        dictionary = FieldDictionary(dictionary_raw)
    except (yaml.YAMLError, OSError, UnicodeError, ValueError, TypeError, AttributeError, KeyError) as exc:
        raise HTTPException(503, "Field dictionary configuration is invalid; ask the administrator to correct it before importing") from exc
    tables = []
    byte_count = row_count = 0
    for department, upload in zip(departments, files, strict=True):
        payload = await upload.read(settings.bridgeflow_max_upload_bytes + 1)
        byte_count += len(payload)
        if byte_count > settings.bridgeflow_max_upload_bytes:
            raise HTTPException(413, "Batch exceeds configured upload size limit")
        filename = (upload.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
        sheet = ""
        try:
            if filename.lower().endswith(".xlsx"):
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    if sum(i.file_size for i in archive.infolist()) > 100 * 1024 * 1024:
                        raise HTTPException(413, "Expanded workbook exceeds 100 MiB")
                with pd.ExcelFile(io.BytesIO(payload)) as workbook:
                    if len(workbook.sheet_names) != 1:
                        raise HTTPException(422, "Multiple sheets require explicit sheet selection")
                    sheet = workbook.sheet_names[0]
                    frame = workbook.parse(sheet, nrows=settings.bridgeflow_max_batch_rows + 1)
            elif filename.lower().endswith(".csv"):
                frame = pd.read_csv(io.BytesIO(payload), skip_blank_lines=False, nrows=settings.bridgeflow_max_batch_rows + 1)
            else:
                raise HTTPException(415, "Use CSV or a single-sheet XLSX workbook")
        except HTTPException:
            raise
        except (ValueError, OSError, zipfile.BadZipFile, UnicodeError) as exc:
            raise HTTPException(422, f"Cannot parse {filename}") from exc
        row_count += len(frame)
        if row_count > settings.bridgeflow_max_batch_rows:
            raise HTTPException(413, "Batch exceeds configured row limit")
        if frame.empty:
            raise HTTPException(422, f"{filename} has no data rows")
        table = await DataSanitizerAgent().run(SanitizerInput(department, period, frame))
        table.filename, table.sheet, table.batch = filename, sheet, batch_id
        for correction in table.corrections:
            correction.source.filename = filename
            correction.source.sheet = sheet
            correction.source.batch = batch_id
            correction.source.source_row = correction.row + 2
        tables.append(table)
    result = BatchSnapshot(period=period, clean_tables=tables, dictionary_snapshot=dictionary_raw or {})
    if dictionary.is_empty:
        result.refusal = "Field dictionary is not configured; declare fields and import a new batch"
    else:
        result.graph = await SemanticResolverAgent().run(tables, adjudicate=False, dictionary=dictionary)
        try:
            assembled = await SOPFlowEngine().run(
                SOPInput(period=period, tables=tables, graph=result.graph), dictionary=dictionary,
            )
            result.master_table = assembled.master_table
        except (UnjoinableTables, MissingRollup) as exc:
            result.refusal = str(exc)
    _write(batch_path(batch_id), result.model_dump(mode="json"))
    return summary(batch_id, result)


@router.get("/{batch_id}", response_model=BatchSummary)
async def get_summary(batch_id: str) -> BatchSummary:
    return summary(batch_id, load_batch(batch_id))


@router.get("/{batch_id}/view")
async def view(
    batch_id: str, section: str = "master", offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> dict:
    result = load_batch(batch_id)
    if section == "master":
        rows = result.master_table.rows if result.master_table else []
    elif section == "mappings":
        rows = [x.model_dump() for x in result.graph.unresolved] if result.graph else []
    elif section == "corrections":
        rows = [c.model_dump() for t in result.clean_tables for c in t.corrections]
    elif section == "quarantine":
        rows = [{"department": t.department, "values": row}
                for t in result.clean_tables for row in t.quarantine]
    else:
        raise HTTPException(422, "Unknown batch view")
    return {"batch_id": batch_id, "total": len(rows), "offset": offset,
            "rows": rows[offset:offset + limit]}


@router.get("/{batch_id}/review")
async def review(batch_id: str, report_id: str | None = None) -> dict:
    from bridgeflow.api.reviews import saved_review
    return saved_review(batch_id, report_id)
