# 04 — Demo plan

Six minutes, one story: **"Should we take Acme's November order?"**

| # | Beat | Screen | Time |
| - | ---- | ------ | ---- |
| 1 | Show the four real spreadsheets. Different dates, different SKU spellings, a shifted header row, a merged cell. "This is a normal Tuesday." | Excel | 0:45 |
| 2 | Drop all four into BridgeFlow. Correction log streams in — 47 fixes, 3 rows quarantined. | Upload | 1:00 |
| 3 | Resolver shows the entity graph. Two links flagged low-confidence; presenter confirms one in a click. "It learns this once." | Resolve | 1:00 |
| 4 | Master Table appears. One aligned table from four files. | Master | 0:30 |
| 5 | Four role panels light up. Finance: "Acme's project margin went negative." Procurement: "because Alu-6061 is +18%." Production: "and Line 2 is at 94%." Marketing: "Acme is Tier C." **The tension is the punchline.** | Risks | 1:30 |
| 6 | Open Quote Simulator for Acme's next enquiry → floor / target / stretch price + 45-day terms instead of 90. | Quote | 1:00 |
| 7 | Close on the HMW slide. | — | 0:15 |

## Demo safety rules

- `LLM_PROVIDER=mock` must reproduce the entire flow offline. Rehearse on mock.
- Sample files in `data/samples/` are committed and are the ones used on stage.
- Every number shown must be traceable to a row — a judge will ask "where did 18% come from?"
