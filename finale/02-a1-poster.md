# 02 — A1 poster

**Goal:** decide whether to make a poster, then (if yes) design, print and collect an A1 poster that
explains BridgeFlow to someone standing two metres away in under a minute, and acts as the backdrop
for the pitch.

**Owner:** logistics, with one PM on copy and one designer on layout.
**Decision due:** Wednesday 7 October. **File to printer:** Thursday 8 October by 14:00.
**Collected and checked:** Friday 9 October.

## Decision: make one

**Recommendation: yes.** The poster is optional, but the booth already has a poster stand, so a
missing poster is conspicuous. It also does work the screen cannot:

- It holds the architecture diagram while the screen is busy with the live demo, so beat 2's
  one-sentence architecture has something to point at.
- It carries the measured results, so we do not have to recite them.
- It orients judges arriving early and passers-by between rounds, and appears in the photos.
- If the demo fails, the poster plus the fallback video still tell the whole story.

The risks are print turnaround and cost. Both are manageable if the file leaves on Thursday.

**Decide no only if** nobody can own the design on Thursday morning. In that case print the
architecture diagram and the measured-results table at A3 and tape them beside the monitor.

## Questions to settle first (Wednesday)

- [ ] **Stand type.** Ask Esther on Slack what the provided stand holds (easel for a rigid board,
      clip frame, or roll-up). This decides paper versus foam board.
- [ ] **Orientation.** Assume portrait unless the stand says otherwise.
- [ ] **Category branding.** Confirm the category (SME or Public) and whether organisers want their
      logo or the hackathon name on posters.
- [ ] **Budget and payer.**
- [ ] **Printer.** Pick a shop or online service that can print A1 with a same-day or next-day
      turnaround and confirm the deadline for Friday collection. Get a quote for both paper and foam
      board.

## Specifications

| Property | Value |
| --- | --- |
| Size | A1, 594 × 841 mm, portrait (confirm against the stand) |
| Bleed | 3 mm each side unless the printer asks for otherwise; keep text 15 mm inside the trim |
| File | PDF with fonts embedded, vector where possible |
| Raster images | At least 150 dpi at final size. A full-width screenshot at 150 dpi needs about 3,500 px width; use a Retina capture and crop rather than enlarge |
| Colour | Export as the printer requests (often RGB PDF is accepted; ask whether they want CMYK). Avoid large pure-black fills on paper |
| Material | Matte paper (cheapest, reduces glare under hall lighting) or 5 mm foam board if the stand is an easel |
| Type sizes | Title 120 pt or larger; section heads 60–72 pt; body 28–36 pt; captions no smaller than 22 pt |
| Readability test | Body text readable from 1.5 m; title and logline readable from 4 m |
| Word count | 250–350 words total. If it reads like the proposal, cut it in half |

## Tooling

Use what the team already knows. Two good options:

- **Typst**, reusing the submission's style (`git show c8a180a:submission/style.typ`). Same fonts and
  colours as the submitted documents, text under version control, exact PDF output.
- **Figma or Canva**, if the designer is faster there. Export a print PDF with bleed.

Either way, keep the source file and the exported PDF out of the public repository unless the team
decides otherwise (see the [README note](README.md#note-on-publishing)).

## Layout (portrait, top to bottom)

```
┌───────────────────────────────────────────────┐
│ BridgeFlow AI                     team · logo │  Title band
│ Four spreadsheets in, one signed-off           │
│ monthly review out.                            │
├───────────────────────────────────────────────┤
│ THE PROBLEM                                    │  ~15%
│ 4 department icons → 4 mismatched sheets       │
│ "≈1 week/month reconciling by hand"            │
├───────────────────────────────────────────────┤
│ HOW IT WORKS                                   │  ~35%
│ Architecture diagram (left → right):           │
│ Files → Python import & clean → Master table   │
│   → Captain → 4 department agents (parallel)   │
│   → Host evidence check → Brief                │
│   Approval card on every write                 │
├──────────────────────┬────────────────────────┤
│ SCREENSHOT A         │ SCREENSHOT B           │  ~20%
│ Cell traced to       │ Finding with formula,  │
│ file/sheet/row/col   │ threshold, G-grade     │
├──────────────────────┴────────────────────────┤
│ MEASURED (real model, 25 Sep 2026)             │  ~15%
│ 53.4 s · 4/4 agents · 75k tokens · cents       │
│ Injection refused · 21/22 tool choice · 31/31  │
├───────────────────────────────────────────────┤
│ WHY IT IS TRUSTWORTHY │ WHAT'S NEXT │ QR codes │  ~15%
└───────────────────────────────────────────────┘
```

## Copy (draft; final copy follows the locked narrative)

Copy must come from [doc 1](01-pitch-narrative.md), and every number from its whitelist.

**Title:** BridgeFlow AI
**Logline:** Four spreadsheets in, one signed-off monthly review out.
**Byline:** Team CONFLUX4 · NUS-ISS Show Me Your Agents Hackathon 2026 · Running on AWS

**The problem.** Production, Procurement, Finance and Marketing each keep their own monthly
spreadsheet. Same customers, different spellings. Same projects, different columns. SMEs without a
data team lose about a week a month reconciling them, and risks such as loss-making orders surface
at year-end.

**How it works.**
1. **Import & clean, no AI.** Python cleans each file under a field dictionary the business
   approves. Rows it cannot fix are quarantined, never dropped.
2. **One traceable table.** Metrics are computed from declared formulas. Every cell traces to file,
   sheet, row and column. Disagreements become questions for a person.
3. **Four agents, in parallel.** A captain agent dispatches production, procurement, finance and
   marketing agents. They read computed metrics, never raw rows.
4. **Evidence or rejection.** The host checks every finding's value, unit and citations. No
   evidence, no finding.
5. **People decide.** Every write waits on an approval card: allow once, or reject with a reason
   the agent hears.

**Measured with a real model (25 Sep 2026).** Re-check each before printing.
- Four-department review: 53.4 s, 8 requests, 75,267 tokens, a few US cents
- Instructions planted in a spreadsheet cell: reached no model session
- Right first tool among about 50: 21 of 22 cases
- Acceptance suite across three industries plus adversarial cases: 31/31

**Why you can trust it.** Code does the maths; agents do the judgement; people approve the writes.
Old months stay frozen as evidence. Raw rows never enter model context.

**What's next.** Pilot on real company exports · user-defined departments · Google Workspace
connector · per-evaluator guest seats.

**Footer:** All sample data is synthetic, modelled on a real business's templates. QR codes: the
public repository (`github.com/EricWang1358/BridgeFlow-AI`) and, only if it will be live on the day,
the guest demo.

## Visual assets to produce

| Asset | How | Owner |
| --- | --- | --- |
| Architecture diagram | Redraw cleanly (do not screenshot a doc); 6 boxes left to right, approval card as a gate under the write arrow. One accent colour for "AI", one for "code", one for "person" | Designer |
| Screenshot A: cell trace | Retina capture of Data → Cross-department master with a figure's source panel open | Demo driver |
| Screenshot B: finding | Retina capture of Conclusions with a finding's formula, threshold, cells and evidence grade | Demo driver |
| Optional screenshot C: approval card | Capture during the Thursday walkthrough | Demo driver |
| Department icons | Four simple icons; one family, one weight | Designer |
| QR codes | Generate locally; test each with two phones from 1.5 m | Logistics |

Take screenshots in English, at 1440×900 or larger, with no session token visible in the address
bar and no personal names on screen.

## Production schedule

| When | Step | Done |
| --- | --- | --- |
| Wed 7 Oct | Go/no-go; stand type and printer confirmed; copy draft from doc 1 | [ ] |
| Thu 8 Oct, 10:00 | Screenshots captured; numbers re-checked against the whitelist | [ ] |
| Thu 8 Oct, 12:00 | Layout v1; whole team reviews on screen at 25% zoom (simulates distance) | [ ] |
| Thu 8 Oct, 13:00 | Proof: print two A4 crops at 100% scale (title band and body text) and read from 1.5 m | [ ] |
| Thu 8 Oct, 14:00 | Final PDF to printer; written confirmation of collection time | [ ] |
| Fri 9 Oct | Collect; check against the proof checklist below; protect in a tube or flat bag | [ ] |
| Sat 10 Oct, 8:30 | Mount on the stand; photograph the booth before judging starts | [ ] |

## Proof checklist (before sending and on collection)

- [ ] Every number matches the whitelist, with the same rounding everywhere.
- [ ] Category and team name correct; no institutional branding that breaches the dress or
      branding guidance.
- [ ] Spelling, especially product names: BridgeFlow, DeepSeek, Feishu, Lark, AWS Lightsail.
- [ ] No session tokens, real names, phone numbers or emails in screenshots.
- [ ] QR codes scan from 1.5 m.
- [ ] "Synthetic data" disclosure present.
- [ ] Colours read correctly in print (check the proof under ordinary indoor light).
- [ ] Size and bleed as specified; nothing important within 15 mm of the edge.

## Backup

Keep the final PDF on two laptops and a USB stick. If the print fails or is damaged, show the poster
PDF full-screen on the booth monitor between rounds, and print the architecture diagram at A3 on the
morning as a stopgap.
