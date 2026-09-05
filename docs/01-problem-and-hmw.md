# 01 — Problem framing & HMW

## How Might We

> How might we build a multi-agent AI engine for Singaporean SMEs to align unstructured
> monthly data across production, procurement, finance and marketing, in order to eliminate
> data silos, trigger real-time risk warnings, and optimize dynamic quotes?

## Who we are building for

Singaporean SMEs in light manufacturing / contract production — roughly 20–200 staff.
Characteristics that shape the design:

- **No data team.** Nobody will write SQL. The interface must accept the spreadsheet
  they already have, unchanged.
- **Excel is the system of record.** ERP exists in some, but the *decision* still happens
  in a monthly workbook emailed around.
- **Four departments, four vocabularies.** The same product is `SKU-A1`, `Alu bracket`,
  `4000-Sales/A1` and `Acme — bracket order` depending on who you ask.
- **Thin margins, volatile inputs.** Aluminium, freight and FX move faster than their
  quarterly price list.

## The three pains, restated as measurable goals

| Pain | Today | Target with BridgeFlow |
| --- | --- | --- |
| Data silos | ~1 week/month of manual reconciliation | < 10 min automated Master Table |
| Risk blindness | Loss-making orders found at year-end audit | Flagged in the month they occur |
| Static pricing | Price list updated 1–2×/year | Quote simulated per enquiry against live material cost + capacity |

## Why multi-agent (and not one big prompt)

Each stage has a different failure mode and a different notion of "correct":

1. **Sanitizing** is deterministic-ish and must be *auditable* — every correction is logged
   and reversible. Wrong answers here poison everything downstream.
2. **Semantic resolution** is fuzzy matching over entities with human-in-the-loop
   confirmation for low-confidence links. It needs to *ask*, not guess silently.
3. **Evaluation** is genuinely four different jobs with four different objective functions.
   The Production view and the Marketing view will disagree — that disagreement is signal,
   not a bug, and a single agent would average it away.
4. **SOP / quote generation** must be reproducible and explainable to a human approver.

Separating them lets us swap models per stage (cheap model for sanitizing, strong model for
evaluation), test each in isolation, and show a per-stage confidence trail in the demo.

## Explicitly out of scope for the hackathon

- Live ERP / accounting-system connectors (we ingest exported CSV/Excel).
- Multi-tenant auth and RBAC.
- Anything that writes back into a customer's source system.
