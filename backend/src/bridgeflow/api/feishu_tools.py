"""Tool bodies for the Feishu shortcuts (#140). Both move files across a trust boundary,
so both require a fresh DSH approval bound to the request."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field, StringConstraints, model_validator

from bridgeflow import feishu, feishu_tabular
from bridgeflow.api.batches import _check_upload_scope, _import_batch, _visible, load_batch
from bridgeflow.api.reviews import saved_review
from bridgeflow.config import settings
from bridgeflow.identity import UserIdentity, require_user
from bridgeflow.schemas import Department
from bridgeflow.security import consume_approval


def _not_in_guest_mode() -> None:
    """A guest instance never reaches Feishu, and says so rather than "not configured"."""
    if settings.bridgeflow_guest_mode:
        raise HTTPException(403, "Feishu is not available in guest mode")


router = APIRouter(prefix="/tools", tags=["feishu"], dependencies=[Depends(_not_in_guest_mode)])

Token = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{6,64}$")]

#: Swapped in tests; production builds the client from the shell's credentials.
client_factory = feishu.from_settings
#: Swapped in tests; production builds a user-identity client from the header token.
user_client_factory = lambda token: feishu.FeishuDrive.for_user(token, settings.feishu_base_url)


def _client() -> feishu.FeishuDrive:
    try:
        return client_factory()
    except feishu.NotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc


def _user_client(http_request: Request) -> feishu.FeishuDrive:
    """User-identity client (docs/30). The token rides this one request's header;
    it is never cached, logged, or shown to the model."""
    token = http_request.headers.get("x-feishu-user-token", "").strip()
    try:
        return user_client_factory(token)
    except feishu.NotConfigured as exc:
        raise HTTPException(401, str(exc)) from exc


class ImportFile(BaseModel):
    department: Department
    file_token: Token
    #: What file_token addresses (docs/33): a Drive file, an online sheet, or a bitable.
    kind: Literal["file", "sheet", "bitable"] = "file"
    sheet_id: Token | None = None
    table_id: Token | None = None
    header_row: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def _kind_fields(self) -> ImportFile:
        # Each kind declares its addressing exactly; a missing piece is a 422, never a guess.
        if self.kind == "file" and (self.sheet_id or self.table_id or self.header_row):
            raise ValueError("kind=file takes no sheet_id, table_id or header_row")
        if self.kind == "sheet" and (not self.sheet_id or not self.header_row or self.table_id):
            raise ValueError("kind=sheet needs sheet_id and header_row, and no table_id")
        if self.kind == "bitable" and (not self.table_id or self.sheet_id or self.header_row):
            raise ValueError("kind=bitable needs table_id only")
        return self


class ImportRequest(BaseModel):
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    files: list[ImportFile] = Field(min_length=1, max_length=4)
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/feishu-import")
async def feishu_import(request: ImportRequest, http_request: Request) -> dict:
    """Download department files from Feishu Drive and import them as one batch."""
    if not settings.bridgeflow_allow_workflow_write:
        raise HTTPException(403, "Workflow writes disabled by deployment policy")
    if any(f.kind != "file" for f in request.files):
        # Sheets and bitables are read as the signed-in user only (docs/33, decision 4):
        # the tenant identity is never pointed at people's documents.
        raise HTTPException(422, "Sheets and bitables import through the user endpoint only")
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body(), "feishu_import")
    return await _import_with(_client(), request, actor=actor)


async def _import_with(drive: feishu.FeishuDrive, request: ImportRequest,
                       user: UserIdentity | None = None, actor: str = "") -> dict:
    uploads: list[UploadFile] = []
    dropped: list[dict] = []
    try:
        for item in request.files:
            if item.kind == "sheet":
                name, payload, _ = await feishu_tabular.materialize_sheet(
                    drive, item.file_token, item.sheet_id or "", item.header_row or 1)
            elif item.kind == "bitable":
                name, payload, dropped_columns = await feishu_tabular.materialize_bitable(
                    drive, item.file_token, item.table_id or "")
                dropped += [{"department": item.department, **d} for d in dropped_columns]
            else:
                name, payload = await drive.download(item.file_token)
            uploads.append(UploadFile(io.BytesIO(payload), filename=name))
        # Owner: the signed-in user for browser imports; the verified approver in portal mode.
        owner = user.sub if user else (actor if settings.portal_base_url else "")
        summary = await _import_batch(request.period, [f.department for f in request.files], uploads,
                                      owner=owner, dropped_columns=dropped,
                                      # A materialized sheet's CSV starts at its header, but row
                                      # numbers in provenance map back to the original sheet.
                                      source_header_rows=[f.header_row if f.kind == "sheet" else None
                                                          for f in request.files])
    except feishu.FeishuError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        for upload in uploads:
            await upload.close()
        await drive.close()
    return {"batch": summary.model_dump(), "source": "feishu",
            "files": [{"department": f.department, "file_token": f.file_token} for f in request.files]}


class UploadRequest(BaseModel):
    batch_id: str
    folder_token: Token
    report_id: str | None = Field(None, pattern=r"^[a-f0-9]{32}$")
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


class UserUploadRequest(BaseModel):
    """Browser upload target (docs/30 + 31): exactly one of a Drive folder or a wiki position."""
    batch_id: str
    folder_token: Token | None = None
    wiki_space_id: str | None = Field(None, max_length=64)
    parent_wiki_token: Token | None = None
    report_id: str | None = Field(None, pattern=r"^[a-f0-9]{32}$")

    @model_validator(mode="after")
    def _one_target(self) -> UserUploadRequest:
        # A wiki target needs the space; an empty parent means the space's top level.
        if (self.folder_token is not None) == (self.wiki_space_id is not None):
            raise ValueError("pick exactly one target: folder_token or wiki_space_id")
        return self


@router.post("/feishu-upload-report")
async def feishu_upload_report(request: UploadRequest, http_request: Request) -> dict:
    """Upload a saved review report to a Feishu folder. The report is sent as saved."""
    if not settings.bridgeflow_allow_workflow_write:
        raise HTTPException(403, "Workflow writes disabled by deployment policy")
    consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body(), "feishu_upload_report")
    load_batch(request.batch_id)
    report = saved_review(request.batch_id, request.report_id)
    filename = re.sub(r"[^A-Za-z0-9_.-]", "-", f"bridgeflow-review-{report['period']}-{report['report_id'][:8]}.json")
    drive = _client()
    try:
        token = await drive.upload(request.folder_token, filename,
                                   json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
    except feishu.FeishuError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        await drive.close()
    return {"file_token": token, "filename": filename, "report_id": report["report_id"], "status": report["status"]}


# --- User-identity endpoints (docs/30) -------------------------------------------------
# Browser-only: a person's click plus the portal session plus their own Feishu token IS
# the approval (same tier as the /batches browser upload), so these are never registered
# as model tools and never consult consume_approval. The model-facing tenant-token
# endpoints above stay approval-gated.


class ListRequest(BaseModel):
    folder_token: str = Field("", max_length=64)
    page_token: str = Field("", max_length=256)
    page_size: int = Field(50, ge=1, le=200)


@router.post("/feishu-list")
async def feishu_list(request: ListRequest, http_request: Request) -> dict:
    """List one Drive folder as the signed-in user. Metadata only, paged, capped."""
    drive = _user_client(http_request)
    try:
        return await drive.list_files(request.folder_token, request.page_token, request.page_size)
    except feishu.FeishuError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        await drive.close()


@router.post("/feishu-import-user")
async def feishu_import_user(request: ImportRequest, http_request: Request,
                             user: Annotated[UserIdentity | None, Depends(require_user)]) -> dict:
    """Download the files the signed-in user picked and import them as one batch."""
    _check_upload_scope([f.department for f in request.files], user)
    return await _import_with(_user_client(http_request), request, user)


@router.post("/feishu-upload-user")
async def feishu_upload_user(request: UserUploadRequest, http_request: Request,
                             user: Annotated[UserIdentity | None, Depends(require_user)]) -> dict:
    """Upload a saved review report where the signed-in user picked: a Drive folder, or a
    wiki position (docs/31 — land in the Drive root, then attach)."""
    drive = _user_client(http_request)  # the token gate answers before anything exists
    try:
        _visible(load_batch(request.batch_id), user)
        report = saved_review(request.batch_id, request.report_id)
        filename = re.sub(r"[^A-Za-z0-9_.-]", "-", f"bridgeflow-review-{report['period']}-{report['report_id'][:8]}.json")
        payload = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
        if request.wiki_space_id:
            wiki_token = await drive.upload_to_wiki(request.wiki_space_id, request.parent_wiki_token or "",
                                                    filename, payload)
            return {"file_token": "", "wiki_token": wiki_token, "filename": filename,
                    "report_id": report["report_id"], "status": report["status"]}
        token = await drive.upload(request.folder_token or "", filename, payload)
    except feishu.FeishuError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        await drive.close()
    return {"file_token": token, "filename": filename, "report_id": report["report_id"], "status": report["status"]}


# --- Wiki endpoints (docs/31) ----------------------------------------------------------
# Same browser-only contract as the docs/30 endpoints above: the click is the approval,
# the token rides the header, and every answer is metadata only, paged and capped.


class WikiSpacesRequest(BaseModel):
    page_token: str = Field("", max_length=256)


class WikiListRequest(BaseModel):
    space_id: str = Field(min_length=1, max_length=64)
    parent_node_token: str = Field("", max_length=64)
    page_token: str = Field("", max_length=256)
    page_size: int = Field(50, ge=1, le=50)


@router.post("/feishu-wiki-spaces")
async def feishu_wiki_spaces(request: WikiSpacesRequest, http_request: Request) -> dict:
    """List the knowledge bases the signed-in user may see. Metadata only."""
    drive = _user_client(http_request)
    try:
        return await drive.list_wiki_spaces(request.page_token)
    except feishu.FeishuError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        await drive.close()


@router.post("/feishu-wiki-list")
async def feishu_wiki_list(request: WikiListRequest, http_request: Request) -> dict:
    """List one level of a wiki's node tree. Metadata only, paged, capped."""
    drive = _user_client(http_request)
    try:
        return await drive.list_wiki_nodes(request.space_id, request.parent_node_token,
                                           request.page_token, request.page_size)
    except feishu.FeishuError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        await drive.close()


@router.post("/feishu-wiki-upload")
async def feishu_wiki_upload(http_request: Request, file: UploadFile,
                             space_id: Annotated[str, Form(max_length=64)],
                             parent_wiki_token: Annotated[str, Form(max_length=64)] = "") -> dict:
    """Upload a local file into a wiki position the signed-in user picked (docs/31)."""
    drive = _user_client(http_request)  # the token gate answers before the body is read
    try:
        payload = await file.read(feishu.MAX_FILE_BYTES + 1)  # one byte past the cap says "too big"
        if len(payload) > feishu.MAX_FILE_BYTES:
            raise HTTPException(413, "Upload exceeds the size limit")
        filename = Path(file.filename or "upload").name  # strip any client-side path
        wiki_token = await drive.upload_to_wiki(space_id, parent_wiki_token, filename, payload)
    except feishu.FeishuError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        await drive.close()
    return {"wiki_token": wiki_token, "name": filename}


# --- Sheet & bitable reads (docs/33) ---------------------------------------------------
# Same browser-only contract as the docs/30/31 endpoints: the click is the approval and
# the token rides the header. The meta endpoints answer names, dimensions and field
# definitions only — a cell or record value never crosses into a response.


def _meta_error(exc: feishu.FeishuError) -> HTTPException:
    """A user-side authorization refusal (Feishu 403) stays a 403 with Feishu's own
    code/msg (docs/32 FR-7); anything else is upstream trouble and maps to 502."""
    return HTTPException(403 if exc.status == 403 else 502, str(exc))


class SheetMetaRequest(BaseModel):
    token: Token


@router.post("/feishu-sheet-meta")
async def feishu_sheet_meta(request: SheetMetaRequest, http_request: Request) -> dict:
    """Worksheets of one online sheet, for the second-level pick: id, title, dimensions."""
    drive = _user_client(http_request)
    try:
        return {"sheets": await drive.sheet_meta(request.token)}
    except feishu.FeishuError as exc:
        raise _meta_error(exc) from exc
    finally:
        await drive.close()


class BitableMetaRequest(BaseModel):
    """Tables of one bitable; with table_id, that table's field definitions instead."""
    token: Token
    table_id: Token | None = None


@router.post("/feishu-bitable-meta")
async def feishu_bitable_meta(request: BitableMetaRequest, http_request: Request) -> dict:
    drive = _user_client(http_request)
    try:
        if request.table_id:
            fields = await drive.bitable_fields(request.token, request.table_id)
            return {"table_id": request.table_id,
                    "fields": [{"name": f["name"], "ui_type": f["ui_type"]} for f in fields]}
        return {"tables": await drive.bitable_tables(request.token)}
    except feishu.FeishuError as exc:
        raise _meta_error(exc) from exc
    finally:
        await drive.close()
