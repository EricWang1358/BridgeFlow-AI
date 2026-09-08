# 01 — Problem framing and HMW

## How might we

> How might we build a multi-agent AI engine for Singaporean SMEs that aligns unstructured
> monthly data across production, procurement, finance and marketing, so that data silos go away,
> risk warnings arrive while the month is still open, and quotes can be priced against real cost?

## Who we are building for

Singaporean SMEs in light manufacturing and contract production, roughly 20 to 200 staff.
Four characteristics of this segment shape the design:

- There is no data team. Nobody will write SQL, so the interface has to accept the spreadsheet
  they already keep, not a schema we invent for them.
- Excel is the system of record. Some have an ERP, but the decision still gets made in a monthly
  workbook that is emailed around.
- Four departments, four vocabularies. The same product is `SKU-A1`, `Alu bracket`,
  `4000-Sales/A1` and `Acme — bracket order` depending on who you ask.
- Thin margins and volatile inputs. Aluminium, freight and FX move faster than a quarterly
  price list can.

## The three pains, as measurable goals

| Pain | Today | With BridgeFlow |
| --- | --- | --- |
| Data silos | about a week per month of manual reconciliation | a master table in under 10 minutes |
| Risk blindness | loss-making orders surface at year-end audit | flagged in the month they occur |
| Static pricing | price list refreshed once or twice a year | a quote simulated per enquiry against material cost and capacity |

## Why several agents instead of one big prompt

Each stage fails differently, which means each has a different notion of correct:

1. **Sanitising** is close to deterministic and has to be auditable: every correction logged,
   reversible, attributable. Get it wrong here and everything downstream is poisoned.
2. **Semantic resolution** is fuzzy matching over entities, with a human confirming the
   low-confidence links. It needs to ask rather than guess quietly.
3. **Evaluation** is really four jobs with four objective functions. Production and Marketing will
   disagree about the same month, and that disagreement is the signal. A single agent averages it away.
4. **Quote and report generation** has to be reproducible and explainable to whoever approves it.

Splitting them lets us pick a model per stage (cheap for cleaning, strong for judgement), test each
stage separately, and show a per-stage trail in the demo.

## Out of scope for the hackathon

- Live ERP or accounting connectors. We ingest exported CSV and Excel.
- Multi-tenant authentication and RBAC.
- Anything that writes back into a customer's source system.
