# 04 — Q&A sheet

**Goal:** a short, honest, rehearsed answer for every question the judges are likely to ask, with a
named owner per topic, so the six minutes of Q&A in each slot score points instead of losing them.

**Owner:** Q&A lead. Topic owners are listed below.
**Due:** draft Thursday 8 October; final after the Friday rehearsal, then printed (one A4 sheet,
double-sided) for each member.

## How we answer

- **Shape:** one-sentence answer → one piece of proof (a number from the whitelist or something we
  can click) → stop. 30–45 seconds. Let the judge ask a follow-up.
- **Routing:** the Q&A lead takes every question and either answers or says "[name] built that" and
  hands over. Only one person answers each question.
- **Show, do not tell,** when a demo beat exists for it (the "extra beats" table in
  [doc 3](03-demo-script.md#extra-beats-for-qa-can-you-show-me)). Keep it under 45 seconds.
- **Numbers:** only figures from the [doc 1 whitelist](01-pitch-narrative.md#numbers-we-may-quote).
- **When we do not know:** "We have not measured that. Here is what we do know: …" Never invent a
  figure, a customer or a compliance status.
- **Limitations are a strength when volunteered:** say what is not built before the judge finds it.

## Topic owners

| Topic | Owner |
| --- | --- |
| A. How the agent decides | Developer (agent and tool design) |
| B. What it costs to run | PM (business) with developer (infrastructure) |
| C. What happens when it is wrong | Developer (guardrails) |
| D. Why agentic rather than a plain workflow | Lead presenter |
| E. What is next | PM (business) |
| F. Business and market | PM (business) |
| G. Data, privacy and security | Developer (guardrails) |
| H. Technology and platform | Developer (platform) |
| I. Evaluation and evidence | Developer (agent and tool design) |
| J. Hard questions | Q&A lead |

## A. How the agent decides

**Q: How does the agent decide what to do?**
There are two layers. The captain, the agent in the chat, reads the notebook's business state and
picks from about 50 typed tools, such as importing, looking up a metric, tracing a cell, or
dispatching the review. In our tool-selection test it chose the right first tool in 21 of 22 cases.
For a review, it issues one-use dispatch tickets and calls the official subagent tool once per
department in a single response, so the four department agents run in parallel.

**Q: How does a department agent decide what to flag?**
Each department agent sees only its own department's computed metrics, its declared
responsibilities, thresholds and suggested actions from the field dictionary, and source
references. It decides which metrics matter, how to explain them, and what to recommend. It cannot
change a number: the host rebuilds each judgement from trusted computed facts, and any value, unit or
citation that does not match fails validation.

**Q: Who decides the thresholds and formulas?**
The business does, in a field dictionary approved entry by entry. The code executes those
declarations and refuses to guess. Where the dictionary is silent, the system either asks a question
or uses a labelled convention (shown as G3 until someone confirms it, which is what we did with VAT in
the demo).

**Q: Can it act on its own?**
It can read, compute, look things up and propose. Anything that writes business data (confirming a
column match, recording a convention, submitting a handoff) goes through a native approval card.
A person allows it once, or rejects it with a reason that the agent receives. The approval receipt is
bound to that exact request and cannot be replayed.

## B. What it costs to run

**Q: What does one review cost?**
On 25 September, one four-department review on the risk case took 53.4 seconds, 8 model requests and
75,267 tokens: a few US cents at the provider's list price. *(Replace with the recomputed figure from
the whitelist.)* Repeat runs reuse cached context, which lowers it further.

**Q: What about the rest of the pipeline?**
Import, cleaning, the master table, metric calculation and the monthly brief are deterministic Python
and use no model calls. The brief is assembled from the saved review without another model call. The
model is only paid for the review, the captain's suggestions and the approvals it drafts.

**Q: Infrastructure?**
Seven concurrent per-user seats run on one small AWS Lightsail instance (4 GB RAM class), about
290 MB idle per seat with about one-second cold start. One instance per customer.

**Q: What would you charge?**
A managed per-instance subscription plus per-seat licences, with model usage passed through at cost
and metered per review on the overview page. We have not priced it against customers yet; a pilot
will set the number. The comparison point is a week of a salaried person's time each month plus the
cost of risks found late.

**Q: How do you stop the cost running away?**
Model calls go through a gate that caps model choice, request size, tokens, rate and concurrency, and
has a kill switch. In guest mode the provider key exists only in the gate process.

## C. What happens when it is wrong

**Q: What if the AI makes up a number?**
It cannot put one in the table: every table metric is computed by Python from declared formulas. In
the review, a finding must cite evidence or the schema rejects it, and the host re-checks each value,
unit and citation against the computed facts. A department that fails validation or returns nothing
is named, and the report is marked incomplete rather than filling the gap.

**Q: What if its judgement is wrong, even with correct numbers?**
That can happen, so the product labels it. Every finding carries an evidence grade: G1 read from a
file, G2 computed by a formula, G3 resting on an unconfirmed convention, G4 model advice. The brief's
header states that it contains proposals only and nothing has been executed. A person decides, and
every write needs an approval.

**Q: What if a person approves something wrong?**
Batches are immutable. Fixing a file creates a new batch and leaves the old one as evidence.
Dictionary changes apply from the next import; old batches keep their frozen snapshot. Every decision
is in the Records journal with who, what and when.

**Q: What if the data itself is wrong or malicious?**
Rows that rules cannot fix are quarantined and counted, never silently dropped or guessed. Missing
data, ambiguous dates, mismatched currencies and negative costs each produce a named refusal. Text in
cells is treated as data: in a real-model test, instructions planted in a cell reached no model
session. *(Show the "messy data" extra beat if asked.)*

## D. Why agentic rather than a plain workflow

**Q: Isn't this just a workflow with an LLM on top?**
The numbers are a workflow on purpose. Financial figures must be auditable and reproducible, and
nobody can sign a number that two runs derive differently, so the stages are fixed. The agents work
where the inputs are ambiguous and a fixed rule would fail:

- interpreting each department's metrics and explaining what matters to that department;
- proposing column matches when a department renames a column, against fields already declared;
- drafting a field dictionary from column statistics for a new customer;
- turning a plain-language request into the right sequence of about 50 tools, for users who have no
  data team;
- asking for missing information during a handoff and filling records once a person answers.

Agentic where judgement is needed, deterministic where an auditor needs to reproduce the result.

**Q: Why four department agents instead of one?**
Separation of concerns and least privilege. Each agent reads only its own department's metrics and
responsibilities, the way the real departments work. They run in parallel, and a failure in one is
reported as that department's gap without corrupting the others.

**Q: Why not let the model plan freely?**
We considered it. A model-written plan changes between runs, which breaks reproducibility. The
framework's own free-form workflow package describes itself as containment, not a security boundary.
We kept the plan fixed and gave the model freedom inside each stage.

## E. What is next

**Q: What would you build next?**
In order:

1. A pilot on a real company's exports, replacing synthetic data with business acceptance.
2. User-defined departments: a guided editor for department name, scope, metrics and handoffs, so any
   company structure runs without code changes.
3. Connectors: finish Feishu sheet and wiki import, then Lark sign-in, then Google Workspace.
4. Dictionary drafting tested on real data, so the first month needs no hand-written dictionary.
5. One isolated guest seat per evaluator with its own model budget.
6. Operations baseline before a first paying customer: backup, retention, key rotation, spend caps.

**Q: What do you need?**
SMEs willing to pilot with a month of real spreadsheets, and introductions to them.

## F. Business and market

**Q: Who is the customer?**
SMEs of roughly 20–200 staff that run monthly decisions on department spreadsheets, starting with
light manufacturing and contract production in Singapore. The person who feels the pain is whoever
reconciles the month: often a finance or operations manager.

**Q: Have you validated this with real users?**
The templates in the demo are modelled on a real business's v2 department templates (translated and
filled with synthetic data), and the reconciliation pain is what target users described. We have not
run a paid pilot; that is the first roadmap item. *(Do not overstate the number or nature of
conversations.)*

**Q: Why not Excel Copilot, Power BI or an ERP?**
- Excel Copilot and similar assistants work inside one workbook; the problem is four workbooks with
  four vocabularies, and the need for numbers that trace to a source and can be signed.
- BI tools need clean, modelled data and someone to build the model; our users have no data team.
- ERP customisation means a long project, requirements that drift in translation, and handing data to
  an outside implementer. We replace code changes with declarations the business approves.

**Q: How do you onboard a new customer?**
Use the business's own templates. The model drafts a field dictionary from the company's existing
dictionary spreadsheet or from column statistics, a person decides every entry, and a version is
published. Then the five-step monthly routine with in-product tasks, guided tours and a user guide.

**Q: Does it only work for manufacturing?**
Fields, formulas, thresholds and department responsibilities live in the dictionary, and a test
checks that no business field name is written in code. The acceptance suite covers three industries.
The department set is fixed at four in this release; making it user-defined is next.

## G. Data, privacy and security

**Q: Does our data go to the model provider?**
Only bounded summaries, computed metrics and source references, never whole raw tables. Tools return
capped samples with true counts. The model provider is the operator's choice through an
OpenAI-compatible endpoint, so a customer can pick a provider and region they trust.

**Q: DeepSeek is a Chinese provider. Is that a problem?**
The harness is DeepSeek's open agent framework; the model behind it is configurable. Our
measurements used a DeepSeek model, but the deployment can point at another OpenAI-compatible
endpoint. We have not yet measured other providers on the same evaluation set. *(Do not claim
otherwise.)*

**Q: Is it PDPA compliant?**
We have not done a formal PDPA assessment or a third-party security review, and we say so in our
limitations. Design choices that help: one instance per customer, raw rows kept out of model context,
per-employee sign-in with role grants, and secrets kept out of guest processes.

**Q: Who can see and change what?**
Staff sign in per person through Feishu; roles come from organisation membership. A model-initiated
write needs both a role permission checked by the host and a native approval. Full multi-tenant
isolation inside one instance is not built, which is why we deploy one instance per customer.

**Q: What about prompt injection?**
Three layers: cell content is data and never enters prompts as instructions; tool calls carrying
instruction-shaped text are refused by a host guard; there is no shell tool, and outputs are capped.
Shown live in the demo.

## H. Technology and platform

**Q: What is the stack?**
The official DeepSeek Harness provides the web UI, sessions, tool dispatch, native approvals and
subagents. Our TypeScript plugins add typed domain tools, guards and the workspace. A Python backend
does imports, calculations, validation and provenance. Optional portal for Feishu sign-in. We extend
the official runtime rather than fork it.

**Q: Where does AWS come in?**
The product runs on AWS Lightsail and redeploys automatically through GitHub Actions on every merge to
`main`, gated by a preflight check. Per-employee seats and the isolated guest instance run on the same
host.

**Q: Could it run on Bedrock?**
The model gate speaks OpenAI-compatible endpoints. We have not tested a Bedrock-hosted model; it is a
reasonable next experiment, and we would run our evaluation set before switching.

**Q: How does it scale?**
In a probe, a 200,000-row CSV imported in 81–86 seconds with limits raised, and tool outputs stayed
under 37 KB, so raw rows still stayed out of model context. Default limits are lower; we do not claim
production readiness at that size.

**Q: Why did you choose this harness?**
It gave us the native pieces an agent product needs (sessions, approvals, subagents, a web UI)
without building them, so our effort went into the domain tools and guardrails.

## I. Evaluation and evidence

**Q: How do you know it works?**
- An acceptance suite of golden paths across three industries plus adversarial and refusal cases:
  31/31 at submission.
- Real-model runs: the review (4/4 departments validated), prompt injection, a two-hop handoff
  workflow with 8 approvals, and tool selection (21/22).
- Offline automated tests on every pull request. *(Quote the re-run counts from the whitelist or
  omit.)*
- A scripted model so samples, tours and regression tests run free and repeatably.

**Q: How do you measure the quality of the AI's judgement?**
Each sample case has an independent, human-checked answer key that is never given to the model; the
acceptance suite compares outcomes against it. We have not measured judgement quality on real customer data; that is
what the pilot is for.

## J. Hard questions

**Q: Your data is synthetic. Why should we believe this works on real data?**
Fair. The templates come from a real business, the planted problems are the ones such businesses
report, and the refusal paths show what happens when data is bad. Real exports are our first
roadmap item, and the limitations page says so.

**Q: What does not work yet?**
Real enterprise acceptance, full multi-tenant isolation within one instance, large-sheet Feishu
import, production-scale batches, external quotation issuance, formal report sign-off and a
third-party security review.

**Q: What was the hardest part?**
Making the agents useful without letting them touch the numbers. Our first version just asked the
model for JSON; we measured it against the judging criteria, rebuilt it on typed tools and native
subagents, and added host validation so a wrong number cannot reach the report.

**Q: What would you do differently?**
Start with the evaluation set and the guardrails on day one, and get real spreadsheets from a pilot
company earlier.

**Q: How did a team of four build this in three weeks?**
52 person-days and 290+ reviewed pull requests, with tests required on every merge. *(Update the
count if quoting.)*

## Practice plan

| When | Drill |
| --- | --- |
| Thu 8 Oct, evening | Each topic owner answers their section aloud; others time and challenge. Rewrite any answer over 45 s |
| Fri 9 Oct, dress rehearsal | Two "judges" (ideally people outside the team) ask 6 minutes of random questions from this sheet plus their own. Log every question that was not on the sheet |
| Sat 10 Oct, between rounds | Debrief the round 1 questions in 5 minutes; adjust answers before round 2 |

## Questions log

Add every real question from rehearsals and from round 1 here, with what we answered and how to
improve it.

| Question | Asked by | Our answer | Better answer |
| --- | --- | --- | --- |
| | | | |
