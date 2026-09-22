from __future__ import annotations

import io
import json
import time
from typing import Annotated

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from bridgeflow import __version__, journal, store
from bridgeflow.api.approvals import router as approvals_router
from bridgeflow.api.batches import router as batches_router
from bridgeflow.api.checklist import router as checklist_router
from bridgeflow.api.conclusions import router as conclusions_router
from bridgeflow.api.console import router as console_router
from bridgeflow.api.conventions import router as conventions_router
from bridgeflow.api.discovery import router as discovery_router
from bridgeflow.api.discovery import tools_router as discovery_tools_router
from bridgeflow.api.dispositions import router as dispositions_router
from bridgeflow.api.documents import router as documents_router
from bridgeflow.api.dictionary_tools import router as dictionary_tools_router
from bridgeflow.api.issues import router as issues_router
from bridgeflow.api.feishu_tools import router as feishu_tools_router
from bridgeflow.api.integration import router as integration_router
from bridgeflow.api.observability import router as observability_router
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
REASON_CAP = 8192


async def _reason_of(response):
    """The refusal's own words, and a response that can still be sent."""
    chunks, size = [], 0
    async for chunk in response.body_iterator:
        chunks.append(chunk)
        size += len(chunk)
        if size > REASON_CAP:
            break
    body = b"".join(chunks)
    reason = ""
    try:
        payload = json.loads(body)
        detail = payload.get("detail") if isinstance(payload, dict) else None
        reason = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False) if detail else ""
    except (ValueError, UnicodeDecodeError):
        reason = ""
    rebuilt = Response(content=body, status_code=response.status_code,
                       headers=dict(response.headers), media_type=response.media_type)
    return rebuilt, reason


@app.middleware("http")
async def decision_journal(request: Request, call_next):
    """Record every decision once, here, instead of logging from forty call sites.

    Every refusal in this codebase raises an HTTPException whose detail is the sentence a
    person should read. Catching it at the seam records that sentence verbatim — a paraphrase
    written at a call site is the thing that goes stale. Facts a handler wants on its own
    entry go on `request.state.journal`; the journal keeps only the declared keys, so this
    cannot become a way around the no-rows rule.
    """
    started = time.perf_counter()
    # Reading the journal is not a decision about the business, and a trace that fills up
    # with someone watching it is a trace nobody can read.
    watched = not request.url.path.startswith(("/journal", "/eval/report"))
    trace = request.headers.get("x-bridgeflow-trace") or journal.new_trace()
    request.state.journal, request.state.trace = {}, trace
    status, reason, response = 500, "", None
    try:
        response = await call_next(request)
        status = response.status_code
        if status >= 400:
            # A refusal reaches here as an ordinary response, because FastAPI has already
            # turned the exception into one. Reading it back is how the journal keeps the
            # caller's own sentence instead of a paraphrase; only error bodies are read,
            # and only up to a cap, so nothing large is ever buffered.
            response, reason = await _reason_of(response)
    except HTTPException as exc:  # raised outside the router, e.g. in a dependency
        status, reason = exc.status_code, str(exc.detail)
        raise
    finally:
        facts = (journal.subject_of(request.url.path)
                 | journal.trace_facts(request.headers)
                 | dict(getattr(request.state, "journal", {}) or {}))
        for key in ("batch_id", "period", "report_id"):
            if key not in facts and key in request.query_params:
                facts[key] = request.query_params[key]
        if watched:
            journal.record(journal.entry(
                trace=trace, surface=journal.shape(request.url.path), method=request.method,
                status=status, started=started, reason=reason, facts=facts,
                actor=journal.actor_of(request.headers.get("x-bridgeflow-user"),
                                       host=bool(request.headers.get("authorization")))))
    # The trace id travels back, so the person reading the studio and the person reading the
    # journal are looking at the same line.
    response.headers["x-bridgeflow-trace"] = trace
    return response
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
app.include_router(dictionary_tools_router, dependencies=[Depends(require_host)])
app.include_router(issues_router, dependencies=[Depends(require_host)])
app.include_router(conclusions_router, dependencies=[Depends(require_host)])
app.include_router(conventions_router, dependencies=[Depends(require_host)])
app.include_router(checklist_router, dependencies=[Depends(require_host)])
app.include_router(dispositions_router, dependencies=[Depends(require_host)])
app.include_router(observability_router, dependencies=[Depends(require_host)])

# The one router with no host dependency, on purpose: the login portal calls it from
# its own forward_auth target, and the portal holds no host credential (api/console.py
# says why). Its own authentication is the portal signature it verifies through JWKS.
app.include_router(console_router)

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
