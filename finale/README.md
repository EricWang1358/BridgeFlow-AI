# Finale preparation: NUS-ISS Show Me Your Agents Hackathon

Team **CONFLUX4** is shortlisted for the Finale on **Saturday 10 October 2026** at NUS-ISS
(25 Heng Mui Keng Terrace, Singapore 119615). This directory holds the plan for getting from
shortlist to stage. It is internal preparation material, not product documentation.

## What the Finale asks of us

| Item | Detail |
| --- | --- |
| Format | Two judging rounds, **15 minutes each, Q&A included**. Round 1: 9:45–11:00. Round 2: 11:15–12:30 |
| Bring | A1 poster (optional), video demonstration, prototype or working demo, supporting material |
| Judges want | The business problem, how the agentic solution works, the value or impact |
| Booth provides | One monitor, extension cables, one poster stand. Laptops, adapters and chargers are ours |
| Arrival | From 8:30. Setup complete by **9:00**. At Influence for the opening by **9:25** |
| Booth area | SME Category: Wissdom Park. Public Category: Bisstro. **Confirm our category** (the product targets SMEs, but the category is whatever we registered under) |
| Attendance | All registered members. Any absence needs a valid reason sent to Esther or Jerome in advance |
| Dress | Smart casual. No shorts, slippers, singlets, or apparel with tertiary-institution branding |
| If we win | NUS-ISS Annual Luncheon, **Monday 19 October 2026, 11:30–14:00**, Conrad Singapore Orchard, with a solution showcase. Hold the date now |

## The five workstreams

| # | Doc | Output | Depends on | Due |
| --- | --- | --- | --- | --- |
| 1 | [Pitch narrative](01-pitch-narrative.md) | Locked three-beat story, spoken script, number whitelist | — | **Wed 7 Oct, end of day** |
| 2 | [A1 poster](02-a1-poster.md) | Go/no-go decision, print-ready PDF, printed poster collected | 1 | Decision Wed; file to printer **Thu 8 Oct**; collected **Fri 9 Oct** |
| 3 | [Demo script](03-demo-script.md) | Five-minute click path, environment plan, fallback video | 1 | Draft Thu 8 Oct; frozen after the Thu run-through |
| 4 | [Q&A sheet](04-qa-sheet.md) | Answers to the likely questions, owner per topic | 1, 3 | Draft Thu 8 Oct; final after rehearsal |
| 5 | [Dress rehearsal](05-dress-rehearsal.md) | Two timed run-throughs, packing list, day-of runbook | 1–4 | Run-through Thu evening; **full dress Fri 9 Oct** |

The narrative comes first because the poster, the demo and the Q&A answers are all built against
it. Changing the story after Thursday means reprinting and re-rehearsing, so treat it as locked once
the team signs off.

## Timeline

| When | What |
| --- | --- |
| **Wed 7 Oct, before 15:00** | Reply to the organisers with dietary requirements or allergies. Without a reply, a standard halal-certified meal is provided. Confirm whether any member cannot attend |
| Wed 7 Oct | Lock the narrative (doc 1). Decide poster go/no-go and the layout (doc 2). Assign roles (below). Confirm category and booth area with Esther on Slack if unclear |
| Thu 8 Oct, morning | Poster copy and figures final; designer builds layout; proof at 100% scale on A4 crops |
| Thu 8 Oct, by 14:00 | Poster PDF sent to the printer, turnaround confirmed |
| Thu 8 Oct | Demo script drafted and walked through on the real instance. Re-measure any figure we intend to quote (doc 1 whitelist). Q&A sheet drafted |
| Thu 8 Oct, evening | Run-through 1: pitch + demo + mock Q&A, timed. Fix list |
| Fri 9 Oct | Collect the poster. Record or refresh the fallback demo video. **Full dress rehearsal** at roughly 9:45, in outfits, on the laptop and adapters we will bring. Pack |
| Sat 10 Oct | Day-of runbook (doc 5): arrive 8:30, set up by 9:00, Influence 9:25, Round 1 9:45, debrief, Round 2 11:15, lunch, prizes 13:30–14:00 |

## Roles (fill in names)

| Role | Owns | Name |
| --- | --- | --- |
| Lead presenter | Beats 1 and 3 of the pitch, opening and close | |
| Demo driver | The laptop during the demo, the click path, fallbacks | |
| Demo narrator | Talks over the demo if the driver is not also narrating | |
| Q&A lead | Takes each question, answers or routes it to the owner in the Q&A sheet | |
| Timekeeper | Silent time cues during the slot; keeps the team on the 15-minute budget | |
| Logistics | Poster print and collection, packing list, organiser replies | |

The team is two full-stack developers and two product managers. A natural split: a PM presents,
the developer who knows the product best drives the demo, the other developer leads technical Q&A,
and the other PM owns business Q&A, timing and logistics.

## Sources used for these plans

The facts in these documents come from the submitted package and the repository at `main`:

- The submitted business proposal and technical document (commit `c8a180a`, `submission/*.typ`;
  removed from the public tree by `268e594` but still in history).
- The seven-beat demo run of show and failure table, last version at `268e594^:docs/04-demo-plan.md`.
- The organisers' seven judging criteria, as recorded in `268e594^:docs/09-rubric-assessment.md`.
- Current product behaviour: [README](../README.md), [user guide](../docs/user-guide.en.md),
  [architecture](../docs/architecture.md), [limitations](../docs/limitations.md).

Any figure quoted on stage or on the poster must appear in the whitelist in
[doc 1](01-pitch-narrative.md#numbers-we-may-quote) with its date and source.

## Note on publishing

The repository is public, and the release sanitisation (`268e594`) deliberately moved internal
planning out of it. Decide before pushing this branch whether these notes belong in the public
repository or in a private location.
