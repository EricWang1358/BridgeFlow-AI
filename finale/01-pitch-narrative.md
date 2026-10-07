# 01 — Pitch narrative

**Goal:** one story, in three beats, that every member can tell the same way: the business problem,
how the agentic solution works, and the value it delivers. The poster, the demo and the Q&A answers
are built against this document, so it is locked first.

**Owner:** lead presenter, with sign-off from all four members.
**Due:** Wednesday 7 October, end of day. After sign-off, changes need the whole team's agreement
because they ripple into the poster and the rehearsal.

## Definition of done

- [ ] One-sentence logline everyone can say from memory.
- [ ] Three beats, each with one message, a spoken draft, and the proof shown for it.
- [ ] Time budget that leaves at least 5 minutes for Q&A inside the 15-minute slot.
- [ ] Number whitelist: every figure we will say or print, with its date and source, re-checked.
- [ ] The two points we raise unprompted, worded.
- [ ] A 60-second booth version for walk-up visitors and photo moments.
- [ ] Read aloud once, timed, by the lead presenter; the team signs off.

## Constraints that shape the story

- **15 minutes including Q&A, twice.** Judges in round 2 may or may not have seen round 1. Treat
  each slot as a first meeting.
- **The organisers' brief:** explain the business problem, how the agentic AI solution works, and the
  value or impact. Those are our three beats, in that order, in their words.
- **Judging criteria** (seven, as recorded during the build): Goal & Scope; Architecture & Reasoning
  Loop; Tool Use & Integration; Autonomy & Human-in-the-Loop; Safety, Security & Guardrails;
  Observability & Evaluation; Platform & Tooling Usage. Every criterion should be visibly touched by
  either the narrative or the demo (mapping below).
- **"Powered by AWS".** The product runs on AWS Lightsail and deploys from GitHub Actions on every
  merge. Say so once, plainly.
- **The data is synthetic.** Say so once, early, and do not apologise for it again.

## Time budget (15:00)

| Segment | Time | Cumulative |
| --- | --- | --- |
| Beat 1: the problem | 1:15 | 1:15 |
| Beat 2: how it works (one sentence of architecture, then the live demo) | 0:30 + 5:00 | 6:45 |
| Beat 3: value and impact, and what is next | 1:15 | 8:00 |
| Q&A | 6:00 | 14:00 |
| Buffer (late start, handover, a slow model call) | 1:00 | 15:00 |

If the slot starts late or the judges interrupt early, cut from the demo first (the cut order is in
[doc 3](03-demo-script.md#cutting-under-pressure)), never from Q&A below 4 minutes.

## Logline

> **Every month, each department hands in its own spreadsheet, and they never quite agree.
> BridgeFlow combines them into one traceable table and sends one AI agent per department to review
> it, but every number is computed by code and every write waits for a person.**

Short form for the poster and the booth: *Every department's spreadsheet in. One trusted monthly
review out.*

## Positioning

- **Multi-department, not "four".** The sample happens to have four departments (production,
  procurement, finance, marketing), and this release ships with those four built in. Say "every
  department", "one agent per department" and "department agents"; do not lead with "four
  departments" or "four agents", which suggests the product fits only one organisation. If asked,
  answer honestly: four are built in today, and user-defined department structures are next.
- **The monthly review is the flagship; the engine is broader.** The demo stays on the monthly
  review. In beat 3, point to the poster's three tiles: the same traceable data, typed tools and
  approvals already run quotes (no price without evidence), scoring improvement ideas, and handoffs
  between departments. Show them only when a judge asks.
- The spoken lines and timings for both rounds are in [doc 7](07-presentation-script.typ), which
  follows this document.

## Beat 1 — The business problem (1:15)

**Message:** SMEs make monthly decisions from department spreadsheets that do not line up, and
nobody has the time or a data team to reconcile them. The cost is a lost week every month and risk
that surfaces too late.

**Spoken draft:**

> Think of a 60-person concrete supplier here in Singapore. Every month Production, Procurement,
> Finance and Marketing each send a spreadsheet. Same customers, spelled differently. Same projects,
> different column names, different units. Someone in finance spends about a week each month
> stitching them together by hand, and that is what the businesses we spoke to describe.
>
> Each sheet looks fine on its own. The problems only show up when you put them together: an order
> that loses money, a customer two departments call by different names, a figure one department typed
> and another computed. Today that is often found at year-end, by an auditor.
>
> These companies have no data team. Excel is their system of record. And customising an ERP means a
> long project, a requirement that drifts in translation, and handing business data to an outside
> implementer.

**Proof on screen:** the department files in **Sources**, then the cross-department master
with its one disagreement (demo beats 0–1).

**Things to get right:**

- "About a week a month" is what target users describe, not a measurement. Phrase it that way.
- The concrete supplier is fictional. Its templates are modelled on a real business's v2 templates,
  translated to English. Say "fictional supplier" once.
- Do not quote national SME statistics unless someone sources them from a primary publisher
  (SingStat or Enterprise Singapore) by Thursday and adds them to the whitelist.

## Beat 2 — How the agentic solution works (0:30 + demo)

**Message:** a captain agent runs a fixed, auditable pipeline and dispatches one agent per department
in parallel. Code does the arithmetic. Agents do the judgement. People make the decisions.

**One-sentence architecture (said before the demo, with the poster diagram behind us):**

> Python imports and cleans the files under a field dictionary the business approves, and computes
> every metric from declared formulas. A captain agent then sends one AI agent per department to
> review the month, all at the same time. They see computed
> metrics and source references, never raw rows. The host checks every finding against the evidence
> before it reaches the report. Anything that writes business data goes through an approval card.

**Then the demo** ([doc 3](03-demo-script.md)). The demo carries most of this beat; the narration
in doc 3 is written to land these points:

| Point | Where it is shown | Rubric criterion |
| --- | --- | --- |
| One official subagent per department, dispatched in one response, running concurrently | Trajectory during the review | Architecture & Reasoning Loop; Platform & Tooling |
| Typed domain tools (about 50), chosen by the captain | Trajectory steps; "where is X" navigation | Tool Use & Integration |
| Every figure traces to file, sheet, row and column | Click a master-table cell | Observability; Goal & Scope |
| Findings carry formula, threshold, cited cells and evidence grade G1–G4 | Conclusions | Architecture; Observability |
| Writes need a person; a rejection reason returns to the model | Approval card: reject, then allow once | Autonomy & Human-in-the-Loop |
| Instructions hidden in data are refused by a host guard | Injection beat | Safety & Guardrails |
| Each run records tools, timings, tokens and refused calls | Records | Observability & Evaluation |

## Beat 3 — Value and impact (1:15)

**Message:** from a week of reconciliation to a reviewed month in minutes, for a few cents of model
cost, with numbers people can sign because each one traces to a cell. It adapts by declaration, not
by a software project.

**Spoken draft:**

> What changes for that finance manager? The month's files become one table in the time it takes to
> upload them, and the cleaning costs nothing because it is rules, not AI. The review you just watched
> took under a minute and cost a few US cents in model calls. A loss-making order shows up in the
> month it happens, with the formula, the threshold and the cells behind it.
>
> Because every number traces to a source cell, a manager can sign it. Because writes wait for a
> person, nothing changes behind their back. And because fields, formulas and thresholds live in a
> dictionary the business approves, a new rule is an edit that takes effect at the next import. Old
> months stay frozen as evidence.
>
> The monthly review is our flagship, but it runs on one engine. The same traceable data, typed tools
> and approvals already power quotes, where there is no price without evidence; scoring improvement
> ideas; and handoffs between departments.
>
> It is deployed on AWS today, with per-employee sign-in and an isolated guest entry. Next we want a
> pilot on a real company's exports, user-defined department structures, and connectors for Google
> Workspace next to the Feishu one we have. If you know an SME that closes its month in spreadsheets,
> we would like to meet them.

**Proof:** the figures in the whitelist below, the Records page from the demo, and the poster's three
workflow tiles. (The booth poster is deliberately minimal; the measured results are on the detailed
version, `finale/poster/bridgeflow-a1-poster-detailed.pdf`.)

**Things to get right:**

- "Under a minute" refers to the review step on the sample (53.4 s measured). It is not end-to-end
  onboarding.
- "A few US cents" must be recomputed from the measured token count and the provider's list price on
  the day we print. Write the arithmetic into the whitelist.
- End on the ask (a pilot), not on a feature list.

## Two points to raise unprompted

Judges will not infer these by watching. Fit each into beat 2 or the first Q&A answer.

1. **The fixed pipeline is a choice, not a missing capability.** Financial figures must be
   auditable, replayable and attributable. An approver cannot sign a number that two runs derive
   differently. So the stages are fixed, and the model's freedom sits inside each stage: interpreting
   a department's metrics, proposing column matches, drafting dictionary entries, choosing tools,
   asking for missing information.
2. **A conclusion without evidence is rejected, not downgraded.** The finding schema refuses a claim
   with no cited evidence, and the host re-checks each value, unit and citation against the computed
   facts.

## Numbers we may quote

Only these figures may be said aloud or printed. Each must be re-checked on Thursday 8 October
before the poster goes to print. If a re-run gives a different value, update this table and use the
new value with its new date.

| Figure | Value | Measured | Source | Re-check |
| --- | --- | --- | --- | --- |
| Department review, risk case | Every department validated (4 of 4 in the sample); 53.4 s; 8 model requests; 75,267 tokens | 2026-09-25, `deepseek-v4.1-flash` | Submitted business proposal | Re-run one review on the demo instance; record time and tokens from Records |
| Review, balanced case | 4/4 validated; 18.8 s; 106,485 tokens | 2026-09-25 | Business proposal | Optional |
| Cost per review | "A few US cents" | Derived | Tokens × provider list price | Do the arithmetic with the current price, including the cache-hit rate if quoted |
| Prompt-injection defence | An instruction planted in a cell reached no model session; 4/4 validated | Real-model run | Business proposal | Show live in the demo instead of quoting |
| Two-hop handoff workflow | 8 native approvals; 28 model requests; 76.9 s | Real-model run | Business proposal | Optional |
| Tool selection | Captain picks the right first tool in 21/22 cases among about 50 tools | Real-model run | Business proposal | — |
| Acceptance suite | 31/31 (golden paths across three industries, plus adversarial and refusal cases) | At submission | Business proposal | Re-run if quoting |
| Automated tests | Backend 779, portal 47, plugins 115 | At submission | Business proposal | Re-run and quote today's counts, or drop the figure |
| Scale probe | 200,000-row CSV imported in 81–86 s with limits raised; tool outputs ≤ 37 KB | At submission | Business proposal | Quote only with "limits raised"; see limitations |
| Hosting | 7 concurrent seats on one small Lightsail instance; about 290 MB idle per seat; about 1 s cold start | At submission | Business proposal | — |
| Team effort | 4 people, 3 weeks, 52 person-days, 290+ reviewed pull requests | At submission | Business proposal | Update the PR count if quoting |
| Master table | 76 columns, every cell traceable to file, sheet, row and column | Reference case | Business proposal | — |

**Not on the list, so not said:** any accuracy percentage for the AI's judgement, any customer
count, any revenue projection, "production-ready", "no hallucinations", "replaces your accountant".

## Words

| Use | Avoid |
| --- | --- |
| "Department agents", "captain" | "Autonomous AI that runs your finance" |
| "Every department", "one agent per department" | "Four departments", "four agents" in headlines and taglines |
| "Computed by code from declared formulas" | "The AI calculates" |
| "Proposes; a person approves" | "Fully automated" |
| "Traceable to the source cell" | "100% accurate" |
| "Synthetic sample data modelled on a real business's templates" | "Real customer data" |
| "Measured on 25 September with a real model" | Unsourced round numbers |

## Booth version (60 seconds)

For walk-up visitors, other judges and photo moments:

> Every department keeps its own spreadsheet, and someone loses about a week a month reconciling
> them. BridgeFlow turns them into one table where every number traces to its source cell, then sends
> one AI agent per department to review the month in parallel. Code does the maths, agents do the judgement, and
> nothing is written without a person approving it. Want to see a number traced back to its cell?

## Lock checklist

- [ ] Logline agreed.
- [ ] Each beat read aloud and timed (target ±10 s).
- [ ] Whitelist re-checked, with dates updated (Thursday).
- [ ] Poster designer has the logline, the three beat messages and the whitelist (doc 2).
- [ ] Demo narration in doc 3 matches the beat 2 points.
- [ ] Q&A answers in doc 4 use the same numbers and words.
