from __future__ import annotations

import io
from typing import Annotated

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from bridgeflow import __version__
from bridgeflow.api.tools import router as tools_router
from bridgeflow.config import settings
from bridgeflow.pipeline import Orchestrator
from bridgeflow.schemas import Department, PipelineResult, QuoteRecommendation, QuoteRequest

app = FastAPI(title="BridgeFlow AI", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The dsh tools call in here for the work their TypeScript declarations describe.
# See plugins/README.md for why the two halves live where they do.
app.include_router(tools_router)

orchestrator = Orchestrator()

# Hackathon-scoped: one in-memory result per period. Swap for a store before any
# real deployment — see docs/05-roadmap.md.
_results: dict[str, PipelineResult] = {}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "llm_provider": settings.llm_provider}


@app.post("/analyze", response_model=PipelineResult)
async def analyze(
    period: Annotated[str, Form()],
    departments: Annotated[list[Department], Form()],
    files: Annotated[list[UploadFile], File()],
) -> PipelineResult:
    """Run the full pipeline over one month of departmental exports."""
    if len(departments) != len(files):
        raise HTTPException(400, "each uploaded file needs exactly one department label")

    frames: dict[Department, pd.DataFrame] = {}
    for department, upload in zip(departments, files, strict=True):
        frames[department] = _read(await upload.read(), upload.filename or "")

    result = await orchestrator.run(period, frames)
    _results[period] = result
    return result


@app.post("/quote", response_model=QuoteRecommendation)
async def quote(period: str, request: QuoteRequest) -> QuoteRecommendation:
    result = _results.get(period)
    if result is None:
        raise HTTPException(404, f"no analysis for period {period} — run /analyze first")
    return await orchestrator.quote(request, result)


def _read(payload: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(payload))
    return pd.read_csv(io.BytesIO(payload))
