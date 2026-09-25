# 04 — Demo plan

Five minutes, one question: "what does this month's reconciliation say, where do the departments
disagree, and who has to decide what?"

> Written in English because it is spoken on stage and in the video. Every measured figure comes
> from [`00-status.md`](00-status.md); nothing here restates a number that is not measured there.
> The recorded version of this script is the demo video (see *Video* below).

## Before you start

- Start the local instance with `python scripts/start_web.py --demo` after `source env.sh`, with
  `PORTAL_BASE_URL` empty unless you are demonstrating Feishu login. `--demo` loads the sample
  dictionary; without it the sample imports but cannot be reviewed.
- The launcher prints `BridgeFlow model: …`. That model must have its key in the environment; a
  review on a model without one fails at the first call. Change it in *Sessions & settings*.
- Interface in English, a 1440-wide window, zoom 100%. Close the guided-tour welcome card
  (*Maybe later*).
- Rehearse once on the real model the same day. The review is the only billed beat.

## Run of show

| Time | Beat | What you click | What you say | Rubric |
| --- | --- | --- | --- | --- |
| 0:00–0:30 | The problem | Nothing yet: the empty notebook | "Four departments keep four monthly spreadsheets. Same customers, same projects, different spellings, different columns. Nobody here has a data team." | 1 |
| 0:30–1:15 | Four files, no preparation | Sources → **Open sample notebook**; click one file | "A fictional concrete supplier, July 2024. Four real business templates, imported and cleaned as they are. No model has been called and nothing has been charged." | 1, 3 |
| 1:15–2:00 | One table, and the one place it does not add up | Studio → **Data** → **Cross-department master**; open **Open questions**; click a figure | "Three of four rows are complete. Production shortened one customer's name; the table does not guess which is right, it asks. Every figure opens at its file, sheet and row." | 2, 6 |
| 2:00–3:00 | Four department agents | Studio → **This month's tasks** → **Start the review**; then the **Trajectory** tab; then the report under **Artifacts** | "The captain sends production, procurement, finance and marketing agents in parallel. They read computed metrics, never raw rows. Each finding carries its formula, threshold and source cells." | 2, 3 |
| 3:00–3:50 | A person decides | In the chat: ask the captain to record that the business confirmed the 13% VAT convention. **Reject** the first approval card with a reason, then ask again and **Allow once** | "Nothing is written until a person approves this exact change. My rejection and its reason go back to the model, and it says so. Approved, the figures resting on that convention move from G3 to G2." | 4, 5 |
| 3:50–4:30 | What happened, and what was stopped | Studio → **Records**: the run's lanes, tokens, refused calls | "Every run is recorded: which agent called which tool, how long it took, what it cost, what was refused. A spreadsheet cell that tries to instruct the agent is refused at dispatch and appears here." | 5, 6 |
| 4:30–5:00 | Close | Ask the captain "Where is the quadrant chart?"; it opens the page | "The captain knows the product: ask where anything is and it takes you there. Open items say how each is settled. The data is synthetic; the templates are the business's own." | 1, 7 |

If time is short, drop the last beat first, then shorten *What happened*. Never drop *A person
decides*.

## Two things to say unprompted

Judges will not infer either of these from watching ([`09`](09-rubric-assessment.md) argues the case):

1. The fixed pipeline is a choice, not a missing capability. Financial figures have to be auditable,
   replayable and attributable; an approver cannot sign a number that two runs derive differently.
   The framework's own `workflow` package lets the model write the orchestration script and
   describes itself as "containment, not a security boundary" ([`13` §7.4](13-golden-standard.md)).
   Declining it is the point.
2. Every conclusion is bound to evidence. `Finding` rejects an evidence-free claim at the schema
   layer: refused, not downgraded.

## If something goes wrong on stage

| Symptom | Say and do |
| --- | --- |
| The review fails at the first model call | "The model route has no key on this machine." Show the report already saved from the rehearsal under **Artifacts**. |
| The review takes long | Keep talking over the **Trajectory** tab; the four agents appear as they start. |
| The approval card does not appear | The request did not reach a write tool. Ask again naming the convention; never approve something you have not read. |
| Network down | Everything up to *Four department agents* runs offline. Say so, and show the recorded video from 2:00. |

## Demo safety rules

- Import and rule computation cost nothing. The review, the approval beat and captain questions call
  the configured model; the measured durations and token counts are in [`00`](00-status.md).
- If you fall back to the offline test model, say so out loud: it returns fixed text and proves only
  that the interface works.
- Every number shown must trace to a cell. A judge will ask where a percentage came from; open it
  and show the file, row and column.
- Do not present the sample as a customer's books. It is generated, labelled synthetic, and comes
  with an independent answer key that must never be fed to the model.

## Video

The five-minute video follows this run of show, recorded from the real product: the sample
notebook in an isolated `DSH_HOME`, the review and the approval on the real model, captions and
voice-over added in [HyperFrames](https://github.com/heygen-com/hyperframes). Its source lives
outside the repository (`~/Hackathon2026/demo-video/`); only the rendered file is handed in.
