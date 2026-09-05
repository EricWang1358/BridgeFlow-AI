# 04 — Demo plan

Six minutes, one story: **"Should we take Acme's November order?"**

> **Audience: the judges. Written in English because it is spoken on stage.**
> Every number in it comes from [`00-status.md`](00-status.md) — do not restate a
> figure here that is not measured there.

## What can actually run today

**Read this column before rehearsing.** Four of the seven beats have no UI at all: the
self-built frontend was deleted (`fea1fdd`) and the dsh web plugins that replace it are
not written — `plugins/` does not exist yet (#40). The pipeline behind beats 2–5 runs;
what is missing is the screen.

| # | Beat | Rubric | Runs today? | Fallback if it does not |
| - | ---- | ------ | ----------- | ----------------------- |
| 1 | Show the four real spreadsheets. Different dates, different SKU spellings, a shifted header row, a merged cell. "This is a normal Tuesday." | 1 | ✅ Excel, no code needed | — |
| 2 | Drop all four in. Correction log streams in. | 1, 6 | 🟡 Pipeline yes, **no upload UI** | Run the sanitizer at the terminal and show `CorrectionLog` |
| 3 | Resolver shows the entity graph. Presenter confirms a low-confidence link in one click. "It learns this once." | 4 | ❌ **No confirmation UI, and confirmations are not persisted** (#29, #40) | Show `unresolved` in the JSON and say the queue exists at the type level only |
| 4 | Master Table appears. One aligned table from four files. | 2 | 🟡 Built, **no screen**; and the join key is guessed (#44) | Print the table; do not claim the join is safe |
| 5 | Four role panels. Finance: margin negative. Procurement: Alu-6061 +18%. Production: Line 2 at 94%. Marketing: Acme is Tier C. **The tension is the punchline.** | 3, 6 | 🟡 Margin and the price change are computed by rule and cite their cells (#13, #65). **Still missing: line utilisation needs a declared capacity ceiling, and customer tiering has no rule at all.** No screen either (#40) | Show the metric tool output at the terminal; do not claim the two missing figures |
| 6 | Quote Simulator → floor / target / stretch + 45-day terms instead of 90. | 4 | ❌ Price bands are asserted by the model, not computed (#7) | Cut the beat rather than assert a number we cannot derive |
| 7 | Close on the HMW slide. | 1 | ✅ | — |

**As of 2026-09-06 the honest demo is beats 1, 2, 7 plus a terminal walkthrough.**
Beats 3–6 need the week-1 and week-2 work. This table is the acceptance criterion for
#41 — when every row reads ✅, the demo is real.

### The beat that is not in the script yet

Once #26 lands, add an eighth: **a poisoned cell tries to give the agent an instruction,
the guard refuses it, and the attempt is in the audit log.** `docs/09` argues this is the
cheapest move from zero to best-in-room, because most teams will demo a working pipeline
and none will demo an attack being stopped.

## Two things to say out loud, unprompted

From [`09-rubric-assessment.md`](09-rubric-assessment.md) — judges will not infer either:

1. **The fixed pipeline is a deliberate choice, not a missing capability.** Financial
   figures must be auditable, replayable and attributable; an approver cannot sign a
   number that two runs would derive differently. dsh's own `workflow` package — which
   lets the *model* write the orchestration script — is exactly what we declined, and it
   describes itself as "containment, not a security boundary" (`13` §7.4).
2. **Every conclusion is bound to evidence.** `Finding` rejects an evidence-free
   conclusion at the schema layer — it is not downgraded, it is refused. That is the most
   direct answer to rubric 6, so say it rather than hoping someone notices.

## Demo safety rules

- **Rehearse on the real provider, not on mock.** Mock returns
  `mock-justification-<hash>`: it proves the code does not crash and proves nothing else.
  Keep mock as the offline fallback if the network fails on stage, and say so if you use it.
- Sample files in `data/samples/` are committed and are the ones used on stage.
- Every number shown must be traceable to a row — a judge will ask "where did 18% come
  from?" **Today most of them are not.** That is what beat 5's ❌ means.
- Budget for the live run: the suite bills a real API and takes minutes, not seconds.
  See [`00-status.md`](00-status.md) §4.
