"""Tool bodies for the Feishu shortcuts (#140). Both move files across a trust boundary,
so both require a fresh DSH approval bound to the request."""

from __future__ import annotations

import io
import json
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field, StringConstraints

from bridgeflow import feishu
from bridgeflow.api.batches import _check_upload_scope, _import_batch, _visible, load_batch
from bridgeflow.api.reviews import saved_review
from bridgeflow.config import settings
from bridgeflow.identity import UserIdentity, require_user
from bridgeflow.schemas import Department
from bridgeflow.security import consume_approval

router = APIRouter(prefix="/tools", tags=["feishu"])

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


class ImportRequest(BaseModel):
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    files: list[ImportFile] = Field(min_length=1, max_length=4)
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


@router.post("/feishu-import")
async def feishu_import(request: ImportRequest, http_request: Request) -> dict:
    """Download department files from Feishu Drive and import them as one batch."""
    consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body())
    return await _import_with(_client(), request)


async def _import_with(drive: feishu.FeishuDrive, request: ImportRequest,
                       user: UserIdentity | None = None) -> dict:
    uploads: list[UploadFile] = []
    try:
        for item in request.files:
            name, payload = await drive.download(item.file_token)
            uploads.append(UploadFile(io.BytesIO(payload), filename=name))
        summary = await _import_batch(request.period, [f.department for f in request.files], uploads,
                                      owner=user.sub if user else "")
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


@router.post("/feishu-upload-report")
async def feishu_upload_report(request: UploadRequest, http_request: Request) -> dict:
    """Upload a saved review report to a Feishu folder. The report is sent as saved."""
    consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body())
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
async def feishu_upload_user(request: UploadRequest, http_request: Request,
                             user: Annotated[UserIdentity | None, Depends(require_user)]) -> dict:
    """Upload a saved review report to the folder the signed-in user picked."""
    drive = _user_client(http_request)  # the token gate answers before anything exists
    _visible(load_batch(request.batch_id), user)
    report = saved_review(request.batch_id, request.report_id)
    filename = re.sub(r"[^A-Za-z0-9_.-]", "-", f"bridgeflow-review-{report['period']}-{report['report_id'][:8]}.json")
    try:
        token = await drive.upload(request.folder_token, filename,
                                   json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
    except feishu.FeishuError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        await drive.close()
    return {"file_token": token, "filename": filename, "report_id": report["report_id"], "status": report["status"]}
