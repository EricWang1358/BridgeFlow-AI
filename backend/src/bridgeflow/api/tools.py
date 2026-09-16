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
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from bridgeflow import column_matches, mappings, metrics, store
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import load_field_dictionary
from bridgeflow.api.batches import BatchRef, BatchSummary, batch_dictionary, load_batch, summary
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.schemas import CleanTable, Department, Link
from bridgeflow.security import consume_approval

router = APIRouter(prefix="/tools", tags=["tools"])

DEPARTMENTS: tuple[Department, ...] = ("production", "procurement", "finance", "marketing")


# --- metric catalogue --------------------------------------------------------


class MetricCatalogue(BaseModel):
    metrics: list[metrics.MetricSpec]


class CatalogueRequest(BaseModel):
    batch_id: str | None = None


@router.post("/list-metrics", response_model=MetricCatalogue)
async def list_metrics(request: CatalogueRequest | None = None) -> MetricCatalogue:
    """Which metrics can be computed with what the dictionary currently declares."""
    if request and request.batch_id:
        batch = load_batch(request.batch_id)
        if (batch.dictionary_snapshot or {}).get("business_review"):
            from bridgeflow.business import context
            facts = context(request.batch_id, batch)["facts"]
            return MetricCatalogue(metrics=[metrics.MetricSpec(name=name, unit=fact["unit"],
                formula=fact["formula"], requires=[], role="declared_business_contract") for name, fact in facts.items()])
        dictionary = batch_dictionary(batch)
    else:
        dictionary = _dictionary()
    return MetricCatalogue(metrics=metrics.available(dictionary))


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
    batch_id: str | None = None


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
    filename: str = ""
    sheet: str = ""
    source_row: int = -1
    original_column: str = ""


@router.post("/aggregate-metric", response_model=MetricResult)
async def aggregate_metric(request: AggregateRequest) -> MetricResult:
    """Compute one metric by rule, and name a bounded sample of the cells it came from.

    The arithmetic itself lives in `bridgeflow.metrics`, shared with the evaluator, so
    a figure quoted in a finding and a figure returned to a tool call are the same
    figure computed the same way.
    """
    if request.batch_id:
        batch = load_batch(request.batch_id)
        if batch.period != request.period:
            raise HTTPException(409, "Batch period does not match requested period")
        tables = batch.clean_tables
        dictionary = batch_dictionary(batch)
        if any(table.quarantine for table in tables):
            raise HTTPException(409, "Batch contains quarantined rows; resolve the source and reimport before reporting totals")
        if (batch.dictionary_snapshot or {}).get("business_review"):
            from bridgeflow.business import context
            facts = context(request.batch_id, batch)["facts"]
            if request.entity:
                raise HTTPException(409, "Entity-scoped business formulas are not declared; cannot infer a filter")
            if request.metric not in facts:
                raise HTTPException(409, f"Unknown metric; available: {', '.join(facts)}")
            fact = facts[request.metric]
            return MetricResult(metric=request.metric, period=request.period, value=fact["value"],
                unit=fact["unit"], formula=fact["formula"], evidence=[EvidenceCell(
                    **{key: ref[key] for key in ("department", "row", "column", "filename", "sheet", "original_column")},
                    source_row=ref["source_row"] or -1,
                    value=str(next(t for t in tables if t.department == ref["department"]).rows[ref["row"]].get(ref["column"])),
                ) for ref in fact["sources"]], evidence_total=fact["source_count"], evidence_truncated=fact["truncated"])
    else:
        tables = await _clean_tables(request.period)
        dictionary = _dictionary()
    try:
        computed = metrics.compute(
            request.metric, request.period, tables, entity=request.entity, dictionary=dictionary
        )
    except metrics.MetricRefused as refused:
        available = [m.name for m in metrics.available(dictionary)]
        raise HTTPException(
            status_code=409,
            detail=f"{refused} Available metrics: {', '.join(available) or '(none configured)'}. "
                   "Use list_metrics; do not retry undeclared names.",
        ) from refused

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
    saved = store.load(period)
    if saved is not None:
        return saved.clean_tables
    if not settings.bridgeflow_allow_sample_data:
        raise HTTPException(409, "No stored analysis; supply an uploaded batch_id")
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
    #: The tool call this is. Joins the write to the approval that allowed it.
    call_id: str | None = None


class ConfirmationResult(BaseModel):
    source: str
    target: str
    relation: str
    accepted: bool
    confirmed_by: str
    confirmed_at: str
    #: Authenticated DSH session attribution; individual employee identity is not implemented.
    authorised_by: str = ""
    remembered: int


@router.post("/confirm-mapping", response_model=ConfirmationResult)
async def confirm_mapping(request: ConfirmRequest, http_request: Request) -> ConfirmationResult:
    """Record one human decision about a mapping.

    A host credential alone is insufficient: a fresh payload-bound receipt from
    the DSH approval gate is required. Attribution identifies the authenticated
    shared session, without treating an agent-supplied name as employee identity.
    """
    if not settings.bridgeflow_allow_mapping_write:
        raise HTTPException(403, "Mapping writes disabled by deployment policy")
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body(), "confirm_mapping")
    link = Link(
        source=request.source,
        target=request.target,
        relation=request.relation,
        confidence=1.0 if request.accepted else 0.0,
        justification=request.evidence,
    )
    memory = mappings.confirm(
        link,
        by=actor if settings.portal_base_url else request.confirmed_by,
        accepted=request.accepted,
        period=request.period,
        authorised_by=actor,
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
        authorised_by=recorded.authorised_by,
        remembered=len(memory.confirmations),
    )


@router.post("/batch-summary", response_model=BatchSummary)
async def batch_summary(request: BatchRef) -> BatchSummary:
    return summary(request.batch_id, load_batch(request.batch_id))


# --- matching uploaded columns onto declared ones ------------------------------------


# `entity_overlap` is omitted rather than null when nothing is comparable.
@router.post("/column-candidates", response_model=column_matches.CandidateList,
             response_model_exclude_none=True)
async def column_candidates(request: BatchRef) -> column_matches.CandidateList:
    """For each uploaded column the dictionary does not know, the declared columns it
    could be — and only those. Structural evidence only; no cell leaves the batch."""
    batch = load_batch(request.batch_id)
    return column_matches.candidates(
        request.batch_id, batch.period, batch.clean_tables, batch.dictionary_snapshot,
        applied=batch.column_matches,
    )


class ColumnMatchRequest(BaseModel):
    batch_id: str
    department: str
    column: str
    target: str
    accepted: bool
    #: Why, in the person's or the proposal's words. Kept with the decision.
    reason: str = Field("", max_length=500)
    confirmed_by: str = "unknown-agent"
    call_id: str | None = None


class ColumnMatchResult(BaseModel):
    department: str
    column: str
    target: str
    accepted: bool
    confirmed_at: str
    authorised_by: str
    #: What happens now, so a rejection is never a dead end.
    next_step: str
    remaining_candidates: list[str] = Field(default_factory=list)


@router.post("/confirm-column-match", response_model=ColumnMatchResult)
async def confirm_column_match(request: ColumnMatchRequest, http_request: Request) -> ColumnMatchResult:
    """Record one person's decision that an uploaded column is, or is not, a declared one.

    The closed candidate set is enforced here, not trusted from the prompt: a target
    that the batch's frozen dictionary does not declare for this department, or that
    the upload already carries, is refused before any approval is spent.
    """
    if not settings.bridgeflow_allow_mapping_write:
        raise HTTPException(403, "Mapping writes disabled by deployment policy")
    batch = load_batch(request.batch_id)
    tables = [t for t in batch.clean_tables if t.department == request.department]
    if len(tables) != 1:
        raise HTTPException(409, "That department is not in this batch")
    unknown, missing = column_matches.open_columns(batch.dictionary_snapshot, tables[0])
    if request.column not in unknown:
        raise HTTPException(409, "That column is already declared or is not in this upload")
    if request.target not in missing:
        raise HTTPException(
            409,
            "Not a declared candidate: a match can only name a column the dictionary already "
            "declares for this department and the upload lacks. Creating fields is the "
            "dictionary owner's decision.",
        )
    actor = consume_approval(http_request.headers.get("x-bridgeflow-approval", ""), await http_request.body(), "confirm_column_match")

    profile = next(p for p in column_matches.profiling.profile_table(tables[0])[0]
                   if p.column == request.column)
    memory = column_matches.decide(column_matches.ColumnMatch(
        department=request.department, column=request.column, target=request.target,
        accepted=request.accepted, evidence=column_matches.fingerprint(profile),
        reason=request.reason, period=batch.period, batch_id=request.batch_id,
        confirmed_by=actor if settings.portal_base_url else request.confirmed_by, authorised_by=actor,
    ))
    recorded = column_matches.memory_for(memory, request.department, request.column, request.target)
    assert recorded is not None  # just written

    rejected = {m.target for m in memory.matches
                if not m.accepted and m.department == request.department and m.column == request.column}
    remaining = [t for t in missing if t != request.target and t not in rejected]
    if request.accepted:
        step = ("Remembered. This batch stays as it was frozen; import the files again and "
                "this column will be read as the declared one.")
    elif remaining:
        step = "Rejected and remembered. Other declared candidates remain for this column."
    else:
        step = ("Rejected and remembered. No declared column is left for this upload column; "
                "the dictionary owner must decide whether it should be declared.")
    return ColumnMatchResult(
        department=recorded.department, column=recorded.column, target=recorded.target,
        accepted=recorded.accepted, confirmed_at=recorded.confirmed_at,
        authorised_by=recorded.authorised_by, next_step=step, remaining_candidates=remaining,
    )
