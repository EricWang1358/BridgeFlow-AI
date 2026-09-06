"""Data contracts shared by every agent. See docs/03-data-contracts.md."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Department = Literal["production", "procurement", "finance", "marketing"]
Severity = Literal["info", "watch", "warning", "critical"]
# Entity kinds and relations are open, not a closed `Literal`.
#
# The customer's schema is still being negotiated; a sixth kind — a work order, a
# batch, a project — would otherwise mean editing Python, editing schemas and editing
# tests, when it should mean editing one YAML file (`CLAUDE.md`, eighth hard
# constraint). Open does not mean unchecked: the resolver still rejects anything the
# field dictionary does not declare, so the validation moved rather than disappeared.
#
# The names below are the ones the sample data uses. They are documentation of the
# common case, not the permitted set.
EntityKind = str
Relation = str

KNOWN_ENTITY_KINDS: tuple[str, ...] = (
    "sku",
    "raw_material",
    "gl_account",
    "capacity_unit",
    "customer",
)
KNOWN_RELATIONS: tuple[str, ...] = ("consumes", "books_to", "produced_on", "ordered_by")


# --- ingest -------------------------------------------------------------------


class RawUpload(BaseModel):
    department: Department
    period: str = Field(description="ISO year-month, e.g. '2025-11'")
    filename: str
    sheet: str | None = None


# --- stage 1: sanitizer -------------------------------------------------------


class ColumnSpec(BaseModel):
    name: str
    dtype: Literal["string", "number", "date", "bool"]
    unit: str | None = None
    semantic_hint: str | None = None


class SourceRef(BaseModel):
    """Where a value came from, precisely enough to open the file and point at it.

    `docs/07` requires that any result can be traced back to the original file and
    the specific cell, and `docs/04`'s demo rules say a judge will ask. Row and
    column alone cannot answer that: they do not say which file, which sheet, or
    which import batch, and a monthly process has four files a month.
    """

    #: The import batch this came from. Empty until batches exist (#12).
    batch: str = ""
    department: Department
    period: str
    #: Original filename as uploaded, so the answer names something the user has.
    filename: str = ""
    #: Worksheet name for XLSX; empty for CSV.
    sheet: str = ""
    #: 0-based index into the cleaned rows.
    row: int
    column: str

    def cite(self) -> str:
        """One line a person can act on."""
        where = self.filename or f"{self.department} {self.period}"
        sheet = f" [{self.sheet}]" if self.sheet else ""
        return f"{where}{sheet} row {self.row} column {self.column}"


class Correction(BaseModel):
    #: Where the changed value lives. Optional so older logs still load.
    source: SourceRef | None = None
    row: int
    column: str
    before: Any = None
    after: Any = None
    rule: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class CleanTable(BaseModel):
    department: Department
    period: str
    columns: list[ColumnSpec] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    corrections: list[Correction] = Field(default_factory=list)
    quarantine: list[dict[str, Any]] = Field(default_factory=list)


# --- stage 2: resolver --------------------------------------------------------


class Entity(BaseModel):
    id: str
    kind: EntityKind
    label: str
    aliases: list[str] = Field(default_factory=list)


#: How a link came to be believed. "Not judged yet" and "judged and uncertain" are
#: different states, and a human queue that shows them as one tells a reviewer to
#: spend their attention in the wrong place.
LinkStatus = Literal["declared", "adjudicated", "unadjudicated"]


class Link(BaseModel):
    source: str
    target: str
    relation: Relation
    confidence: float = Field(ge=0.0, le=1.0)
    justification: str = ""
    #: `declared` came from the OA dictionary and was never in doubt.
    #: `adjudicated` was judged by a model — trust `confidence`.
    #: `unadjudicated` means no verdict came back. Its confidence is the candidate's
    #: starting value and means nothing; a reviewer must look at this first.
    status: LinkStatus = "adjudicated"


class EntityGraph(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    unresolved: list[Link] = Field(default_factory=list)

    def by_id(self, entity_id: str) -> Entity | None:
        return next((e for e in self.entities if e.id == entity_id), None)


# --- stage 3: evaluator -------------------------------------------------------


class Evidence(BaseModel):
    period: str
    entity_id: str
    metric: str
    value: float
    comparison: str | None = None
    #: The cells this figure was computed from — a bounded sample, never the whole
    #: set. One batch is sized at 200,000 rows (#58).
    sources: list[SourceRef] = Field(default_factory=list)
    #: How many cells contributed, however few are listed above.
    source_count: int = 0
    #: PRD chapter 16 requires a warning to state what it was compared against, the
    #: threshold it crossed, and the impact. Absent means "not stated", not "none".
    baseline: str | None = None
    threshold: str | None = None
    impact: str | None = None


class Finding(BaseModel):
    role: Department
    severity: Severity
    claim: str
    evidence: list[Evidence]
    suggested_action: str

    @field_validator("evidence")
    @classmethod
    def _evidence_required(cls, v: list[Evidence]) -> list[Evidence]:
        # A claim with nothing behind it is a hallucination with good grammar.
        if not v:
            raise ValueError("a Finding must cite at least one piece of evidence")
        return v


class Tension(BaseModel):
    finding_a: Finding
    finding_b: Finding
    description: str


# --- stage 4: SOP & flow ------------------------------------------------------


class MasterTable(BaseModel):
    grain: Literal["month", "quarter", "year"] = "month"
    periods: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)

    #: Labels that never reached the entity graph, so nothing could merge them.
    #: A row per spelling is what an incomplete dictionary looks like in the output,
    #: and the honest thing to do is say so on the table rather than let the split
    #: read as two entities that legitimately exist.
    unmatched_entities: list[str] = Field(default_factory=list)


class ApprovalCard(BaseModel):
    title: str
    owner: Department
    due: date
    findings: list[Finding] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)


class RiskReport(BaseModel):
    period: str
    findings: list[Finding] = Field(default_factory=list)
    tensions: list[Tension] = Field(default_factory=list)
    cards: list[ApprovalCard] = Field(default_factory=list)


# --- quote simulator ----------------------------------------------------------


class QuoteRequest(BaseModel):
    customer_id: str
    sku_id: str
    quantity: int = Field(gt=0)
    requested_delivery: date


class QuoteRecommendation(BaseModel):
    floor_price: float
    target_price: float
    stretch_price: float
    margin_at_target: float
    payment_terms_days: int
    capacity_feasible: bool
    rationale: list[str] = Field(default_factory=list)


# --- pipeline -----------------------------------------------------------------


class PipelineResult(BaseModel):
    period: str
    clean_tables: list[CleanTable] = Field(default_factory=list)
    graph: EntityGraph = Field(default_factory=EntityGraph)
    master_table: MasterTable = Field(default_factory=MasterTable)
    risk_report: RiskReport | None = None
