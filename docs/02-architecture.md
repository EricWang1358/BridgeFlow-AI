# 02 — Architecture

> **部分内容已过时。** 语义对齐一节仍描述已废弃的字符串相似度候选生成；
> 整体架构以 [`13-golden-standard.md`](13-golden-standard.md) 为准。

## Pipeline

```
Upload (n files)
   → Sanitizer      → CleanTable[]      + CorrectionLog[]
   → Resolver       → EntityGraph       + UnresolvedLink[]  (human-in-the-loop)
   → Evaluator ×4   → Finding[]         (one set per role, run concurrently)
   → SOP & Flow     → MasterTable + RiskReport + ApprovalCard[]
        └ (on demand) QuoteSimulator → QuoteRecommendation
```

Every stage consumes and emits a typed Pydantic model from `bridgeflow.schemas`. No stage
reads raw files except the Sanitizer, and no stage calls an LLM directly — they all go
through `bridgeflow.llm.get_provider()`.

## Agent responsibilities

### 1. Data Sanitizer Agent
- **In:** raw CSV/XLSX, one per department per month.
- **Out:** `CleanTable` (normalised column names, typed columns, ISO dates) plus a
  `CorrectionLog` recording every change with a reason and confidence.
- **Method:** rules first (dtype inference, date parsing, unit normalisation, duplicate
  and shifted-header detection), LLM only for the residue rules cannot handle —
  ambiguous header naming, free-text category values, obvious typos in entity names.
- **Invariant:** never silently drops a row. Unfixable rows go to a `quarantine` table
  surfaced in the UI.

### 2. Semantic Resolver Agent (core)
- **In:** all `CleanTable`s for a period.
- **Out:** an `EntityGraph` linking `SKU ↔ RawMaterial ↔ GLAccount ↔ CapacityUnit`, plus a
  normalised time axis (weekly procurement and daily production both roll up to month).
- **Method:** blocking + fuzzy string match to generate candidates, LLM to adjudicate with
  a confidence score and a short justification. Links below the confidence threshold become
  `UnresolvedLink`s that the user confirms once — the confirmation is persisted as a
  mapping rule, so month 2 needs far less human input than month 1.
- **This is the moat.** Everything else is downstream of getting these joins right.

### 3. Multi-Role Evaluator Agent (core)
Four role prompts over the same `EntityGraph`, run concurrently:

| Role | Question it answers | Example finding |
| --- | --- | --- |
| Production | Order trend, capacity utilisation, headroom | "Line 2 at 94% utilisation; Nov orders exceed capacity by 12%" |
| Finance | Loss-making projects, AR ageing, bad-debt risk | "Project X gross margin −4% after material rise; Acme AR at 92 days" |
| Procurement | Material price trend, purchase cost drift | "Alu-6061 +18% QoQ; current quotes still priced at Q1 cost" |
| Marketing | Customer tiering under capacity constraints | "Tier-C customer consuming 30% of Line 2 at lowest margin" |

Each emits `Finding{role, severity, claim, evidence[], suggested_action}`. Evidence must
cite concrete rows from the Master Table — a finding with no evidence is dropped. Findings
that conflict across roles are surfaced as a *tension*, not resolved automatically.

### 4. SOP & Flow Engine
- Builds the month/quarter/year `MasterTable` (the single aligned wide table).
- Renders the risk report and generates `ApprovalCard`s — a discrete decision with owner,
  deadline and the findings that justify it.

### ✨ Dynamic Quote Simulator (sub-feature)
Given an enquiry (customer, SKU, quantity, requested delivery), simulates:
`material cost curve × capacity availability × customer AR history` and returns a
recommended price band, payment terms, and the margin at each point of the band.

## LLM provider layer

`bridgeflow/llm/` defines one interface:

```python
class LLMProvider(Protocol):
    async def complete(self, *, system: str, messages: list[Message],
                       schema: type[BaseModel] | None = None) -> Response: ...
```

Adapters live in `llm/providers/`: `mock` (deterministic, default), plus stubs for
`hermes`, `deepseek`, `openclaw` and `anthropic`. Selected by the `LLM_PROVIDER` env var,
and overridable **per agent** (`LLM_PROVIDER_SANITIZER=deepseek`) so we can run a cheap
model for cleaning and a strong one for evaluation.

> **Open question:** the exact SDK/endpoint for `hermes`, `deepseek-harness` and `openclaw`
> is not yet confirmed. The adapters are written against the interface with `NotImplemented`
> bodies — filling them in should not require touching any agent code.

## Frontend

Next.js + TypeScript. Three screens:
1. **Upload & Sanitize** — drop files, see the correction log, resolve quarantined rows.
2. **Master Table & Risks** — the aligned table, filterable by period, with role-tagged
   findings down the side.
3. **Quote Simulator** — enquiry form, price-band chart, recommendation card.
