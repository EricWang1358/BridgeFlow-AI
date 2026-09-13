# 04 — Demo plan

Six minutes, one question: "what does this month's reconciliation say, and where do the departments disagree?"

> Written in English because it is spoken on stage. Every measured figure comes from
> [`00-status.md`](00-status.md); nothing here restates a number that is not measured there.
> The concrete clicking sequence, prerequisites and the answer key are in
> [`17`](17-business-mvp-acceptance.md) and the [one-stop demo](../demo-walkthrough/README.md).

## What runs today

The stage path is the native DSH Web demo with the generated 2025-11 business case: four department
CSV files, a frozen field dictionary, four department sub-sessions, and a report that cites cells.
The older "Acme November order" narrative runs on the legacy Python pipeline, which is off by
default (`BRIDGEFLOW_ENABLE_LEGACY_PIPELINE`), so treat it as a terminal walkthrough rather than a
screen you will click through.

| # | Beat | Rubric | Runs today | If it does not |
| - | ---- | ------ | ---------- | -------------- |
| 1 | Show the four monthly files. Different date formats, different spellings for one product, a shifted header, a merged cell. "This is a normal Tuesday." | 1 | yes, no code needed | — |
| 2 | Import all four. Corrections and quarantined rows come back per batch; a renamed column is proposed as a match to a declared field and a person approves it in the native approval panel, then the file is re-imported. Quarantined rows are released or discarded the same way. The batch stays immutable, so re-running does not overwrite last month. | 1, 4, 6 | yes, native panel and column-match view | name the frozen dictionary on screen if the batch returns `needs_configuration` |
| 3 | Start the review from the panel. The captain dispatches four department sub-sessions in parallel; they only read and judge. Anything that writes — a column match, a quarantine release — is asked of a person by the captain, never approved by a department sub-session. | 4 | yes. The refusal half is the interesting half: nothing is written, and the reviewer's reason comes back into the model's own narration | if the approval panel is not visible, show the native audit events instead |
| 4 | One aligned master table from four files, with the labels that never reached the entity graph listed rather than hidden. | 2 | yes, as an artifact in the right-hand panel | — |
| 5 | Four department views: load against declared available hours, spend against budget at the same quantity, project margin, weighted payment terms, the order-vs-output gap. Tension between departments is the punchline. | 3, 6 | mostly. Every figure shown is computed by rule from declared columns and cites its cells | do not claim a customer tier, a price band, a credit decision or an executed action; none of them exist |
| 6 | Optional, only if time allows. Open the quotation workspace: what a quote sheet would contain, which inputs are missing, and who owes each one. Numbers are computed from declared arithmetic on a synthetic case. | 4 | only as a declaration preview | do not present it as an issued quote; contract parsing and sending do not exist yet |
| 7 | Close on the HMW slide. | 1 | yes | — |
| 8 | Show an attack being stopped: a poisoned cell tries to instruct the agent, the host guard refuses at dispatch, and the attempt is in the audit trail. | 5, 6 | yes: `plugins/src/guards/untrusted-input.ts` is wired in `plugins/src/index.ts`, and the deny/allow cases are shared with the Python side | say the guard is deliberately narrow (it errs toward letting a real purchase order through), and that breadth comes from the adversarial eval suite |

The issue numbers behind the caveats above, in case a judge asks where a claim is tracked:
[#7](https://github.com/EricWang1358/BridgeFlow-AI/issues/7) price bands must come from real cost
arithmetic, [#13](https://github.com/EricWang1358/BridgeFlow-AI/issues/13) the evaluator consumes
metrics instead of raw rows, [#25](https://github.com/EricWang1358/BridgeFlow-AI/issues/25) the
corrected attribution of the slow runs,
[#44](https://github.com/EricWang1358/BridgeFlow-AI/issues/44) the join key is no longer guessed
(PR #60), [#46](https://github.com/EricWang1358/BridgeFlow-AI/issues/46) and
[#88](https://github.com/EricWang1358/BridgeFlow-AI/issues/88) the field-mapping wizard and quarantine
disposal (now built as the column-match approval and quarantine release/discard tools, #146/#156).

Beat 8 is the beat most teams will not have. A working pipeline is table stakes; an attack being
refused, in a product whose input is four spreadsheets maintained by four different people, is a
specific and plausible threat you can demonstrate in 30 seconds.

### How to rehearse beat 3

Have the second screen ready before the turn starts. The point lands only if the audience watches
the agent stop and wait. Say it out loud while it is waiting: "nothing has been written yet, and if
I walk away now, nothing will be." Then refuse first and re-run to approve. A refusal that carries
the reviewer's reason back into the model's narration is the part nobody else shows.

## Two things to say unprompted

Judges will not infer either of these from watching ([`09`](09-rubric-assessment.md) argues the case):

1. The fixed pipeline is a choice, not a missing capability. Financial figures have to be auditable,
   replayable and attributable; an approver cannot sign a number that two runs derive differently.
   The framework's own `workflow` package lets the model write the orchestration script and
   describes itself as "containment, not a security boundary" ([`13` §7.4](13-golden-standard.md)).
   Declining it is the point.
2. Every conclusion is bound to evidence. `Finding` rejects an evidence-free claim at the schema
   layer: refused, not downgraded.

## Demo safety rules

- Rehearse on the real provider, not on mock. Mock returns placeholder text such as
  `mock-justification-<hash>`: it proves the code does not crash. If the network fails on stage and
  you fall back to mock, say so out loud.
- Import and rule computation cost nothing. Sending the analysis request in the native conversation
  calls the configured model, so budget for real charges and minutes rather than seconds; the
  measured durations and token counts are in [`00`](00-status.md).
- Use the case dictionary (`data/business_demo/dictionary.yaml`), or start with `--demo`. With the
  default dictionary the import succeeds and the review refuses, and the failure looks like a bug.
- Every number shown must trace to a cell. A judge will ask where a percentage came from; expand
  "explanation and raw source" and show the file, row and column.
- Do not present the sample as a customer's books. It is generated, labelled synthetic, and comes
  with an independent answer key that must never be fed to the model.
- Three browser smokes are currently red on the development machine for reasons unrelated to the
  product ([#97](https://github.com/EricWang1358/BridgeFlow-AI/issues/97)). Rehearse on a real
  `DSH_HOME`, and do not use a red smoke as evidence that the demo is broken.