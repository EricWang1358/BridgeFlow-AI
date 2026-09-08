# 02 — Agent contracts

> Reference document. What is still true here is the input and output contract of each stage.
> For where dsh sits in the architecture, read [`13`](13-golden-standard.md); for measured numbers,
> [`00`](00-status.md). This file deliberately carries no numbers.
>
> The stage names below come from the original Python pipeline. The delivered entry point runs the same
> four stages as fixed domain steps plus one native subagent per department;
> [`17`](17-business-mvp-acceptance.md) describes that path.

## Pipeline

```text
Upload (n files)
   → Sanitizer      → CleanTable[]      + CorrectionLog[]
   → Resolver       → EntityGraph       + UnresolvedLink[]   (human-in-the-loop)
   → Evaluator ×4   → Finding[]          (one set per role, run concurrently)
   → SOP & Flow     → MasterTable + RiskReport + ApprovalCard[]
        └ (on demand) QuoteSimulator → QuoteRecommendation
```

Every stage consumes and emits a typed Pydantic model from `bridgeflow.schemas` (see
[`03`](03-data-contracts.md)). Only the Sanitizer reads raw files.

### 1. Data Sanitizer

- **In:** raw CSV or XLSX, one per department per month.
- **Out:** `CleanTable` (normalised column names, typed columns, ISO dates) plus a `CorrectionLog`
  recording what changed, the rule that changed it, a confidence and a reason.
- **Method:** rules first (dtype inference, date parsing, unit normalisation, duplicate and
  shifted-header detection); the model only handles what rules cannot, such as ambiguous header
  naming or free-text category values.
- **Invariant:** never drop a row silently. Rows we cannot fix go to `quarantine`, which is shown
  in the UI rather than quietly excluded.

### 2. Semantic Resolver

- **In:** all `CleanTable`s for a period, plus the field dictionary.
- **Out:** an `EntityGraph` linking SKU, raw material, GL account, capacity unit and customer,
  on a normalised time axis (weekly procurement and daily production both roll up to month).
- **Method:** candidates arrive in descending order of trust: what the field dictionary declares,
  then what the rows put together (co-occurrence), then the model adjudicating the residue. Never
  from how an identifier is spelled. `SKU-A1` and the aluminium it consumes share no characters;
  measured similarity is 35.3, and string matching produced zero links (issue #24). Similarity is
  used only to merge aliases of one entity, and a test locks that down.
- Links below the confidence threshold become unresolved and a person confirms them once. That
  confirmation is stored as a mapping rule, so month 2 needs less human input than month 1.
  This is the part worth the most: everything downstream depends on these joins being right.

### 3. Multi-Role Evaluator

Four role views over the same graph, run concurrently:

| Role | Question it answers | Example finding |
| --- | --- | --- |
| Production | order trend, capacity utilisation, headroom | "Line 2 at 94% utilisation; November orders exceed capacity by 12%" |
| Finance | loss-making projects, AR ageing, bad debt | "Project X gross margin −4% after material rise; Acme AR at 92 days" |
| Procurement | material price trend, purchase cost drift | "Alu-6061 +18% quarter on quarter; current quotes still priced at Q1 cost" |
| Marketing | customer tiering under a capacity constraint | "Tier-C customer consuming 30% of Line 2 at the lowest margin" |

Each emits `Finding{role, severity, claim, evidence[], suggested_action}`. Evidence must cite
specific cells, and a finding with no evidence is refused at the schema layer, not shown with a
caveat. When two roles disagree, the disagreement is surfaced as a `Tension`; the system does not
reconcile it.

### 4. SOP & Flow Engine

Builds the Master Table (the one aligned wide table), renders the risk report and raises approval
cards: a discrete decision with an owner, a deadline and the findings that justify it.

### 5. Quote Simulator (sub-feature)

Given an enquiry (customer, SKU, quantity, requested delivery), it simulates material cost curve,
capacity availability and customer AR history, and returns a price band, payment terms and the
margin at each point of the band. The floor has to come from arithmetic, not from the model
asserting a number; that is issue #7 and the reason the current quotation path is declarative
([docs/20](20-quotation-brief.md)).

## LLM provider layer

`bridgeflow/llm/` defines one protocol:

```python
class LLMProvider(Protocol):
    async def complete(self, *, system: str, messages: list[Message],
                       schema: type[BaseModel] | None = None) -> Response: ...
```

Adapters live in `llm/providers/`: `mock` (deterministic, the default for offline tests) plus
`deepseek`, `anthropic`, `openai_compatible`, `hermes`, `openclaw` and `dsh`. A provider is chosen
by `LLM_PROVIDER` and can be overridden per agent (`LLM_PROVIDER_SANITIZER=deepseek`), which is how
you run a cheap model for cleaning and a strong one for judgement.

Two cautions. First, putting dsh behind this protocol is the mistake recorded in
[`13` §3](13-golden-standard.md): dsh is the runtime, not a completion backend.
Second, mock output is placeholder text; it proves the code does not crash and nothing else.

## Frontend

Not a self-built app. The UI is dsh web customised through Client plugins; the surfaces it has to
cover are import and correction review, the master table with role-tagged findings, and the quote
declaration view. Current state and boundaries: [`17`](17-business-mvp-acceptance.md),
[`18`](18-native-captain-and-state.md).
