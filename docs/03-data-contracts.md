# 03 — Data contracts

All models live in `backend/src/bridgeflow/schemas/`. They are the interface between
agents; changing one is a breaking change and needs a PR review.

## Ingest

```python
Department = Literal["production", "procurement", "finance", "marketing"]

class RawUpload:
    department: Department
    period: str            # "2025-11"  (ISO year-month)
    filename: str
    sheet: str | None
```

## Stage 1 — Sanitizer

```python
class Correction:
    row: int
    column: str
    before: Any
    after: Any
    rule: str              # "date_parse" | "unit_normalise" | "llm_typo_fix" | ...
    confidence: float      # 0..1
    reason: str

class CleanTable:
    department: Department
    period: str
    columns: list[ColumnSpec]     # name, dtype, unit, semantic_hint
    rows: list[dict[str, Any]]
    corrections: list[Correction]
    quarantine: list[dict[str, Any]]   # rows we refused to guess at
```

## Stage 2 — Resolver

```python
class Entity:
    id: str                # canonical id, e.g. "sku:A1"
    kind: Literal["sku", "raw_material", "gl_account", "capacity_unit", "customer"]
    label: str
    aliases: list[str]     # every department-local name we've seen

class Link:
    source: str            # Entity.id
    target: str            # Entity.id
    relation: Literal["consumes", "books_to", "produced_on", "ordered_by"]
    confidence: float
    justification: str

class EntityGraph:
    entities: list[Entity]
    links: list[Link]
    unresolved: list[Link]         # below threshold — needs human confirmation
```

Confirmed `unresolved` links are persisted to `data/mappings/{tenant}.json` and applied
automatically in later periods.

## Stage 3 — Evaluator

```python
Severity = Literal["info", "watch", "warning", "critical"]

class Evidence:
    period: str
    entity_id: str
    metric: str
    value: float
    comparison: str | None    # "vs 2025-10: +18%"

class Finding:
    role: Department
    severity: Severity
    claim: str                # one sentence, no hedging
    evidence: list[Evidence]  # MUST be non-empty
    suggested_action: str

class Tension:
    finding_a: Finding
    finding_b: Finding
    description: str          # why these two pull in opposite directions
```

## Stage 4 — SOP & Flow

```python
class MasterTable:
    grain: Literal["month", "quarter", "year"]
    periods: list[str]
    rows: list[dict[str, Any]]   # one row per (period, sku, customer)

class ApprovalCard:
    title: str
    owner: Department
    due: date
    findings: list[Finding]
    options: list[str]
```

## Quote Simulator

```python
class QuoteRequest:
    customer_id: str
    sku_id: str
    quantity: int
    requested_delivery: date

class QuoteRecommendation:
    floor_price: float        # below this we lose money
    target_price: float
    stretch_price: float
    margin_at_target: float
    payment_terms_days: int
    capacity_feasible: bool
    rationale: list[str]
```
