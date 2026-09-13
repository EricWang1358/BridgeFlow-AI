"""Immutable uploaded batches. Row-bearing views are browser-only, never tools."""

from __future__ import annotations

import hashlib
import io
import json
import re
import uuid
import zipfile
from pathlib import Path
from typing import Annotated

import pandas as pd
import yaml
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from bridgeflow import column_matches
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import FieldDictionary, SemanticResolverAgent
from bridgeflow.agents.sop_flow import MissingRollup, SOPFlowEngine, SOPInput, UnjoinableTables
from bridgeflow.column_matches import AppliedMatch
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
    demo_case: str | None = None
    dictionary_source: str | None = None
    #: Uploaded columns renamed onto declared columns at import, from human decisions.
    column_matches: list[AppliedMatch] = Field(default_factory=list)
    #: Decisions not applied because the uploaded column's shape changed.
    stale_matches: list[str] = Field(default_factory=list)


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
    demo_case: str | None = None
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
    #: `department.column → declared column`, applied from remembered decisions.
    matched_columns: list[str] = Field(default_factory=list)
    stale_matches: list[str] = Field(default_factory=list)
    #: Uploaded columns the dictionary does not know that might be a declared column
    #: this department is missing. Non-zero means the captain has something to propose.
    column_questions: int = 0


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
        demo_case=result.demo_case,
        dictionary=result.dictionary_source or _relative_dictionary(),
        declared_entities=_declared_entities(result.dictionary_snapshot),
        matched_columns=[f"{m.department}.{m.column} → {m.target}" for m in result.column_matches],
        stale_matches=result.stale_matches,
        column_questions=column_matches.count_questions(result.dictionary_snapshot, result.clean_tables),
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
    return await _import_batch(period, departments, files)


@router.post("/demo", response_model=BatchSummary)
async def demo_batch() -> BatchSummary:
    """Explicit synthetic notebook; freeze its dictionary without replacing deployment policy."""
    folder = REPO_ROOT / "data/business_demo"
    departments: list[Department] = ["production", "procurement", "finance", "marketing"]
    files = [UploadFile(io.BytesIO((folder / "risk" / f"{department}.csv").read_bytes()),
                        filename=f"sample-{department}.csv") for department in departments]
    try:
        return await _import_batch("2025-11", departments, files, folder / "dictionary.yaml", "risk")
    finally:
        for upload in files:
            await upload.close()


async def _import_batch(period: str, departments: list[Department], files: list[UploadFile],
                        source_dictionary: Path | None = None, demo_case: str | None = None) -> BatchSummary:
    if len(files) != len(departments) or not 1 <= len(files) <= 4:
        raise HTTPException(422, "Provide one file per department (1–4 departments)")
    if len(set(departments)) != len(departments):
        raise HTTPException(422, "Duplicate department; combine its sheets explicitly first")
    batch_id = uuid.uuid4().hex
    path = source_dictionary or dictionary_path()
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
    sources = []
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
        # Browser-only originals live outside the model-readable batch snapshot.
        # Capture before sanitation mutates values; this is a parsed table preview.
        parsed = json.loads(frame.to_json(orient="split", date_format="iso"))
        sources.append({"id": department, "filename": filename, "sheet": sheet,
                        "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload),
                        "columns": parsed["columns"], "rows": parsed["data"]})
        table = await DataSanitizerAgent().run(SanitizerInput(department, period, frame))
        table.filename, table.sheet, table.batch = filename, sheet, batch_id
        for correction in table.corrections:
            correction.source.filename = filename
            correction.source.sheet = sheet
            correction.source.batch = batch_id
            correction.source.source_row = correction.row + 2
        tables.append(table)
    result = BatchSnapshot(period=period, clean_tables=tables, dictionary_snapshot=dictionary_raw or {})
    if not dictionary.is_empty:
        # Before anything reads the tables: a remembered match makes this upload look
        # the way the dictionary already describes it. Frozen batches are never redone.
        result.column_matches, result.stale_matches = column_matches.apply(tables, dictionary_raw)
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
    result.demo_case = demo_case
    result.dictionary_source = str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)
    manifest = [{key: source[key] for key in ("id", "filename", "sheet", "sha256", "bytes")}
                | {"total": len(source["rows"])} for source in sources]
    _write(batch_path(batch_id).parent / "sources" / batch_id / "index.json", {"sources": manifest})
    for source in sources:
        _write(batch_path(batch_id).parent / "sources" / batch_id / f"{source['id']}.json", source)
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


@router.get("/{batch_id}/review-notes/{report_id}")
async def review_notes(batch_id: str, report_id: str) -> dict:
    load_batch(batch_id)
    from bridgeflow.api.reviews import review_notes as notes
    return notes(batch_id, report_id)


@router.get("/{batch_id}/sources")
async def list_sources(batch_id: str) -> dict:
    batch = load_batch(batch_id)
    sources = []
    folder = batch_path(batch_id).parent / "sources" / batch_id
    manifest_path = folder / "index.json"
    manifest = {item["id"]: item for item in json.loads(manifest_path.read_text(encoding="utf-8"))["sources"]} if manifest_path.is_file() else {}
    for table in batch.clean_tables:
        path = batch_path(batch_id).parent / "sources" / batch_id / f"{table.department}.json"
        if path.is_file() and table.department in manifest:
            sources.append(manifest[table.department] | {"preview_available": True})
        else:
            # Older batches have no retained original. Never substitute cleaned rows.
            sources.append({"id": table.department, "filename": table.filename,
                            "sheet": table.sheet, "preview_available": False})
    return {"batch_id": batch_id, "sources": sources}


@router.get("/{batch_id}/sources/{source_id}")
async def source_preview(batch_id: str, source_id: Department,
                         offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)) -> dict:
    batch = load_batch(batch_id)
    if source_id not in {table.department for table in batch.clean_tables}:
        raise HTTPException(404, "Source not found in this batch")
    path = batch_path(batch_id).parent / "sources" / batch_id / f"{source_id}.json"
    if not path.is_file():
        raise HTTPException(404, "Original preview was not retained for this batch; import a new batch")
    source = json.loads(path.read_text(encoding="utf-8"))
    rows = source.pop("rows")
    return {**source, "batch_id": batch_id, "total": len(rows), "offset": offset,
            "rows": rows[offset:offset + limit]}


@router.get("/{batch_id}/artifacts")
async def list_artifacts(batch_id: str, offset: int = Query(0, ge=0),
                         limit: int = Query(50, ge=1, le=100)) -> dict:
    load_batch(batch_id)
    folder = batch_path(batch_id).parent / "reviews" / batch_id
    paths = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    artifacts = []
    for path in paths[offset:offset + limit]:
        report = json.loads(path.read_text(encoding="utf-8"))
        artifacts.append({key: report[key] for key in
                          ("report_id", "batch_id", "period", "status", "parent_session_id")}
                         | {"created_at": path.stat().st_mtime})
    return {"batch_id": batch_id, "total": len(paths), "offset": offset, "artifacts": artifacts}
