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

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import FieldDictionary, load_field_dictionary
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.schemas import CleanTable, Department

router = APIRouter(prefix="/tools", tags=["tools"])

DEPARTMENTS: tuple[Department, ...] = ("production", "procurement", "finance", "marketing")


# --- metric catalogue --------------------------------------------------------


class MetricSpec(BaseModel):
    """One metric, defined by the entity kinds it needs rather than by column names.

    Naming a column here would hard-code the customer's schema, which is still being
    negotiated. The dictionary maps kinds to whatever the columns turn out to be.
    """

    name: str
    unit: str
    formula: str
    requires: list[str]
    #: How to combine the values found for `requires`.
    op: str


METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(
        name="total_output",
        unit="units",
        formula="sum of production output quantity for the period",
        requires=["output_quantity"],
        op="sum",
    ),
    MetricSpec(
        name="material_spend",
        unit="currency",
        formula="sum of procurement line amounts for the period",
        requires=["purchase_amount"],
        op="sum",
    ),
    MetricSpec(
        name="revenue",
        unit="currency",
        formula="sum of finance revenue lines for the period",
        requires=["revenue_amount"],
        op="sum",
    ),
)


class MetricCatalogue(BaseModel):
    metrics: list[MetricSpec]


@router.post("/list-metrics", response_model=MetricCatalogue)
async def list_metrics() -> MetricCatalogue:
    """Which metrics can be computed at all.

    Returns an empty list when the field dictionary is missing: without declarations
    nothing can be computed by rule, and saying so is the honest answer.
    """
    if load_field_dictionary(_dictionary_path()).is_empty:
        return MetricCatalogue(metrics=[])
    return MetricCatalogue(metrics=list(METRICS))


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
    dictionary = load_field_dictionary(_dictionary_path())
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


class EvidenceCell(BaseModel):
    department: str
    row: int
    column: str
    value: str


#: How many contributing cells a tool result may name. The PRD sizes one batch at
#: 200,000 rows; returning a cell per row would put the table back into the context
#: the tools exist to keep it out of — and every agent in the fan-out pays separately.
EVIDENCE_SAMPLE = 5


class MetricResult(BaseModel):
    metric: str
    period: str
    value: float
    unit: str
    formula: str
    #: A bounded sample, never the whole set. See `evidence_total`.
    evidence: list[EvidenceCell] = Field(default_factory=list)
    evidence_total: int = 0
    evidence_truncated: bool = False


@router.post("/aggregate-metric", response_model=MetricResult)
async def aggregate_metric(request: AggregateRequest) -> MetricResult:
    """Compute one metric by rule, and return the cells it came from.

    Refuses rather than estimates. A metric whose declared fields are absent has no
    honest value, and an invented one would propagate into a finding that claims to
    be evidence-backed.
    """
    spec = next((m for m in METRICS if m.name == request.metric), None)
    if spec is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"No metric named {request.metric!r}. "
                f"Call list_metrics — the set is configured, not fixed in code."
            ),
        )

    dictionary = load_field_dictionary(_dictionary_path())
    if dictionary.is_empty:
        raise HTTPException(
            status_code=409,
            detail=(
                "The OA field dictionary is not configured, so no column can be "
                "identified by meaning. Nothing is computed from column spelling."
            ),
        )

    tables = await _clean_tables(request.period)
    total = 0.0
    evidence: list[EvidenceCell] = []

    unreadable: list[str] = []

    for table in tables:
        for measure in spec.requires:
            for column in _columns_measuring(dictionary, table, measure):
                for index, row in enumerate(table.rows):
                    if request.entity and request.entity.lower() not in str(row).lower():
                        continue
                    raw = row.get(column)
                    if raw is None or raw == "":
                        continue  # an absent measurement is absent, not zero
                    number = _as_number(raw)
                    if number is None:
                        # Present but unreadable. Summing around it would answer from
                        # a subset of the rows and present the result as the total.
                        unreadable.append(f"{table.department} row {index} {column}={raw!r}")
                        continue
                    total += number
                    evidence.append(
                        EvidenceCell(
                            department=table.department,
                            row=index,
                            column=column,
                            value=str(raw),
                        )
                    )

    if unreadable:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{request.metric} cannot be computed: "
                f"{len(unreadable)} declared value(s) could not be read as numbers — "
                + "; ".join(unreadable[:5])
                + ". Refusing rather than totalling the rows that happened to parse."
            ),
        )

    if not evidence:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{request.metric} needs {', '.join(spec.requires)}, and the field "
                f"dictionary declares no such column for {request.period}. "
                f"Refusing rather than returning a figure with no source rows."
            ),
        )

    return MetricResult(
        metric=spec.name,
        period=request.period,
        value=round(total, 4) if spec.op == "sum" else total,
        unit=spec.unit,
        formula=spec.formula,
        evidence=evidence[:EVIDENCE_SAMPLE],
        evidence_total=len(evidence),
        evidence_truncated=len(evidence) > EVIDENCE_SAMPLE,
    )


# --- helpers -----------------------------------------------------------------


def _dictionary_path() -> Path:
    configured = Path(settings.field_dictionary_path)
    return configured if configured.is_absolute() else REPO_ROOT / configured


def _columns_measuring(dictionary: FieldDictionary, table: CleanTable, measure: str) -> list[str]:
    """The columns in this table the dictionary declares as `measure`.

    Only declared columns count. A column that merely looks like an amount is not
    one, and inferring it is how an unfounded figure reaches a finding.
    """
    declared = set(dictionary.columns_measuring(table.department, measure))
    return [c.name for c in table.columns if c.name in declared]


def _as_number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


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
