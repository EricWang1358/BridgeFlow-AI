"""Tool bodies for the Feishu shortcuts (#140). Both move files across a trust boundary,
so both require a fresh DSH approval bound to the request."""

from __future__ import annotations

import io
import json
import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field, StringConstraints

from bridgeflow import feishu
from bridgeflow.api.batches import _import_batch, load_batch
from bridgeflow.api.reviews import saved_review
from bridgeflow.schemas import Department
from bridgeflow.security import consume_approval

router = APIRouter(prefix="/tools", tags=["feishu"])

Token = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{6,64}$")]

#: Swapped in tests; production builds the client from the shell's credentials.
client_factory = feishu.from_settings


def _client() -> feishu.FeishuDrive:
    try:
        return client_factory()
    except feishu.NotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc


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
    drive = _client()
    uploads: list[UploadFile] = []
    try:
        for item in request.files:
            name, payload = await drive.download(item.file_token)
            uploads.append(UploadFile(io.BytesIO(payload), filename=name))
        summary = await _import_batch(request.period, [f.department for f in request.files], uploads)
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
