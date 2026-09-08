# 03 — Data contracts

All models live in `backend/src/bridgeflow/schemas/`. They are the interface between stages:
changing one is a breaking change and needs a review, because every agent, tool signature and UI
card reads them.

Two types at the top of the module are deliberately open:

```python
Department = Literal["production", "procurement", "finance", "marketing"]
Severity   = Literal["info", "watch", "warning", "critical"]
EntityKind = str      # KNOWN_ENTITY_KINDS documents the common case; it does not restrict it
Relation   = str      # ditto, see KNOWN_RELATIONS
```

Entity kinds and relations used to be closed `Literal`s, which meant that meeting a sixth kind of
entity (a work order, a batch, a project) required editing Python. It does not: the field dictionary
still decides what is accepted, so an undeclared kind is refused rather than invented. Making it open
moved the check, it did not remove it. `Department` and `Severity` stay closed because they are
product decisions, not customer schema.

## Ingest

```python
class RawUpload:
    department: Department
    period: str            # "2025-11"  (ISO year-month)
    filename: str
    sheet: str | None
```

## SourceRef: the one type worth reading carefully

Every downstream claim is anchored to one of these. Row and column alone cannot answer "which file,
which sheet, which import batch", and a month has four files, so a citation carries all of it:

```python
class SourceRef:
    batch: str                 # the import batch this came from
    department: Department
    period: str
    filename: str              # as uploaded, so the answer names something the user has
    sheet: str                 # worksheet for XLSX, empty for CSV
    row: int | None            # index into the cleaned rows
    column: str
    source_row: int | None     # original row number, kept stable through dedup and quarantine
    original_column: str       # original header text
    page: int | None           # text citations, for quoted documents
    paragraph: str
    excerpt: str               # capped length
    document_sha256: str
```

A validator makes the two citation shapes honest: a cell citation must state period, row and column;
a text citation must state file, digest and excerpt. Text coordinates never fake a spreadsheet cell.
`cite()` renders whichever form it is into one line a person can act on.

## Stage 1 — Sanitizer

```python
class ColumnSpec:
    name: str
    dtype: Literal["string", "number", "date", "bool"]
    unit: str | None
    semantic_hint: str | None

class Correction:
    source: SourceRef | None   # optional so older logs still load
    row: int
    column: str
    before: Any
    after: Any
    rule: str                  # "date_parse" | "unit_normalise" | "llm_typo_fix" | ...
    confidence: float          # 0..1
    reason: str

class CleanTable:
    department: Department
    period: str
    columns: list[ColumnSpec]
    rows: list[dict[str, Any]]
    corrections: list[Correction]
    quarantine: list[dict[str, Any]]   # rows we refused to guess at
    source_rows: list[int]
    filename: str
    sheet: str
    batch: str
    original_columns: dict[str, str]   # cleaned name -> as it was written
```

## Stage 2 — Resolver

```python
class Entity:
    id: str                # canonical id, e.g. "sku:A1"
    kind: EntityKind
    label: str
    aliases: list[str]     # every department-local name seen so far

LinkStatus = Literal["declared", "adjudicated", "unadjudicated"]

class Link:
    source: str            # Entity.id
    target: str
    relation: Relation
    confidence: float
    justification: str
    status: LinkStatus

class EntityGraph:
    entities: list[Entity]
    links: list[Link]
    unresolved: list[Link]         # below threshold, needs a human
```

`status` exists because "not judged yet" and "judged and uncertain" are different things, and a queue
that shows them as one sends the reviewer's attention to the wrong place. `declared` came from the
field dictionary and was never in doubt. `adjudicated` was judged by a model, so trust `confidence`.
`unadjudicated` means no verdict came back: its confidence is the candidate's starting value and means
nothing, so it is looked at first.

Confirmed links are persisted to mapping memory and applied automatically in later periods.

## Stage 3 — Evaluator

```python
class Evidence:
    period: str
    entity_id: str
    metric: str
    value: float
    comparison: str | None     # "vs 2025-10: +18%"
    sources: list[SourceRef]   # a capped sample, never the whole set
    source_count: int          # how many cells contributed, however few are listed
    baseline: str | None       # what it was compared against
    threshold: str | None      # what it crossed
    impact: str | None

class Finding:
    role: Department
    severity: Severity
    claim: str                 # one sentence, no hedging
    evidence: list[Evidence]   # must be non-empty
    suggested_action: str

class Tension:
    finding_a: Finding
    finding_b: Finding
    description: str           # why these two pull in opposite directions
```

`evidence` has a validator that raises on an empty list. A claim with nothing behind it is a
hallucination with good grammar, and the schema refuses it instead of displaying it quietly.
`baseline`, `threshold` and `impact` follow the PRD's requirement that a warning state what it was
compared against and what it crossed; absent means "not stated", not "none".

## Stage 4 — SOP & Flow

```python
class MasterTable:
    grain: Literal["month", "quarter", "year"]
    periods: list[str]
    rows: list[dict[str, Any]]
    unmatched_entities: list[str]   # labels that never reached the entity graph

class ApprovalCard:
    title: str
    owner: Department
    due: date
    findings: list[Finding]
    options: list[str]

class RiskReport:
    period: str
    findings: list[Finding]
    tensions: list[Tension]
    cards: list[ApprovalCard]
```

A row per spelling is what an incomplete dictionary looks like in the output. `unmatched_entities`
names those labels instead of letting the split read as two entities that legitimately exist.

## Quote

```python
class QuoteRequest:
    customer_id: str
    sku_id: str
    quantity: int            # must be positive
    requested_delivery: date

class QuoteRecommendation:
    floor_price: float       # below this we lose money
    target_price: float
    stretch_price: float
    margin_at_target: float
    payment_terms_days: int
    capacity_feasible: bool
    rationale: list[str]
```

These two models belong to the legacy simulator, where the model asserted the three price points.
The quotation path being built now does not use them: a quote sheet is declared in the field
dictionary and evaluated by the shared arithmetic, so its numbers come from cells, not from prose
([`20`](20-quotation-brief.md), [`21`](21-quotation-design.md)).

## Whole-pipeline envelope

```python
class PipelineResult:
    period: str
    clean_tables: list[CleanTable]
    graph: EntityGraph
    master_table: MasterTable
    risk_report: RiskReport | None
```
