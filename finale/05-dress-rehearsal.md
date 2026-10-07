# 05 — Full dress rehearsal

**Goal:** run the whole 15-minute slot twice under Finale conditions, with the people, laptop,
adapters, network and clothes we will use on Saturday, and leave Friday night with nothing left to
decide. This document also holds the packing list and the Saturday runbook.

**Owner:** timekeeper (runs the rehearsal), with logistics for packing.
**When:** run-through 1 on Thursday 8 October, evening; full dress on Friday 9 October, ideally
starting around 9:45 so the model provider, network and our energy match the real slot time.

## Definition of done

- [ ] Two complete slots run back to back, each within 15:00, with at least 5:00 of Q&A.
- [ ] One slot includes an unannounced failure, recovered without losing more than 30 s.
- [ ] Reset between slots completed in under two minutes.
- [ ] Setup from a packed bag to "ready" timed under 20 minutes.
- [ ] Scorecard averages at least 4 of 5 on every rubric row; any row below 4 has a fix assigned.
- [ ] Packing list checked and the bag packed on Friday night.
- [ ] Every member knows the Saturday runbook times without looking.

## Run-through 1 (Thursday evening, about 90 minutes)

Lower fidelity: the aim is to find problems while there is still a day to fix them.

| Time | Activity |
| --- | --- |
| 0:00 | Read the narrative (doc 1) aloud once, timed per beat |
| 0:10 | Demo (doc 3) three times in a row on the chosen environment; time each beat |
| 0:35 | Mock Q&A: each topic owner answers their section of doc 4; challenge and time |
| 1:05 | One full 15-minute slot end to end |
| 1:20 | Fix list: owner and deadline for each item; decide anything still open (environment, cuts, roles) |

Outputs: a frozen demo order, a fix list, and a draft of the five-minute fallback video if it is
still missing.

## Full dress (Friday)

### Conditions to simulate

- **Standing,** in Saturday's clothes and shoes (smart casual; no shorts, slippers, singlets, or
  tertiary-institution branding).
- **External monitor** over the adapter we will bring, at the zoom level in doc 3, read from 2 m.
- **Phone hotspot** as the only network, unless the venue Wi-Fi is confirmed.
- **The printed poster** on a stand or taped to a wall behind the presenter.
- **Outside judges:** at least two people who have not seen the product, given doc 4 and told to ask
  anything. Brief one to interrupt the demo once.
- **Hard stop at 15:00:** the timekeeper ends the slot mid-sentence if needed.
- **Background noise:** play recorded crowd noise or rehearse in a common area; the booth area will
  not be quiet.

### Agenda (about 2 hours)

| Time | Activity |
| --- | --- |
| 0:00 | **Cold setup.** Unpack from the bag, connect, start the instance, open the sample notebook, run the "before each slot" checklist from doc 3. Target: under 20 minutes (on Saturday we have 30) |
| 0:20 | **Slot 1.** Full 15 minutes: pitch, demo, Q&A |
| 0:35 | Judges score (scorecard below); team debrief, 10 minutes |
| 0:45 | **Reset** between rounds (doc 3), timed |
| 0:50 | **Slot 2** with an unannounced failure injected by the timekeeper (pick one from the drills below) |
| 1:05 | Judges score; debrief |
| 1:15 | Booth drill: 60-second version (doc 1) to three "walk-up visitors" in a row |
| 1:25 | Packing check against the list below; bag packed |
| 1:45 | Go / no-go (below) |

### Positions and handovers

```
          [ poster stand ]
 [ presenter ]           [ booth monitor ]
            [ demo driver at laptop ]
   [ Q&A lead ]   [ timekeeper, in judges' sightline but behind them if possible ]
```

- The presenter stands beside the poster and points to the architecture diagram for beat 2's
  one-sentence architecture.
- The demo driver sits or stands at the laptop and does not block the monitor.
- Handover lines are fixed: presenter to driver: *"Let me show you July."* Driver to presenter: *"So
  that is the month. What does it change for the business?"*
- The timekeeper gives silent cues with cards: **2 min** left in demo, **wrap** (30 s), **Q&A**
  (switch), **2 min** left in slot.

### Failure drills

The timekeeper injects one per dress slot without warning. All must have been practised at least once
by Friday night.

| Drill | Expected recovery |
| --- | --- |
| Turn the hotspot off during the review | Switch network or play the fallback video from that beat; narrate live |
| Unplug the monitor adapter | Reconnect, or turn the laptop to face the judges and continue |
| "Start the review" greyed out | Read the reason aloud; switch to *All clear: ready to review* |
| No approval card appears | Paste the request again naming the convention |
| A judge interrupts during beat 2 with "how is this different from Excel Copilot?" | One-sentence answer, then return to the demo |
| The presenter forgets a beat | The demo driver picks up the line; practise this once |
| A judge asks something not on the sheet | "We have not measured that; here is what we know…" Log it |

### Scorecard (one per judge per slot)

Score 1–5. Rows 1–7 are the organisers' judging criteria; rows 8–11 are delivery.

| # | Criterion | What a 5 looks like | Score |
| --- | --- | --- | --- |
| 1 | Goal & Scope | Clear user, clear pain, clear limits | |
| 2 | Architecture & Reasoning Loop | Fixed pipeline explained as a choice; captain and four parallel agents seen | |
| 3 | Tool Use & Integration | Typed tools visible in Trajectory; captain navigates the product | |
| 4 | Autonomy & Human-in-the-Loop | Reject with reason, agent adapts, allow once | |
| 5 | Safety, Security & Guardrails | Injection refused; raw rows never reach the model; key isolation explained | |
| 6 | Observability & Evaluation | Cell trace; Records with tokens and refused calls; evaluation figures | |
| 7 | Platform & Tooling Usage | Official harness used idiomatically; AWS deployment stated | |
| 8 | Business problem landed in the first 75 s | | |
| 9 | Wow moment landed before 1:00 of the demo | | |
| 10 | Value and the ask were clear | | |
| 11 | Q&A: concise, honest, one speaker per answer | | |
| — | Total time, demo time, Q&A time | | |

Debrief questions: what did the judges remember a minute later? What confused them? Which answer was
weakest? What would we cut?

## Go / no-go (Friday night)

All must be true; otherwise assign the fix and re-test before bed.

- [ ] Demo environment works on the demo laptop over the hotspot.
- [ ] Fallback video plays offline on two devices and a USB stick.
- [ ] Poster collected and checked (doc 2), or the stopgap plan is ready.
- [ ] Every whitelist number re-checked and consistent across poster, script and Q&A sheet.
- [ ] Model gate budget covers six reviews plus margin; API key valid; provider status normal.
- [ ] Each member knows their role, arrival time and what they are carrying.

## Packing list

**Demo hardware**

- [ ] Demo laptop, fully charged, with the environment ready and tested
- [ ] Backup laptop with the same setup (or at least the fallback video and poster PDF)
- [ ] Chargers for both laptops and phones
- [ ] Video adapters: USB-C to HDMI, USB-C to DisplayPort, and an HDMI cable (the booth monitor's
      input is unknown)
- [ ] Phone hotspot plus a second phone on a different carrier if possible; a power bank
- [ ] Wireless mouse or presentation clicker
- [ ] USB stick: fallback videos, poster PDF, screenshots, Q&A sheet
- [ ] Small power strip with a universal plug (extension cables are provided, but outlets may be
      shared)

**Print**

- [ ] A1 poster, protected in a tube or flat case
- [ ] Q&A sheet, one per member
- [ ] Two copies of the demo script with the cut order and failure table
- [ ] Optional: one-page handout or business card with the repository QR code

**Personal**

- [ ] Smart casual outfit, covered shoes
- [ ] ID, water, snacks for the gap between rounds
- [ ] Tape, scissors and cable ties for the poster and cables

## Saturday 10 October runbook

| Time | What | Who |
| --- | --- | --- |
| Before leaving | Check the provider status page and the gate. Confirm everyone is on the way | Logistics |
| **8:30** | Arrive at NUS-ISS, 25 Heng Mui Keng Terrace. Go to our category's area (SME: Wissdom Park; Public: Bisstro) | All |
| 8:30–8:45 | Mount the poster. Connect the laptop to the booth monitor. Test the hotspot and venue Wi-Fi | Logistics, demo driver |
| 8:45–9:00 | Start the instance, open the sample notebook, run the doc 3 checklist. Run one review as a warm-up to confirm the model path end to end | Demo driver |
| **9:00** | **Setup complete.** Reset the instance after the warm-up review. Loop the submitted demo video on the monitor while waiting | Demo driver |
| **9:25** | **At Influence** for the opening. Take the laptop or leave it with the screen locked | All |
| **9:45–11:00** | **Round 1.** Our slot time within the round: confirm on arrival. Fifteen minutes before our slot: re-run the checklist | All |
| After our round 1 slot | 5-minute debrief: questions asked, what landed, what to change. Log questions in doc 4. Reset the instance | Q&A lead, demo driver |
| 11:00–11:15 | Break. Snack, water, re-check the gate budget | All |
| **11:15–12:30** | **Round 2.** Same procedure. Treat these judges as new unless told otherwise | All |
| 12:30 | Lunch (dietary requirements were due to the organisers on Wednesday 7 October, 15:00) | All |
| **13:30–14:00** | **Prize presentation** | All |
| After | Pack up. Photograph the booth. Note contacts made and promised follow-ups | Logistics |

Between rounds, nobody changes code, data or configuration on the demo laptop.

## After the Finale

- Hold **Monday 19 October 2026, 11:30–14:00** (NUS-ISS Annual Luncheon, Conrad Singapore Orchard).
  Winners must attend and showcase their solution, so keep the demo laptop and poster as they are
  until the results are known.
- Send follow-ups to anyone who asked about a pilot within two working days.
- Add a short retrospective to this directory: what the judges asked, what worked, what to change.
