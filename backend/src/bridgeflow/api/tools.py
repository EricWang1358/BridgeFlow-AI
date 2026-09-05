"""The bodies behind the dsh tools.

The declarations live in `plugins/` because TypeScript is the only side of the
runtime boundary that can declare a tool — the Python SDK is a JSON-RPC client with
no tool surface. The work lives here because this is where pandas is, and because
`docs/13` §7 settles that the model must not do arithmetic it cannot be audited on.

Every endpoint answers one tool call. Two rules hold throughout:

- **Nothing is guessed.** A metric whose declared fields are missing is refused with
  409, not estimated. A column the field dictionary does not claim comes back
  undeclared rather than inferred from its name (`CLAUDE.md`, eighth hard constraint).
- **Every figure carries its rows.** `aggregate_metric` returns the cells it summed,
  so a finding can cite them and a judge asking "where did that come from" has an
  answer.
"""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from bridgeflow import mappings, metrics
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import load_field_dictionary
from bridgeflow.config import REPO_ROOT
from bridgeflow.schemas import CleanTable, Department, Link

router = APIRouter(prefix="/tools", tags=["tools"])

DEPARTMENTS: tuple[Department, ...] = ("production", "procurement", "finance", "marketing")


# --- metric catalogue --------------------------------------------------------


class MetricCatalogue(BaseModel):
    metrics: list[metrics.MetricSpec]


@router.post("/list-metrics", response_model=MetricCatalogue)
async def list_metrics() -> MetricCatalogue:
    """Which metrics can be computed with what the dictionary currently declares."""
    return MetricCatalogue(metrics=metrics.available(_dictionary()))


# --- field dictionary lookup -------------------------------------------------


class LookupRequest(BaseModel):
    department: Department
    column: str


class ColumnMeaning(BaseModel):
    department: str
    column: str
    kind: str | None = None
    #: "declared" only when the OA dictionary actually claims the column.
    source: str


@router.post("/lookup-field-dictionary", response_model=ColumnMeaning)
async def lookup_field_dictionary(request: LookupRequest) -> ColumnMeaning:
    """What the dictionary declares this column to be.

    `FieldDictionary.kind_for` falls back to built-in English column hints when no
    dictionary is loaded, which is fine for running the committed samples and wrong
    to report as a declaration: the customer's real export is very likely not in
    English, and a hint that happens to match is a coincidence, not a fact.

    So an unconfigured dictionary answers "unconfigured" and no kind at all, rather
    than passing a guess off as an answer — `CLAUDE.md`, eighth hard constraint.
    """
    dictionary = _dictionary()
    if dictionary.is_empty:
        return ColumnMeaning(
            department=request.department,
            column=request.column,
            kind=None,
            source="unconfigured",
        )
    kind = dictionary.kind_for(request.department, request.column)
    return ColumnMeaning(
        department=request.department,
        column=request.column,
        kind=kind,
        source="declared" if kind else "undeclared",
    )


# --- metric aggregation ------------------------------------------------------


class AggregateRequest(BaseModel):
    metric: str
    period: str
    entity: str | None = None


#: Re-exported so tests and callers name one constant, not two.
EVIDENCE_SAMPLE = metrics.EVIDENCE_SAMPLE


class MetricResult(BaseModel):
    metric: str
    period: str
    value: float
    unit: str
    formula: str
    #: A bounded sample, never the whole set. See `evidence_total` and #58.
    evidence: list[EvidenceCell] = Field(default_factory=list)
    evidence_total: int = 0
    evidence_truncated: bool = False


class EvidenceCell(BaseModel):
    department: str
    row: int
    column: str
    value: str


@router.post("/aggregate-metric", response_model=MetricResult)
async def aggregate_metric(request: AggregateRequest) -> MetricResult:
    """Compute one metric by rule, and name a bounded sample of the cells it came from.

    The arithmetic itself lives in `bridgeflow.metrics`, shared with the evaluator, so
    a figure quoted in a finding and a figure returned to a tool call are the same
    figure computed the same way.
    """
    tables = await _clean_tables(request.period)
    try:
        computed = metrics.compute(
            request.metric, request.period, tables, entity=request.entity, dictionary=_dictionary()
        )
    except metrics.MetricRefused as refused:
        raise HTTPException(status_code=409, detail=str(refused)) from refused

    return MetricResult(
        metric=computed.metric,
        period=computed.period,
        value=computed.value,
        unit=computed.unit,
        formula=computed.formula,
        evidence=[
            EvidenceCell(
                department=ref.department,
                row=ref.row,
                column=ref.column,
                value=str(_cell(tables, ref)),
            )
            for ref in computed.sources
        ],
        evidence_total=computed.source_count,
        evidence_truncated=computed.truncated,
    )


def _cell(tables: list[CleanTable], ref) -> object:
    for table in tables:
        if table.department == ref.department and 0 <= ref.row < len(table.rows):
            return table.rows[ref.row].get(ref.column, "")
    return ""


# --- helpers -----------------------------------------------------------------


def _dictionary():
    return load_field_dictionary(metrics.dictionary_path())


async def _clean_tables(period: str) -> list[CleanTable]:
    """Sanitize the committed sample files for one period.

    A real deployment reads the uploaded batch instead; the sample path is what the
    demo and the tests run on.
    """
    samples = REPO_ROOT / "data" / "samples"
    agent = DataSanitizerAgent()
    tables: list[CleanTable] = []
    for department in DEPARTMENTS:
        path = samples / f"{department}_{period}.csv"
        if not path.is_file():
            continue
        tables.append(await agent.run(SanitizerInput(department, period, pd.read_csv(path))))
    if not tables:
        raise HTTPException(status_code=409, detail=f"No sample data for period {period}.")
    return tables


# --- confirming a mapping ----------------------------------------------------


class ConfirmRequest(BaseModel):
    source: str
    target: str
    relation: str
    accepted: bool
    evidence: str = ""
    period: str = ""
    confirmed_by: str = "unknown-agent"


class ConfirmationResult(BaseModel):
    source: str
    target: str
    relation: str
    accepted: bool
    confirmed_by: str
    confirmed_at: str
    remembered: int


@router.post("/confirm-mapping", response_model=ConfirmationResult)
async def confirm_mapping(request: ConfirmRequest) -> ConfirmationResult:
    """Record one human decision about a mapping.

    The only endpoint here that writes. Its caller is gated by `ctx.approval`
    (`plugins/src/guards/approval-gate.ts`), so reaching this point means somebody
    granted it — which is the part an auditor reads.
    """
    link = Link(
        source=request.source,
        target=request.target,
        relation=request.relation,
        confidence=1.0 if request.accepted else 0.0,
        justification=request.evidence,
    )
    memory = mappings.confirm(
        link, by=request.confirmed_by, accepted=request.accepted, period=request.period
    )
    recorded = memory.find(link)
    assert recorded is not None  # just written
    return ConfirmationResult(
        source=recorded.source,
        target=recorded.target,
        relation=recorded.relation,
        accepted=recorded.accepted,
        confirmed_by=recorded.confirmed_by,
        confirmed_at=recorded.confirmed_at,
        remembered=len(memory.confirmations),
    )
