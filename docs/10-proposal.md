# 10 — Proposal (3-week hackathon build)

> **已按 [`13-golden-standard.md`](13-golden-standard.md) 重排，落在里程碑与看板上。**
> 本文保留原始的范围与工作量估算；**实现顺序以里程碑为准**：
> [第一周](../../milestones/1) 架构归位与信任边界 · [第二周](../../milestones/2) 编排、记忆与人在环 ·
> [第三周](../../milestones/3) 可观测、eval 与演示。
>
> 与本文原始排期的差别：`docs/13` 第六节测出 rubric 第 2/3/5/7 项不达标的**根因是同一个**——
> dsh 被放在了错误的位置。所以第一周从「数据基础」改成「架构归位」，修根因一次修五项，
> 优先级高于按 PRD 补功能。自建前端与自建编排均已废弃。

> Renumbered from "07" — that slot holds the business PRD ([`07-prd-v0.1.md`](07-prd-v0.1.md)).
> Revised against measured results and the judging rubric; the review that drove the changes
> is [`11-proposal-review.md`](11-proposal-review.md).

Project: **BridgeFlow AI** — turn four messy monthly spreadsheets (production / procurement /
finance / marketing) into one aligned Master Table, with risk warnings and dynamic quotes.

- Team: 2 full-stack developers + 2 PMs · Timeline: 3 weeks · Total effort: **52 person-days**
  (28 dev of 30 available — **2 days held as buffer**; 24 PM of 30)
- Build framework: **DeepSeek Harness (`dsh`)** — the Python SDK drives the bundled `dsh`
  runtime as a subprocess over JSON-RPC on stdio, with one typed tool per data operation
  (see [`06-deepseek-harness.md`](06-deepseek-harness.md)); the plain orchestrator stays as
  fallback, and `LLM_PROVIDER=mock` keeps the whole pipeline runnable offline.
- Starting point: the scaffold runs the pipeline end-to-end and dsh is verified live (0.6s
  runtime boot in WSL, 0.6s for a tool-free turn). Integration is de-risked.
- **The throughput note in the original plan was wrong and has been corrected.** It blamed
  627s on 21 rows on whole tables being pasted into prompts, and scheduled tool-isation in
  week 2 as the cure. Measurement (#25) showed the prompts are ~590 characters: the time goes
  on dsh running a dozen `bash` steps over the repository per call, because an agent runtime
  was being used as a completion provider. Taking the resolver off it cut one adjudication
  from 12–212s and ~7,100 tokens of tool output to 3.6s and 707 tokens. The evaluator has not
  been moved yet, which is what week 1 is for.

---

## Scope and Proposed Approach

The scope is staged so that **each week produces a usable decision or increment**, and every
week ends demoable with an explicit sign-off. Sign-offs are the human checkpoints: nothing
advances to the next stage unattended.

> **以下三个 Week 小节是原始排期，范围与工作量估算仍然有效，但顺序已被重排。**
> 对照关系：
>
> | 原始 | 现在 | 为什么动 |
> | --- | --- | --- |
> | W1 数据基础 + Sanitizer + 信任边界 | **W1 保留信任边界，其余下沉** | 信任边界是 rubric 第 5 项，且已知有真实漏洞；数据契约冻结（#14）留在 W1，Sanitizer 的功能补齐（#1/#16）推到 W3 |
> | W2 Resolver + Evaluator + typed tools | **typed tools 与研判层上提到 W1**（#27 #13） | 它们是 rubric 第 2/3/5/7 项的共同根因。修根因一次修五项，优先级高于按 PRD 补功能 |
> | W2 映射确认与跨月记忆 | **W2 不变**（#29 #30 #39） | 依赖 OA 字段字典（#32），本来就是 W2 |
> | W3 报价 + eval + 演示 | **W3 不变**（#28 #31 #41 …） | 收尾不动 |
> | — | **W2 新增：workflow 取代 Orchestrator**（#38） | 原计划没有这条，但它是 rubric 第 2 项的正面回答 |
>
> 逐条 issue 见三个里程碑。

### Week 1 — "Mess in, clean out": data foundation, Data Sanitizer, input trust boundary

| | |
| --- | --- |
| **Scope** | Freeze and extend the v1 data contracts and the metric dictionary (the typed schemas already exist and pass tests — this is a freeze, not a build). Author four deliberately messy monthly sample files with known defects, plus a poisoned variant. Build the Data Sanitizer: rules-first, LLM only for the residue; every fix logged with rule + confidence; unfixable rows quarantined, never dropped. **Establish the input trust boundary**: spreadsheet cell content is data, never instruction — delimited and provenance-marked before it reaches any prompt, with output validated against the tainted input. Upload UI with live correction log. |
| **Deliverables** | Frozen schemas (CleanTable, CorrectionLog, EntityGraph, Finding, MasterTable) · messy demo dataset + one poisoned dataset · working Sanitizer as a `dsh` tool · injection defence with a passing attack case · Import Center UI · sign-off on the defect test-case set. |
| **Assumptions** | Sample files stand in for production data. The OA field dictionary is a **week-2 dependency, not a week-1 one** — see below. Mock LLM provider keeps runs deterministic and offline; one real provider key available for live runs. No auth / permissions in scope beyond least-privilege on the runtime itself. |
| **Estimate** | **19 person-days** (10 dev + 9 PM: dataset authoring incl. adversarial cases, contract freeze, demo narrative). |

**Usable decision:** four messy files in → typed clean tables + reviewable correction log out,
with a demonstrated refusal to obey instructions planted in the data.

### Week 2 — "One table, four lenses": Semantic Resolver + Multi-Role Evaluator + Master Table

| | |
| --- | --- |
| **Scope** | Build the core. **Semantic Resolver** joins SKU ↔ raw material ↔ GL account ↔ capacity from three sources in descending order of trust: declared in the OA field dictionary, co-occurrence within a row, then model adjudication of the residue — never from how identifiers are spelled. Low-confidence links go to a one-click human queue and persist as versioned mapping rules, so month 2 costs a fraction of month 1. Roll day/week/month source data onto a monthly axis (sum / average / period-end per metric). **Multi-Role Evaluator** runs four role analyses concurrently (capacity, margin/AR, price drift, customer tiering) — metrics computed by **typed tools**, not by the model reading raw rows; every finding must cite source rows. SOP Engine v1 assembles the monthly Master Table. |
| **Deliverables** | Resolver + Evaluator driven through `dsh` with a typed tool per data operation (read table, aggregate metric, look up field dictionary, compute capacity load) · mapping-confirmation screen · cross-month mapping memory · Master Table with drill-down to source rows · four role panels · the "Acme tension" demo beat, every number traceable. |
| **Assumptions** | **Dependency: the OA field dictionary.** Auto-accept rate is a function of its coverage, not a tunable threshold — `consumes` (SKU↔material) and `books_to` (SKU↔GL account) yield zero links at any threshold, because no single sheet contains both sides; they must be declared, not inferred (`data/mappings/README.md`). If the dictionary slips, week 2 ships with co-occurrence relations only and the declared ones are stubbed from sample BOM data. Metric formulas frozen from week 1 — no new metrics mid-week. Per-metric aggregation configurability is deferred; week 2 ships fixed roll-up rules. Findings are advisory: no write-back, no auto-actions. |
| **Estimate** | **16 person-days** (10 dev + 6 PM: mapping ground truth, metric sign-off). |

**Usable decision:** one aligned Master Table with trusted, evidence-backed findings.

### Week 3 — "Decide and quote": Dynamic Quote Simulator, evaluation, demo

| | |
| --- | --- |
| **Scope** | **Quote Simulator**: enquiry in → simulation over material cost × capacity × customer AR history → floor/target/stretch price band + payment-term options, with sensitivities shown; the floor is computed deterministically, not asserted by the model. Approval gate in-UI; unapproved plans cannot be exported; nothing is auto-sent. Risk report + approval cards. **Evaluation suite**: golden-path cases (the Acme order must be judged loss-making; the aluminium rise must surface) and adversarial cases (planted instructions, missing critical fields, contradictory departments, empty sheet), run in CI. Decision tracing: per-agent call, duration, tokens, retries. Acceptance pass, demo polish (streaming progress, offline mock fallback), full rehearsal. |
| **Deliverables** | Quote Simulator driven through `dsh` · approval gate · risk report & approval cards · **eval suite green in CI** · decision trace visible in the demo · acceptance spot-checks passed (traceability, three-scenario comparison) · rehearsed six-minute demo. |
| **Assumptions** | Approval flow simulated in-UI only (no email/CRM). **XLSX/PDF export is out of scope** — it scores nothing against the rubric and the days buy the eval suite instead. Also out of scope: ERP connectors, multi-tenant auth, write-back, mobile, i18n, currency/unit normalisation. Demo runs on the committed sample dataset; one live-LLM rehearsal with mock fallback ready. |
| **Estimate** | **17 person-days** (8 dev + 9 PM: eval case authoring, acceptance, pitch deck, rehearsal). |

**Usable decision:** a recommended quote band + payment terms behind an explicit approval gate,
with the evidence for every number and a suite proving it holds under attack.

---

## Proposed Solution Overview

BridgeFlow AI is a multi-agent engine on **DeepSeek Harness**. The Python SDK runs the bundled
`dsh` runtime as a subprocess over JSON-RPC; each data operation is a typed tool the agents
call, and typed Pydantic contracts sit between every stage. If the `dsh` preview breaks
mid-hackathon — every published release is a prerelease and the project states breaking changes
are expected — one environment variable falls back to the plain orchestrator and we lose nothing.

1. **Data Sanitizer** — rules first, LLM for the residue. Fixes typos, formats and duplicates;
   every correction logged with rule and confidence; unfixable rows quarantined, never dropped.
   Cell content is treated as untrusted data, never as instruction.
2. **Semantic Resolver (core)** — joins what never matched across departments from declarations
   and row co-occurrence rather than string similarity, unifies day/week/month onto a monthly
   axis, and learns from human confirmations (versioned mapping rules) so month 2 needs a
   fraction of month 1's effort.
3. **Multi-Role Evaluator** — four concurrent role lenses over the same data; metrics computed
   by tools and only interpreted by the model; no finding without cited evidence; cross-role
   conflicts surface as tensions for humans, not auto-resolved.
4. **SOP & Flow Engine + Dynamic Quote Simulator** — monthly Master Table, risk report and
   approval cards; on demand, a simulated price band and payment terms with full sensitivity
   disclosure, gated behind explicit approval and never sent automatically.

**Why a fixed pipeline rather than a planning agent.** This is a deliberate tradeoff, not a
missing capability. Financial figures have to be auditable, reproducible and attributable: an
approver cannot sign off on a number that two runs would derive differently. The stages are
fixed; the judgement inside each stage is where the model earns its place.

**Engineering:** Python 3.12 / FastAPI / pandas behind typed dsh tools; the operator UI is
dsh web customised through Client plugins rather than a self-built app. A pluggable LLM provider layer with a
deterministic mock default keeps rehearsal reproducible — though mock output is placeholder
text, so it is a fallback, not what gets demoed. Deployment is deliberately unconfigured: no
Dockerfiles, no CI, until the target is settled. Human-in-the-loop gates sit exactly where the risk is: critical
fields never auto-filled, low-confidence mappings never auto-published, quotes never auto-sent
— and, because those gates protect against model error rather than hostile input, the input
trust boundary in week 1 covers what they cannot.
