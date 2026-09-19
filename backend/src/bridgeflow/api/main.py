from __future__ import annotations

import io
from typing import Annotated

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from bridgeflow import __version__, store
from bridgeflow.api.approvals import router as approvals_router
from bridgeflow.api.batches import router as batches_router
from bridgeflow.api.checklist import router as checklist_router
from bridgeflow.api.conclusions import router as conclusions_router
from bridgeflow.api.conventions import router as conventions_router
from bridgeflow.api.discovery import router as discovery_router
from bridgeflow.api.discovery import tools_router as discovery_tools_router
from bridgeflow.api.dispositions import router as dispositions_router
from bridgeflow.api.documents import router as documents_router
from bridgeflow.api.feishu_tools import router as feishu_tools_router
from bridgeflow.api.integration import router as integration_router
from bridgeflow.api.quarantine_tools import router as quarantine_tools_router
from bridgeflow.api.reviews import router as reviews_router
from bridgeflow.api.tools import router as tools_router
from bridgeflow.api.workflow import router as workflow_router
from bridgeflow.api.workflow_tools import router as workflow_tools_router
from bridgeflow.api.write_identity import router as write_identity_router
from bridgeflow.config import settings
from bridgeflow.pipeline import Orchestrator
from bridgeflow.schemas import Department, PipelineResult, QuoteRecommendation, QuoteRequest
from bridgeflow.security import require_host

app = FastAPI(title="BridgeFlow AI", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The dsh tools call in here for the work their TypeScript declarations describe.
# See plugins/README.md for why the two halves live where they do.
app.include_router(write_identity_router, dependencies=[Depends(require_host)])
app.include_router(tools_router, dependencies=[Depends(require_host)])
app.include_router(batches_router, dependencies=[Depends(require_host)])
app.include_router(reviews_router, dependencies=[Depends(require_host)])
app.include_router(documents_router, dependencies=[Depends(require_host)])

# The escalation checkpoint (#30): where a pending decision is published, and where
# a person answers it. Without this the approval seam is fail-closed and unanswerable
# — correct for an unattended run, and not a human in the loop.
app.include_router(approvals_router, dependencies=[Depends(require_host)])
app.include_router(workflow_router, dependencies=[Depends(require_host)])
app.include_router(discovery_router, dependencies=[Depends(require_host)])
app.include_router(discovery_tools_router, dependencies=[Depends(require_host)])
app.include_router(workflow_tools_router, dependencies=[Depends(require_host)])
app.include_router(quarantine_tools_router, dependencies=[Depends(require_host)])
app.include_router(feishu_tools_router, dependencies=[Depends(require_host)])
app.include_router(integration_router, dependencies=[Depends(require_host)])
app.include_router(conclusions_router, dependencies=[Depends(require_host)])
app.include_router(conventions_router, dependencies=[Depends(require_host)])
app.include_router(checklist_router, dependencies=[Depends(require_host)])
app.include_router(dispositions_router, dependencies=[Depends(require_host)])

orchestrator = Orchestrator()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "llm_provider": settings.llm_provider}


@app.post("/analyze", response_model=PipelineResult, dependencies=[Depends(require_host)])
async def analyze(
    period: Annotated[str, Form()],
    departments: Annotated[list[Department], Form()],
    files: Annotated[list[UploadFile], File()],
) -> PipelineResult:
    """Run the full pipeline over one month of departmental exports."""
    if not settings.bridgeflow_enable_legacy_pipeline:
        raise HTTPException(403, "Legacy completion pipeline is disabled; use DSH domain tools")
    if len(departments) != len(files):
        raise HTTPException(400, "each uploaded file needs exactly one department label")

    frames: dict[Department, pd.DataFrame] = {}
    for department, upload in zip(departments, files, strict=True):
        frames[department] = _read(await upload.read(), upload.filename or "")

    result = await orchestrator.run(period, frames)
    store.save(result)
    return result


@app.post("/quote", response_model=QuoteRecommendation, dependencies=[Depends(require_host)])
async def quote(period: str, request: QuoteRequest) -> QuoteRecommendation:
    if not settings.bridgeflow_enable_legacy_pipeline:
        raise HTTPException(403, "Ungrounded quote generation is disabled")
    result = store.load(period)
    if result is None:
        raise HTTPException(404, f"no analysis for period {period} — run /analyze first")
    return await orchestrator.quote(request, result)


def _read(payload: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(payload))
    return pd.read_csv(io.BytesIO(payload))
