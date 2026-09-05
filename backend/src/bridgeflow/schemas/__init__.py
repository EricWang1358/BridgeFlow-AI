"""Data contracts shared by every agent. See docs/03-data-contracts.md."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Department = Literal["production", "procurement", "finance", "marketing"]
Severity = Literal["info", "watch", "warning", "critical"]
EntityKind = Literal["sku", "raw_material", "gl_account", "capacity_unit", "customer"]
Relation = Literal["consumes", "books_to", "produced_on", "ordered_by"]


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


class Correction(BaseModel):
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


class Link(BaseModel):
    source: str
    target: str
    relation: Relation
    confidence: float = Field(ge=0.0, le=1.0)
    justification: str = ""


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
