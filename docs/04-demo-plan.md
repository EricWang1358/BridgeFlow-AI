# 04 — Demo plan

Six minutes, one story: **"Should we take Acme's November order?"**

> **Audience: the judges. Written in English because it is spoken on stage.**
> Every number in it comes from [`00-status.md`](00-status.md) — do not restate a
> figure here that is not measured there.

## What can actually run today

**Read this column before rehearsing.** Most beats still have no UI: the self-built
frontend was deleted (`fea1fdd`), and of the plugins that replace it only the approval
half is written (#30). The pipeline behind beats 2–5 runs; what is mostly missing is the
screen. The one screen that exists is the operator console, and it is the screen that
carries rubric item 4.

| # | Beat | Rubric | Runs today? | Fallback if it does not |
| - | ---- | ------ | ----------- | ----------------------- |
| 1 | Show the four real spreadsheets. Different dates, different SKU spellings, a shifted header row, a merged cell. "This is a normal Tuesday." | 1 | ✅ Excel, no code needed | — |
| 2 | Drop all four in. Correction log streams in. | 1, 6 | 🟡 Pipeline yes, **no upload UI** | Run the sanitizer at the terminal and show `CorrectionLog` |
| 3 | Resolver shows the entity graph. Presenter confirms a low-confidence link in one click. "It learns this once." | 4 | 🟡 **The confirmation half runs end to end.** The tool call blocks on a person, the pending decision appears at `/console`, one click releases it, and the mapping is written naming who approved it. Measured: 3.1s to the console, 4.0s to turn end. Click 拒绝 instead and nothing is written. **Still no entity graph** (#40) | Show the console and the two outcomes; describe the graph rather than showing it |
| 4 | Master Table appears. One aligned table from four files. | 2 | 🟡 Built, **no screen**; and the join key is guessed (#44) | Print the table; do not claim the join is safe |
| 5 | Four role panels. Finance: margin negative. Procurement: Alu-6061 +18%. Production: Line 2 at 94%. Marketing: Acme is Tier C. **The tension is the punchline.** | 3, 6 | 🟡 Margin and the price change are computed by rule and cite their cells (#13, #65). **Still missing: line utilisation needs a declared capacity ceiling, and customer tiering has no rule at all.** No screen either (#40) | Show the metric tool output at the terminal; do not claim the two missing figures |
| 6 | Quote Simulator → floor / target / stretch + 45-day terms instead of 90. | 4 | ❌ Price bands are asserted by the model, not computed (#7) | Cut the beat rather than assert a number we cannot derive |
| 7 | Close on the HMW slide. | 1 | ✅ | — |

### Rehearse beat 3 like this

Have the console open on a second screen *before* the turn starts. The point lands only
if the judges watch the agent stop and wait. Say the sentence out loud while it is
waiting: **"nothing has been written yet, and if I walk away now nothing will be."** Then
click 拒绝 first and re-run to approve — the refusal is the more interesting half, and it
is the half no other team will show.

**As of 2026-09-06 the honest demo is beats 1, 2, 3 (confirmation half), 7 plus a
terminal walkthrough.**
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
