# 10 — Proposal (3-week hackathon build)

> Renumbered from "07" — that slot holds the business PRD ([`07-prd-v0.1.md`](07-prd-v0.1.md)).
> Review notes against measured results: [`11-proposal-review.md`](11-proposal-review.md).

Project: **BridgeFlow AI** — turn four messy monthly spreadsheets (production / procurement /
finance / marketing) into one aligned Master Table, with risk warnings and dynamic quotes.

- Team: 2 full-stack developers + 2 PMs · Timeline: 3 weeks · Total effort: **51 person-days**
- Build framework: **DeepSeek Harness (`dsh`)** — one plugin per agent, driving the Python
  backend over HTTP (see `docs/06-deepseek-harness.md`); the plain orchestrator stays as fallback.
- Starting point: scaffold already runs the pipeline end-to-end on mock data — timeline de-risked.

---

## Scope and Proposed Approach

The scope is staged so that **each week produces a usable decision or increment**, and every
week ends demoable with an explicit sign-off.

### Week 1 — "Mess in, clean out": data foundation & Data Sanitizer

| | |
| --- | --- |
| **Scope** | Freeze v1 data contracts and the metric dictionary. Author four deliberately messy monthly sample files with known defects. Build the Data Sanitizer: rules-first, LLM only for the residue; every fix logged with rule + confidence; unfixable rows quarantined, never dropped. Upload UI with live correction log. |
| **Deliverables** | Typed schemas (CleanTable, CorrectionLog, EntityGraph, Finding, MasterTable) · messy demo dataset · working Sanitizer behind a `dsh` plugin · Import Center UI · sign-off on the defect test-case set. |
| **Assumptions** | Sample files stand in for real data (none available in-window). Mock LLM provider keeps runs deterministic and offline; one real provider key available for live runs. No auth / permissions in scope. |
| **Estimate** | **18 person-days** (10 dev + 8 PM: dataset authoring, contract freeze, demo narrative). |

**Usable decision:** four messy files in → typed clean tables + reviewable correction log out.

### Week 2 — "One table, four lenses": Semantic Resolver + Multi-Role Evaluator + Master Table

| | |
| --- | --- |
| **Scope** | Build the core: Semantic Resolver joins SKU ↔ raw material ↔ GL account ↔ capacity, with confidence scores; low-confidence links go to a one-click human queue and persist as versioned mapping rules. Multi-Role Evaluator runs four role analyses concurrently (capacity, margin/AR, price drift, customer tiering) — every finding must cite source rows. SOP Engine v1 assembles the monthly Master Table. |
| **Deliverables** | Working Resolver + Evaluator behind `dsh` plugins · mapping-confirmation screen · Master Table with drill-down to source rows · four role panels · the "Acme tension" demo beat, every number traceable. |
| **Assumptions** | PMs confirm mapping ground truth on sample data; threshold tuned to ≥90% auto-accept. Metric formulas frozen from week 1 — no new metrics mid-week. Findings are advisory: no write-back, no auto-actions. |
| **Estimate** | **15 person-days** (10 dev + 5 PM: ground-truth confirmation). |

**Usable decision:** one aligned Master Table with trusted, evidence-backed findings.

### Week 3 — "Decide and quote": Dynamic Quote Simulator & demo

| | |
| --- | --- |
| **Scope** | Quote Simulator: enquiry in → simulation over material cost × capacity × customer AR history → floor/target/stretch price band + payment-term options, with sensitivities shown. Approval gate in-UI; unapproved plans cannot be exported; nothing is auto-sent. Risk report + approval cards, XLSX export matching the screen. Acceptance pass, demo polish (streaming progress, offline mock fallback), full rehearsal. |
| **Deliverables** | Working Quote Simulator behind a `dsh` plugin · approval gate + XLSX export · risk report & approval cards · acceptance spot-checks passed (traceability, three-scenario comparison, export = page) · rehearsed six-minute demo. |
| **Assumptions** | Approval flow simulated in-UI only (no email/CRM). Export is XLSX only; PDF deferred. Out of scope: ERP connectors, multi-tenant auth, write-back, mobile, i18n. Demo runs on the committed sample dataset; one live-LLM rehearsal with mock fallback ready. |
| **Estimate** | **18 person-days** (10 dev + 8 PM: acceptance, pitch deck, rehearsal). |

**Usable decision:** a recommended quote band + payment terms behind an explicit approval gate.

---

## Proposed Solution Overview

BridgeFlow AI is a multi-agent engine on **DeepSeek Harness**: each of the four agents is one
thin `dsh` plugin that calls a Python endpoint; typed Pydantic contracts sit between every
stage. If the `dsh` preview breaks mid-hackathon, we fall back to the plain orchestrator and
lose nothing.

1. **Data Sanitizer** — rules first, LLM for the residue. Fixes typos, formats and duplicates;
   every correction logged; unfixable rows quarantined.
2. **Semantic Resolver (core)** — joins what never matched across departments, unifies
   day/week/month onto a monthly axis, and learns from human confirmations (versioned mapping
   rules), so month 2 needs a fraction of month 1's effort.
3. **Multi-Role Evaluator** — four concurrent role lenses over the same data; no finding
   without cited evidence; cross-role conflicts surface as tensions for humans, not auto-resolved.
4. **SOP & Flow Engine + Dynamic Quote Simulator** — monthly Master Table, risk report and
   approval cards; on demand, a simulated price band and payment terms with full sensitivity
   disclosure, gated behind explicit approval and never sent automatically.

**Engineering:** Python 3.12 / FastAPI / pandas; Next.js + TypeScript frontend (Upload &
Sanitize, Master Table & Risks, Quote Simulator). A pluggable LLM provider layer with a
deterministic mock default keeps the demo and CI offline and stable; Docker gives identical
local and AWS behaviour. Human-in-the-loop gates sit exactly where they must: critical fields
never auto-filled, low-confidence mappings never auto-published, quotes never auto-sent.
