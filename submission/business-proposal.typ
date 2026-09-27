// BridgeFlow AI — Business Proposal
// Show Me Your Agents Hackathon (NUS-ISS) — final submission

#import "style.typ": *

#show: doc.with(
  kind: "Business Proposal",
  subtitle: "Turning department spreadsheets into one traceable monthly business review",
  companion: [Technical Document (architecture, safety, evaluation)],
)

= Executive summary

BridgeFlow AI is a multi-agent business-review engine for small and medium-sized enterprises whose monthly decisions still live in department spreadsheets. Every department keeps its own file in its own vocabulary. BridgeFlow imports those files, combines them into one immutable, cell-traceable master table under a human-approved field dictionary, and runs a cross-department AI review in which a captain agent dispatches one subagent per department in parallel. Every metric is computed by deterministic Python from the formulas the dictionary declares, never by the model, and every write, from a mapping confirmation to a department handoff, requires an explicit human approval.

The reference scenario in this submission is a light-manufacturing SME with four departments: Production, Procurement, Finance and Marketing. The engine is not tied to that scenario. Fields, formulas, thresholds and each department's responsibilities are declared in the dictionary rather than written in code, so the same engine can serve other industries. User-defined department structures and connectors to the platforms SMEs already use (Feishu/Lark today; Google Workspace and others next) are on the roadmap.

The result is a monthly business brief in minutes instead of the week of manual reconciliation our target users describe. Risk shows up in the month it occurs instead of at the year-end audit, and every number can be traced back to the source cell that produced it.

#fact[
  *Cost and time of one full review (real model, measured 2026-09-25):* 53.4 seconds, 8 model requests, 75,267 tokens, a few US cents per monthly review. The whole loop is deployed and reproducible: 779 backend tests, 47 portal tests and 115 plugin tests pass offline, and every measured figure in this document has a reproduction command in the repository.
]

The product runs on AWS Lightsail and redeploys automatically on every merge to `main`. It has per-employee Feishu (Lark) sign-in and resolves roles from organization membership. A zero-login guest entry for evaluators is built: it is isolated from production data, and its model spend is capped by a gateway.

= Problem statement

*Who we build for.* SMEs of roughly 20–200 staff that run the business on spreadsheets spread across several departments. We start in Singapore, with light manufacturing and contract production as the first vertical. The same pattern appears wherever departments report separately and management decides monthly. Four characteristics shape the product:

- *No data team.* Nobody will write SQL, so the interface must accept the spreadsheets people already keep.
- *Excel is the system of record.* Some companies have an ERP, but decisions are still made in a monthly workbook that is emailed around.
- *Many departments, many vocabularies.* The same product is `SKU-A1`, `Alu bracket`, `4000-Sales/A1` or “Acme — bracket order”, depending on who you ask.
- *Thin margins, volatile inputs.* Materials, freight and FX move faster than a price list that is refreshed twice a year.

#block(width: 100%, breakable: false)[
  *The three pains, as measurable goals:*

  #table(
    columns: (1.2fr, 1.6fr, 1.6fr),
    table.header[Pain][Today][With BridgeFlow],
    [Data silos], [≈1 week per month of manual reconciliation], [Master table in minutes, under 10 min end to end],
    [Risk blindness], [Loss-making orders surface at year-end audit], [Flagged in the month they occur, with formula, threshold and source cells],
    [Static pricing], [Price list refreshed once or twice a year], [Quotation workspace pricing each enquiry against declared cost and capacity bases],
  )
]

*Why not buy ERP customization?* ERP customization has three familiar problems: long delivery cycles, implementations that drift from the requirement, and the trust cost of handing business data to an outside implementer. All three come from one root cause: the requirement has to be translated into code first. BridgeFlow replaces that translation with *declarations*. Fields, units, formulas, thresholds and responsibilities live in a versioned, human-readable dictionary that the business approves entry by entry. The code executes the declarations and refuses to guess. Changing a field definition is a dictionary edit that takes effect on the next import. Old batches stay frozen as evidence and are never recomputed.

= The product

== The monthly loop

+ *Import.* Each department uploads its file (CSV/XLSX) on the business's own template. The sanitizer repairs what rules can fix and logs every repair with its rule and confidence. Rows it cannot repair without guessing are quarantined, and no row is ever dropped silently.
+ *One aligned table.* Rows are joined on the columns the dictionary declares joinable. Declared formulas are computed and compared with what each department wrote. When they disagree, the system opens a question for a person instead of silently picking one value. The reference case produces a 76-column master table, and every cell traces back to file, sheet, row and column.
+ *Cross-department review.* The captain issues one-use dispatch tickets and calls the official subagent tool once per department in a single response, so the departments run concurrently. Each subagent can only submit structured output. The host re-checks every value, unit, status and citation against the dictionary before anything reaches the report.
+ *A brief people can sign.* The brief has a one-line conclusion and attention items written as logic chains (metric → formula → threshold → cited cells), with evidence grades G1–G4 and Word export. Its header states its own limits: it contains proposals only, and nothing has been executed.
+ *Human decisions.* Mapping confirmations, dispositions and every workflow action appear on native approval cards. A person can approve once (bound to a one-use receipt), reject with a reason, or let the request time out. Each of the three outcomes writes exactly what it should and nothing more.

== Configurable by declaration, not by industry

Light manufacturing is the demonstration scenario. The product itself is not built around it:

- *Business rules are data.* Each department's responsibility, metrics, thresholds and suggested actions come from the dictionary. A test checks that no business field name appears in the code. The acceptance suite already covers three industries. This release fixes the department set to the four reference roles; making the department set itself user-defined (name, scope, metrics, handoffs) is the next step.
- *The dictionary is drafted by the model and approved by people.* It can be transcribed from the company's existing dictionary spreadsheet, or drafted from column statistics alone. A person accepts, edits or rejects every entry before a version is published, so day one does not start from a blank file.
- *Connectors, not lock-in.* Sign-in and organization roles already come from Feishu/Lark, and import from Feishu sheets and wiki is being integrated. The same connector layer is designed to take Google Workspace (Sheets, Drive) and other third-party platforms next.

== Beyond the monthly close

- *Discovery → decision → execution.* Source materials are registered, and candidate work scenarios are scored on a quadrant chart under a declared policy. An MVP decision is recorded with each person's vote. Once approved, that decision becomes the scope of the filling-and-handoff workflow. The scope is re-checked on every read, and revising the decision marks it stale.
- *Filling & handoff workflow.* Departments fill standard records, and the captain asks for anything missing. Records then pass from one department to the next (demonstrated over two hops), with due times, overdue flags and a timeline of who did what and when.
- *Quotation workspace.* A declared template shows which fields a quotation needs and who owes each piece of evidence. A complete sample case is checked against a hand-computed answer. Pricing on real business samples starts with the pilot.
- *Overview.* One screen shows close progress, open items, workflow stages with overdue counts, key metrics and model token usage. Each block opens the page that owns it.

= Differentiation

#table(
  columns: (1.15fr, 1fr, 1fr),
  table.header[][Typical ERP customization][BridgeFlow],
  [Changing a rule], [Requirement → development → test → release], [Edit the dictionary; takes effect on the next import; old batches stay frozen],
  [Where numbers come from], [Report-layer logic, hard to trace], [Deterministic Python over declared formulas; every cell cites file/sheet/row/column],
  [Can the model invent numbers?], [n/a], [Department judgements are rebuilt from trusted facts; a wrong value, unit or citation fails validation and the report is marked `partial`],
  [Who can write], [System administrator], [Whoever the approval card names; one-use receipts; replays refused],
  [Business data exposure], [Implementer needs real data to debug], [Raw rows never enter model context (three layers); instructions planted in cells reached no model session (measured on the real model)],
  [New industry or department structure], [New implementation project], [New dictionary; same engine],
)

Three further design choices are deliberate, and each is demonstrated:

- *A fixed pipeline, not a free-planning agent.* Financial figures must be auditable and reproducible, and nobody can sign off on two runs that produce different numbers. The stages are fixed. The model does its work in the judgement inside each stage.
- *Evidence as a schema constraint.* The schema refuses any finding without cited evidence. Such findings are not shown with a caveat; they are rejected.
- *Explicit refusals.* Missing data, ambiguous dates, mismatched currencies and negative costs each produce a named refusal. Reporting a total over 640 of 760 rows would turn “at least this much” into “exactly this much”.

= Measured results (real-model evidence)

All figures below were measured on the deployed code path with a real model (`deepseek-v4.1-flash` unless noted). Each has a reproduction command in the repository, and the raw artefacts are kept with it.

#table(
  columns: (1.5fr, 2.2fr),
  table.header[Run][Result],
  [Cross-department review, risk case], [4/4 departments validated; 53.4 s, 8 requests, 75,267 tokens],
  [Same, balanced case], [4/4 validated; 18.8 s, 106,485 tokens],
  [Prompt-injection defence], [Instructions planted in a cell reached no model session; 4/4 validated],
  [Workflow, two hops end to end], [8 native approvals, 28 model requests, 76.9 s; a stage cannot complete before its own output is recorded],
  [Tool selection (captain picks the right first tool among ≈50)], [21/22; median 3 steps, ≈41 k tokens per case],
  [Acceptance suite (golden paths across three industries + adversarial/refusal cases)], [31/31 passing],
  [Automated tests (offline)], [Backend 779, portal 47, plugins 115; run on every pull request],
  [Scale probe, 200 k-row CSV], [Imports in 81–86 s with limits raised; tool outputs stay ≤ 37 KB, so raw rows stay out of model context at scale],
)

We report open limitations next to these results (see Risks and the Technical Document).

= Demonstration and deployment

- *Live instance:* #link(meta.live) (AWS Lightsail). Every merge to `main` runs the offline checks and deploys automatically through GitHub Actions. A 35-check preflight gates each deploy.
- *Sign-in:* per-employee Feishu OAuth through the portal at #link(meta.portal). Roles come from organization membership. A model-initiated write needs both role permission and a native approval.
- *Evaluator entry:* a zero-login guest demo with its own backend and console, a nightly reset, file uploads blocked and AI off by default. A model gateway keeps the real API key out of guest processes entirely and caps model choice, token counts, request size, rate and concurrency; it also has a kill switch. The entry has been verified end to end locally, and public enablement is the final deployment step.
- *Works without spending:* every sample, tour and check can run offline with a scripted model, free and repeatable.

*Five-minute demo.* Open the sample notebook (a fictional supplier's four department files) → read the master table and its one deliberate disagreement → trace one number to its source cell → start the review and watch the department subagents run in parallel → approve one request, reject another with a reason, and see that each outcome writes exactly what it should.

= Business model and go-to-market

*Deployment shape.* Web-only, with one instance per customer, so a company's spreadsheets, dictionary and model key never share a tenant with another company's. Seven concurrent per-user seats already run on a single small Lightsail instance (≈290 MB idle per seat, ≈1 s cold start). Per-seat isolation, quotas and a nightly reset are built in.

*Cost structure.* Import and master-table computation are deterministic and cost nothing. A full review uses on the order of $10^5$ tokens, a few cents at current DeepSeek pricing, and most of those tokens are cache hits on repeat runs. The operator chooses the model, and the product works with any OpenAI-compatible endpoint.

*Go-to-market.*

+ *Pilot on the templates the business already uses.* The dictionary is drafted from the company's own dictionary spreadsheet, then reviewed entry by entry and published as a version.
+ *Land the monthly close.* The routine has five stages, with an in-product task list, guided tours and a built-in user guide, and is designed for employees who have never used an agent product.
+ *Expand vertically and across platforms.* Light manufacturing comes first. We then move into adjacent industries with the same department-spreadsheet pattern (distribution, construction materials, services) and add connectors for the platforms customers already work in: Feishu/Lark, Google Workspace and others.

*Revenue sketch.* A managed per-instance subscription plus per-seat licensing, with model usage passed through at cost (metered per review on the product's overview page). The unit economics work because a review costs cents at the margin. What it replaces, a week of salaried reconciliation plus year-end surprises, costs far more.

= Roadmap (post-hackathon)

#table(
  columns: (1.4fr, 2.2fr),
  table.header[Next][What it unlocks],
  [User-defined departments], [A guided editor for department name, scope, metrics and handoffs, so any company structure can run without code changes],
  [Third-party connectors], [Feishu sheets/wiki import to finish, then Lark (international) sign-in, then Google Workspace (Sheets, Drive) and other platforms],
  [Pilot with real customer exports], [Business acceptance on real exports in place of labelled synthetic data],
  [Dictionary drafting on real data], [First-month onboarding without writing a dictionary by hand],
  [Guest seat pool], [One isolated seat per evaluator, with its own model budget and one-click reset],
  [Operations baseline], [Backup, retention, key rotation and spend caps in place before the first paying customer],
)

= Risks and mitigations

#table(
  columns: (1.5fr, 2.1fr),
  table.header[Risk][Mitigation],
  [All demo data is synthetic], [Stated on screen and in every document; a pilot with real exports is the first roadmap item; the refusal paths are shown in the demo],
  [No full multi-tenant boundary yet], [One instance per customer by design; per-employee chat isolation and formal report sign-off are listed as not built],
  [Dependence on one model provider], [Operator-configured model behind an OpenAI-compatible gateway; a deterministic scripted model keeps regression testing free and repeatable],
  [Public demo abuse], [Five-layer key defence: dedicated prepaid account, key held only by the gateway process, model/size/rate caps, application cooldowns, per-request accounting],
  [Very large files], [Measured and documented (81–86 s import for 200 k rows when limits are raised); raising the limits is an explicit operator decision with a memory budget],
)

= Team

Team *#meta.team*: two full-stack developers and two product managers. Over three weeks the team put in 52 person-days and merged 290+ reviewed pull requests, with tests required on every merge. The repository's status document is the single source for every measured figure and is updated after each run.

#v(1.2em)
#line(length: 100%, stroke: 0.4pt + rule-color)
#block(par(justify: false, text(size: 8.3pt, fill: muted)[
  Submission package: business proposal (this document), technical document, demo video, and the live deployment at #link(meta.live). All sample data is fictional. Every measured figure has a reproduction command and a raw evidence artefact in the repository.
]))
