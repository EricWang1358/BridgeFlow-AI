# 10 — Proposal (3-week hackathon build)

> This is the scope and effort estimate as proposed. It is not the build order any more.
> [`13-golden-standard.md`](13-golden-standard.md) measured that rubric items 2, 3, 5 and 7 were all
> failing for one shared reason: dsh had been put in the wrong place. Fixing that root cause once
> fixes five items, so week 1 became "put the architecture back" rather than "data foundation".
> The self-built frontend and the hand-written orchestrator were both dropped.
> Work order lives on the [project board](https://github.com/users/EricWang1358/projects/1);
> current status lives in [`00`](00-status.md).
>
> Renumbered from "07"; that slot holds the business PRD ([`07-prd-v0.1.md`](07-prd-v0.1.md)).
> It was revised against measured results and the judging rubric; the review that drove the six
> changes is [`11-proposal-review.md`](11-proposal-review.md).

Project: BridgeFlow AI, turning four messy monthly spreadsheets (production, procurement, finance,
marketing) into one aligned Master Table, with risk warnings and dynamic quotes.

- Team: 2 full-stack developers + 2 PMs. Timeline: 3 weeks. Total effort: 52 person-days
  (28 dev of 30 available, 2 days held as buffer; 24 PM of 30).
- Build framework: DeepSeek Harness (`dsh`). The Python SDK drives the bundled `dsh` runtime as a
  subprocess over JSON-RPC on stdio, with one typed tool per data operation
  (see [`06-deepseek-harness.md`](06-deepseek-harness.md)). `LLM_PROVIDER=mock` keeps the whole
  pipeline runnable offline.
- Starting point: the scaffold ran the pipeline end to end and dsh was verified live, so integration
  was de-risked (timings in [`00`](00-status.md)).
- One correction worth keeping in the record: the original plan blamed a 627-second run on whole
  tables being pasted into prompts, and scheduled tool-isation in week 2 as the cure. Measurement
  (#25) showed the prompts were about 590 characters; the time went on dsh running a dozen `bash`
  steps over the repository per call, because an agent runtime was being used as a completion
  provider. Taking the resolver off it cut one adjudication from 12-212s and ~7,100 tokens of tool
  output to 3.6s and 707 tokens. Moving metric computation into tools is still week-1 work, but it
  is the answer to rubric item 3, not to the throughput problem.

---

## Scope and staged approach

Each week produces one usable decision, and each week ends demoable with an explicit sign-off.
Sign-offs are the human checkpoints: nothing advances to the next stage unattended.

The three week sections below are the original plan. The effort estimates still hold; the order does
not. How they moved:

| Original | Now | Why it moved |
| --- | --- | --- |
| W1 data foundation + Sanitizer + trust boundary | W1 keeps the trust boundary, the rest sinks later | The trust boundary is rubric item 5 and had a known live hole. Contract freeze (#14) stayed in W1; Sanitizer feature work (#1 / #16) moved to W3 |
| W2 resolver + evaluator + typed tools | Typed tools and the evaluation layer moved up to W1 (#27, #13) | They are the shared root cause of rubric items 2, 3, 5 and 7 |
| W2 mapping confirmation + cross-month memory | unchanged (#29, #30, #39) | Depends on the OA field dictionary (#32), always week 2 material |
| W3 quoting + eval + demo | unchanged (#28, #31, #41) | Closing week does not move |
| (not in the original plan) | W2 adds "replace the orchestrator" (#38) | It is the direct answer to rubric item 2 |

Per-issue detail is on the board.

### Week 1 - "Mess in, clean out": data foundation, Sanitizer, input trust boundary

| | |
| --- | --- |
| Scope | Freeze and extend the v1 data contracts and the metric dictionary (schemas already exist and pass tests, so this is a freeze, not a build). Author four deliberately messy monthly sample files with known defects, plus a poisoned variant. Build the Data Sanitizer: rules first, model only for the residue; every fix logged with rule and confidence; unfixable rows quarantined, never dropped. Establish the input trust boundary: spreadsheet cell content is data, never instruction, delimited and provenance-marked before it reaches any prompt, with output validated against the tainted input. Upload UI with live correction log. |
| Deliverables | Frozen schemas (CleanTable, CorrectionLog, EntityGraph, Finding, MasterTable); messy demo dataset plus one poisoned dataset; working Sanitizer as a `dsh` tool; injection defence with a passing attack case; Import Center UI; sign-off on the defect test-case set. |
| Assumptions | Sample files stand in for production data. The OA field dictionary is a week-2 dependency, not a week-1 one. The mock LLM provider keeps runs deterministic and offline; one real provider key is available for live runs. No auth or permissions in scope beyond least-privilege on the runtime itself. |
| Estimate | 19 person-days (10 dev + 9 PM: dataset authoring including adversarial cases, contract freeze, demo narrative). |

Usable decision: four messy files in, typed clean tables plus a reviewable correction log out, with
a demonstrated refusal to obey instructions planted in the data.

### Week 2 - "One table, four lenses": Semantic Resolver, Multi-Role Evaluator, Master Table

| | |
| --- | --- |
| Scope | Build the core. The Semantic Resolver joins SKU to raw material, GL account and capacity from three sources in descending order of trust: declared in the OA field dictionary, then co-occurrence within a row, then model adjudication of the residue, never from how identifiers are spelled. Low-confidence links go to a one-click human queue and persist as versioned mapping rules, so month 2 costs a fraction of month 1. Roll day and week source data onto a monthly axis (sum / average / period-end per metric). The Multi-Role Evaluator runs four role analyses concurrently (capacity, margin and AR, price drift, customer tiering), with metrics computed by typed tools rather than by the model reading raw rows; every finding must cite source rows. SOP Engine v1 assembles the monthly Master Table. |
| Deliverables | Resolver and Evaluator driven through `dsh` with a typed tool per data operation (read table, aggregate metric, look up field dictionary, compute capacity load); mapping-confirmation screen; cross-month mapping memory; Master Table with drill-down to source rows; four role panels; the "Acme tension" demo beat with every number traceable. |
| Assumptions | Dependency: the OA field dictionary. Auto-accept rate is a function of its coverage, not a tunable threshold: `consumes` (SKU to material) and `books_to` (SKU to GL account) yield zero links at any threshold, because no single sheet contains both sides; they must be declared, not inferred (`data/mappings/README.md`). If the dictionary slips, week 2 ships with co-occurrence relations only and the declared ones are stubbed from sample BOM data. Metric formulas frozen in week 1, no new metrics mid-week. Per-metric aggregation configurability is deferred; week 2 ships fixed roll-up rules. Findings are advisory: no write-back, no auto-actions. |
| Estimate | 16 person-days (10 dev + 6 PM: mapping ground truth, metric sign-off). |

Usable decision: one aligned Master Table with evidence-backed findings a person can act on.

### Week 3 - "Decide and quote": Quote Simulator, evaluation, demo

| | |
| --- | --- |
| Scope | Quote Simulator: enquiry in, simulation over material cost, capacity and customer AR history, floor / target / stretch price band plus payment-term options with sensitivities shown, where the floor is computed deterministically rather than asserted by the model. Approval gate in the UI: unapproved plans cannot be exported and nothing is auto-sent. Risk report and approval cards. Evaluation suite: golden-path cases (the Acme order must be judged loss-making; the aluminium rise must surface) and adversarial cases (planted instructions, missing critical fields, contradictory departments, empty sheet). Decision tracing: per-agent call, duration, tokens, retries. Acceptance pass, demo polish (streaming progress, offline mock fallback), full rehearsal. |
| Deliverables | Quote Simulator driven through `dsh`; approval gate; risk report and approval cards; eval suite passing; decision trace visible in the demo; acceptance spot-checks passed (traceability, three-scenario comparison); rehearsed six-minute demo. |
| Assumptions | Approval flow is simulated in the UI only (no email, no CRM). XLSX and PDF export are out of scope: they score nothing against the rubric and the days buy the eval suite instead. Also out of scope: ERP connectors, multi-tenant auth, write-back, mobile, i18n, currency and unit normalisation. The demo runs on the committed sample dataset, with one live-model rehearsal and a mock fallback ready. |
| Estimate | 17 person-days (8 dev + 9 PM: eval case authoring, acceptance, pitch deck, rehearsal). |

Usable decision: a recommended quote band and payment terms behind an explicit approval gate, with
the evidence for every number and a suite that shows it holds under attack.

---

## Solution overview

BridgeFlow AI is a multi-agent engine built on DeepSeek Harness. Typed Pydantic contracts sit between
every stage, each data operation is a tool the agents call, and the deterministic arithmetic never
passes through a model.

1. Data Sanitizer. Rules first, model for the residue. Fixes typos, formats and duplicates; every
   correction logged with rule and confidence; unfixable rows quarantined, never dropped. Cell
   content is treated as untrusted data, never as instruction.
2. Semantic Resolver (core). Joins what never matched across departments from declarations and row
   co-occurrence rather than string similarity; unifies day, week and month onto a monthly axis;
   learns from human confirmations, so month 2 needs a fraction of month 1's effort.
3. Multi-Role Evaluator. Four concurrent role lenses over the same data. Metrics are computed by
   tools and only interpreted by the model; no finding without cited evidence; cross-role conflicts
   surface as tensions for a human instead of being auto-resolved.
4. SOP & Flow Engine plus Quote Simulator. Monthly Master Table, risk report and approval cards; on
   demand, a simulated price band and payment terms with sensitivity disclosure, behind an explicit
   approval gate and never sent automatically.

**Why a fixed pipeline rather than a planning agent.** This is a deliberate trade-off, not a missing
capability. Financial figures have to be auditable, reproducible and attributable: an approver cannot
sign a number that two runs derive differently. The stages are fixed; the judgement inside each stage
is where the model earns its place.

**Engineering.** Python 3.12, FastAPI and pandas behind typed dsh tools. The operator UI is dsh web
customised through Client plugins, not a self-built app. A pluggable LLM provider layer with a
deterministic mock default keeps rehearsal reproducible, though mock output is placeholder text, so it
is a fallback rather than a demonstration. Human-in-the-loop gates sit where the risk is: critical
fields are never auto-filled, low-confidence mappings are never auto-published, quotes are never
auto-sent. Those gates protect against model error, not against hostile input, which is why the input
trust boundary belongs in week 1.
