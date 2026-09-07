# 12 — Delivery, Measurement and Controls (form content)

Fill-in content for the "Delivery, Measurement and Controls" submission form, ready to paste.

Before submitting: every Owner marked *(TBC)* needs a real name, and the two baselines flagged
below need real figures. Every other number in this form is measured, with its source in brackets.

---

## DATA, TOOLS & OPERATING CONSTRAINTS

| Data or Document | Source | Owner | Access Status | Privacy or Quality concern |
| --- | --- | --- | --- | --- |
| Four monthly departmental reports (production / procurement / finance / marketing; CSV·XLSX) | Manual export by each department | Departmental data owners *(TBC)* | Not yet obtained — de-identified samples stand in | Contains customer names and amounts. Four sheets maintained by four different people, so any one of them can be tampered with; treated as untrusted input throughout |
| OA field dictionary (department → column → entity type) | Export from OA, written by a person before anything is uploaded | Master-data owner *(TBC)* | **Not obtained**; the demo runs on a synthetic dictionary the team wrote | Without a declaration the delivered path refuses and marks the batch `needs_configuration`; only the legacy resolver still falls back to English column-name guessing (#32), which is itself a guess |
| Bill of materials (SKU ↔ raw material) | ERP / master data | Production or process owner *(TBC)* | Not obtained | Nothing else declares this relationship — co-occurrence cannot infer it (measured, see below). Missing allocation ratios mean unit cost cannot be computed, leaving the quote floor unfounded |
| Chart-of-accounts mapping (SKU ↔ GL account) | Finance | Finance owner *(TBC)* | Not obtained | Same: the `books_to` relation depends on this declaration |
| Demo sample dataset `data/samples/*.csv` | Authored by the team (fictional, not real business data) | This team | In the repository | **Must never be presented as real business figures.** Contains deliberately planted data defects for the demo |
| Poisoned dataset (prompt-injection cases) | Authored by the team | This team | In the repository: `data/poisoned/<industry>/` plus the shared guard case file | Security testing only; must not be mixed into the normal demo dataset |
| Field dictionary file `data/mappings/field-dictionary.yaml` | Filled from the OA export above | Master-data owner *(TBC)* | Format defined, content pending | Once non-empty it is followed exactly — undeclared columns are ignored rather than guessed at |

---

## AI MODELS & TOOLS

> The Status column is the honest part of this form. The rest describes the target system, so
> several rows are commitments rather than descriptions, and a judge may ask to see any row
> demonstrated. Built means it is in `main` with tests; Partial means it exists but does not meet
> the description; Committed means it is not written yet.

| Model/Tool | Role in the proposal | Status (as of 2026-09-07) | Operating Constraint |
| --- | --- | --- | --- |
| DeepSeek Harness `dsh` 0.1.2rc1 | Agent runtime. The default path is the official `dsh web` plus local Host/Client plugins; the Python SDK drives the bundled CLI as a subprocess over JSON-RPC on stdio (timings in [`00-status.md`](00-status.md), the dsh facts table) | **Built** for the delivered path: sessions, native approval, typed tools and official subagent fan-out are all in use. The legacy wrapper that used dsh as a completion provider still exists and is off by default (#25, #38) | **Every published release is a prerelease and the project states breaking changes are expected** → pinned to `==0.1.2rc1`, never a range. A single runtime cannot interleave turns, so concurrent calls are serialised behind a lock |
| `deepseek-v4-flash` (provider `deepseek-official`) | The judgement layer for all four agents: adjudicating mappings, writing findings and quote rationale | **Built** for the delivered review path: metrics are computed by Python from the frozen dictionary, and the model only interprets them, picks the declared action and explains the threshold comparison (#13). Free text is labelled as model suggestion | **Interprets and judges; never computes.** Input must pass the trust boundary first. Returns free text with no schema parameter, so structured output is validated locally — an unparseable reply raises rather than degrading to an empty result |
| Mock provider (built in, deterministic) | Default backend for CI and rehearsal; runs the whole pipeline offline | **Built** — but its output is placeholder text, so it is a fallback, not the rehearsal target | No network, no key. The suite runs in this mode, so the demo does not bet on connectivity (counts: `00-status.md`) |
| pandas 2.2 | Cleaning, metric aggregation, Master Table assembly | **Built** — all three run in Python against declared formulas; nothing a rule can compute is handed to the model | Deterministic; results never pass through a model. Anything a rule can compute is not given to the model |
| rapidfuzz 3.10 | **Only** merges aliases of the same entity (`SKU-A1` / `sku-a1` / `SKU A1`) | **Built** — locked by test | **Never used to discover links between different entities.** Measured cross-department similarity is 0–35.3 (SKU-A1 × RM-Alu-6061 = 35.3), below any usable threshold; a test locks this constraint in place |
| Purpose-built typed tools | Read table, aggregate metric, look up field dictionary, profile columns, open and close a review, record a mapping decision | **Built** — seven tool modules in `plugins/src/tools/` (`batch-summary`, `list-metrics`, `aggregate-metric`, `lookup-field-dictionary`, `profile-batch`, `review-batch`, `confirm-mapping`) (#27) | All schema-typed. The model reaches data only through tools, never raw rows |
| FastAPI (Python) | Private domain service behind the plugins | **Built** for that role — batches are persisted and immutable, and one-use approval receipts are replay-checked. The legacy synchronous `/analyze` with in-memory results (#12) is off by default | No authentication; internal and demo use only, never exposed publicly. Binds 127.0.0.1 unless explicitly configured otherwise |
| dsh web + Client plugins | The operator UI, customised rather than rebuilt | **Built** — import/data panel, report cards, business-state tab and approval-note input register through official slots (#40) | Custom tool cards register into the `tool.call.toolview` slot; presenters must be pure functions of their arguments because they also run on session replay |

---

## AGENT / WORKFLOW ROLES

| Role | Responsibility | Status | Input | Output | Escalate when |
| --- | --- | --- | --- | --- | --- |
| **Data Sanitizer** | Repair formats, types, duplicates and shifted columns; log every change with original value, new value, rule, confidence and reason | **Built** for the declared defect classes, including duplicate rows and shifted rows, each logged and covered by tests (#16). Single-sheet XLSX is accepted; multi-sheet is refused until an explicit sheet and header choice exists (#47) | Raw departmental CSV / XLSX | `CleanTable` + `CorrectionLog` + quarantined rows | A critical field (amount / customer / SKU / approval) is missing → **never filled in**; the row is quarantined and downstream results are marked incomplete |
| **Semantic Resolver** | Build cross-department entity mappings from three sources in descending order of trust: OA dictionary declarations → row co-occurrence → model adjudication of the residue | **Built** — the three-source order works and a confirmed link is stored in mapping memory (#29). The month-2 saving it should produce has not been measured, because the sample set covers one month | `CleanTable` ×4 + field dictionary | `EntityGraph` (links + unresolved) | Confidence < 0.75 → human queue, never auto-published. `consumes` / `books_to` are empty because no sheet contains both sides → escalate to the master-data owner for a dictionary entry |
| **Multi-Role Evaluator** | Four concurrent role analyses: production, finance, procurement, marketing | **Built** — four official sub-sessions run concurrently over tool-computed metrics, each child submits `structured_output`, and the host validates role, values, units, status, action and citations; a failed role leaves the report partial instead of inventing a judgement (#13, #26) | `EntityGraph` + metrics computed by tools | `Finding[]` (evidence enforced by schema) + `Tension[]` | Two roles reach opposing conclusions about the same entity → emitted as a Tension **for a human to settle; the system never reconciles it automatically** |
| **SOP & Flow Engine** | Assemble the monthly Master Table, risk report and approval cards | **Partial** — the Master Table now joins only on a dictionary-declared key and refuses to merge without one (#44, PR #60). Roll-up folding is declared per measure. What is still missing is a formal sign-off workflow: today the report names the responsible role per check instead of issuing an approval card | `Finding` + `CleanTable` | `MasterTable` + `RiskReport` + `ApprovalCard` | A critical-severity finding appears → an approval card is raised with an owning department and a deadline |
| **Dynamic Quote Simulator** | Simulate price and payment terms across material cost × capacity × customer AR history | **Partial** — the price band is no longer asserted: a declarative evaluator computes Decimal cost and price drafts from declared facts and refuses, naming what is missing (#7 at the arithmetic layer). Contract extraction from real documents and multi-scenario comparison are not built | Enquiry + Master Table + Findings | Price band (floor computed deterministically) + payment-term options + sensitivities | Cost, capacity or FX basis is missing → **formal submission refused**, draft allowed. Never sent externally under any condition |

---

## INTEGRATIONS AND MANUAL FALLBACK

Integration scope is deliberately narrow. Upstream is manually exported CSV or XLSX: no ERP, MES,
CRM or procurement connectors. Downstream produces screens and files only; it writes back to no
business system and connects to no email, CRM or customer channel. That is the structural guarantee
that a quote cannot be sent automatically, rather than a flag someone could flip. The only external
dependency is model access, via the dsh subprocess to the DeepSeek API.

**Three fallback layers, degrading in steps rather than all-or-nothing:**

1. **dsh runtime fails or ships a breaking change** → change one environment variable
   (`LLM_PROVIDER=mock`, or a direct API provider). No agent code changes: `Orchestrator` is a
   plain async method carrying no framework dependency, and that seam exists for this reason.
2. **Model or network unavailable** → the deterministic mock provider replays the whole
   pipeline offline and the suite still passes. **Rehearsal runs in this mode by default**, so the
   demo does not depend on connectivity.
3. **All automation fails** → the intermediate artefacts are human-readable by design:
   `CorrectionLog`, `EntityGraph` and the Master Table are all tables. The business continues
   with its existing monthly process. **Source files are never overwritten**, so a failure costs
   time, not data.

---

## SUCCESS MEASURES

| Metric | Baseline | Target | How measured | Review period |
| --- | --- | --- | --- | --- |
| End-to-end review duration | measured on the delivered native path in [`00-status.md`](00-status.md), the single source for every measured number | hold under a minute on the sample set | Time the review from `review_context` to the saved report | Every round |
| Semantic mappings produced | on the sample set: 15 entities, 1 confirmed relation, 6 awaiting adjudication, and `consumes` / `books_to` zero because no sheet contains both sides (counts in `00-status.md`) | All four relation types non-empty | Count the review output per batch | When the real dictionary arrives |
| Conclusion traceability | **100%** (schema rejects any finding without evidence) | Hold at 100% | Spot-check findings back to the source file row | Weekly |
| Prompt-injection block rate | guard in place and tested against a shared deny/allow case set; not proof that every injection is blocked | 100% of the adversarial cases we ship, blocked at dispatch and logged | `python -m bridgeflow.eval` plus the guard tests at real dispatch. There is no CI: the project excluded it, so this is run by hand and recorded in `00` | Every release candidate |
| Golden-path eval pass rate | 24/24 on the held-out acceptance set (three industries: load, metrics, five defect classes, injection) | 100% | `python -m bridgeflow.eval`, run by hand; the acceptance set is not read during development | Every release candidate |
| Correction-log completeness | **100%** — every correction carries a rule and a confidence; counts in the sanitizer facts table of [`00-status.md`](00-status.md) | Hold at 100% | `CorrectionLog` entries vs actual changes | Weekly |
| Cross-month confirmation effort | no data: memory is built, but the sample set covers one month, so the saving has never been measured | Month 2 confirmations < 30% of month 1 | Compare two consecutive monthly runs | When a second month of files exists |
| Manual monthly reconciliation time | ⚠️ **Baseline needed from the business** | 50% below baseline | Timed comparison against current process | Post-delivery |

The last row cannot be verified without a baseline. Before submitting, ask the business how many
person-days month-end reconciliation actually takes today; otherwise "50% reduction" is a slogan.

---

## RISKS, GUARDRAILS AND HUMAN APPROVAL

| Risk | Consequence | Preventive Control | Human Owner |
| --- | --- | --- | --- |
| **Prompt injection** — spreadsheet cell content read as instruction | Findings manipulated: a critical risk relabelled as info, and an approver signs off on a false conclusion | Input trust boundary at the host: the shells are removed by profile patch, and `plugins/src/guards/untrusted-input.ts` denies instruction-shaped tool arguments monotonically at dispatch, so a later listener cannot argue the refusal away. Structured results are validated against the batch's frozen contract, and the adversarial cases are replayed by hand (no CI by project decision) | Technical lead *(TBC)* |
| **Wrong entity merge** | Cost, order and capacity joins corrupted; the whole Master Table is wrong in a way that is hard to notice | Confidence < 0.75 goes to a human queue; links come only from declarations and row co-occurrence, **never string similarity** (locked by test); mapping changes never silently recompute published results | Master-data owner *(TBC)* |
| **Critical field auto-filled** | Finance and quote figures distorted | Amount / customer / SKU / approval fields are never auto-filled; the row is quarantined and downstream results marked incomplete | Data administrator *(TBC)* |
| **Agent asserts a conclusion with no basis** | The business cannot approve it, or trusts something false | `Finding` enforces non-empty evidence at the schema level — an unevidenced conclusion is **rejected, not shown with a caveat** | Technical lead *(TBC)* |
| **Quote used beyond its authority** | Wrong price, payment terms or delivery date promised to a customer | No sending channel is integrated at all (structural); formal submission refused without cost and capacity basis; nothing is marked externally usable without approval | Sales lead + approver *(TBC)* |
| **Prerelease dsh dependency breaks** | The demo does not run on the day | Pinned to `==0.1.2rc1`; offline mock fallback; **rehearsal runs on mock** | Technical lead *(TBC)* |
| **OA field dictionary arrives late** | Week 2 core capability degrades; two relation types cannot be built | Listed as an explicit week-2 prerequisite with a fallback (co-occurrence relations only, declared ones stubbed from sample BOM); 2 dev-days of buffer held | PM *(TBC)* |
| **Demo data mistaken for real business data** | False operating figures circulate | All sample data is fictional and labelled as such in the repository; exports carry data version and source | PM *(TBC)* |

---

## HUMAN APPROVAL POINTS

Four mandatory checkpoints, in ascending order of risk. Each one blocks progress until it is
answered, and none can be skipped once confirmed:

1. **Data-repair confirmation** — data administrator
   Deterministic format conversions run automatically but are all logged. **Missing critical
   fields (amount / customer / SKU / approval) must be handled by a person**; until they are,
   every downstream result is marked incomplete.

2. **Mapping publication** — master-data owner
   Mappings below the confidence threshold **cannot be auto-published**. One human confirmation
   becomes a versioned rule reused in later months — this is where "month 2 costs less than
   month 1" comes from. Changing a mapping flags the affected months and lets a person decide
   whether to recompute.

3. **Risk-finding disposition** — owning department head
   Findings can be confirmed, rejected, assigned, annotated or closed, with the operator and
   timestamp retained. **The system never rewrites the underlying facts** — disposition changes
   the status of a conclusion, not the data.

4. **External use of a quote** — authorised approver
   Nothing is marked externally usable without approval. The system does not send, and does not
   commit to delivery dates or credit limits.

Plus a weekly sign-off: **each week produces one usable decision, and the business signs it off
before the next week starts.**

Four things the system will never do automatically. These are design red lines, not configuration:
overwrite a source file · fill a critical field · merge a low-confidence entity · send a quote.