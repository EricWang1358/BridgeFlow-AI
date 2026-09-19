/**
 * The look of the BridgeFlow surfaces inside the native shell.
 *
 * Written as readable CSS on purpose. The previous version was one declaration per
 * line with no spacing, which made it effectively unreviewable — and an unreviewable
 * stylesheet is how a UI drifts into looking unowned.
 *
 * Three rules hold throughout:
 *
 * - **Inherit the shell, do not fight it.** Colours resolve from the host's own
 *   `--background` / `--foreground` first, so BridgeFlow follows the user's theme
 *   instead of painting a second design system on top of the first.
 * - **One primary action per surface.** Everything else is quiet. A screen where six
 *   buttons look identical is a screen that tells you nothing about what to do next,
 *   which was the state this replaces.
 * - **Data gets room.** Tables scroll horizontally rather than compressing columns;
 *   a header that wraps one character per line is not a cosmetic problem, it is an
 *   unreadable table.
 */
export const style = `
.bf-panel, .bf-state, .bf-drawer, .bf-card, .bf-hero, .bf-open {
  /* Surfaces sit on the host's background; the second surface lifts off it slightly. */
  --bf-surface: var(--background, #fff);
  --bf-surface-2: #f4f6f9;
  --bf-line: #d8dee6;
  --bf-line-strong: #b6c0cc;
  --bf-text: var(--foreground, #101b27);
  --bf-muted: #5b6b7c;
  --bf-accent: #2f6bd8;
  --bf-accent-soft: #e8f0fd;
  --bf-warn: #8a4b06;
  --bf-warn-bg: #fdf3e0;
  --bf-ok: #10643d;
  --bf-ok-bg: #e6f5ec;
  --bf-danger: #9d271c;
  --bf-danger-bg: #fdeceb;
  --bf-sans: 'Source Sans 3', 'Source Sans Pro', system-ui, -apple-system, 'Segoe UI',
    'Noto Sans SC', 'Source Han Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --bf-serif: 'Source Serif 4', 'Source Serif Pro', 'Noto Serif SC', 'Source Han Serif SC',
    Georgia, 'Songti SC', serif;
  --bf-radius: 10px;
  --bf-shadow: 0 1px 2px #0f172a12, 0 8px 24px #0f172a14;
  color: var(--bf-text);
  font-family: var(--bf-sans);
  font-variant-numeric: tabular-nums;
}

/* ---- typography -------------------------------------------------------- */

.bf-panel h2, .bf-state h2 { font-family: var(--bf-serif); font-size: 20px; font-weight: 700; margin: 0; letter-spacing: -.01em }
.bf-brief-headline, .bf-card-head h3 { font-family: var(--bf-serif) }
.bf-panel h3, .bf-state h3 { font-size: 15px; font-weight: 640; margin: 0 0 6px }
.bf-report h4 { font-size: 14px; font-weight: 640; margin: 0 0 8px }
.bf-panel p, .bf-state p, .bf-card p { line-height: 1.65; margin: 6px 0 }
.bf-hint { font-size: 12px; color: var(--bf-muted); line-height: 1.6 }
.bf-lead { color: var(--bf-muted); margin: 4px 0 0 }
.bf-mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px }

/* ---- panel shell ------------------------------------------------------- */

/* The [open] qualifier is load-bearing: a bare .bf-panel rule with display:grid
   outranks the user agent's own dialog:not([open]) { display: none }, which leaks
   the closed panel onto the shell. Seen once, in a screenshot, before anybody had
   clicked anything. */
.bf-panel[open] {
  background: var(--bf-surface);
  border: 1px solid var(--bf-line);
  border-radius: 14px;
  box-shadow: var(--bf-shadow);
  padding: 0;
  width: min(1180px, 94vw);
  max-width: min(1180px, 94vw);
  /* Height follows the content: the import step is short, the master table is long.
     A fixed height left two thirds of the panel empty on the screen a first-time
     user sees first. */
  max-height: min(880px, 90vh);
  overflow: hidden;
  display: grid;
  grid-template-rows: auto 1fr;
}
.bf-panel::backdrop { background: #0b16247a; backdrop-filter: blur(2px) }
.bf-panel:not([open]) { display: none }

.bf-panel-head {
  display: flex; align-items: flex-start; gap: 16px;
  padding: 18px 24px 14px;
  border-bottom: 1px solid var(--bf-line);
  background: var(--bf-surface);
}
.bf-panel-head > div:first-child { flex: 1; min-width: 0 }
.bf-panel-body { overflow: auto; padding: 20px 24px 28px }

/* Secondary entrances. They are always available and rarely the point, so they read
   as links rather than as the first thing on the panel. */
.bf-panel-body > details > summary {
  cursor: pointer; font-size: 12px; color: var(--bf-muted);
  padding: 3px 0; list-style-position: outside;
}
.bf-panel-body > details > summary:hover { color: var(--bf-text) }
.bf-panel-body > details[open] > summary { margin-bottom: 8px }
.bf-panel-body > details { margin: 0 0 4px }
.bf-panel-body > details[open] { margin-bottom: 20px }

/* ---- buttons ----------------------------------------------------------- */

.bf-panel button, .bf-card button, .bf-state button, .bf-drawer button, .bf-open {
  font: inherit;
  border: 1px solid var(--bf-line-strong);
  border-radius: 8px;
  padding: 7px 13px;
  background: var(--bf-surface);
  color: inherit;
  cursor: pointer;
  transition: background .12s, border-color .12s;
}
.bf-panel button:hover:not(:disabled), .bf-card button:hover:not(:disabled),
.bf-state button:hover:not(:disabled), .bf-open:hover { background: var(--bf-surface-2) }
.bf-panel button:disabled, .bf-card button:disabled, .bf-drawer button:disabled { opacity: .45; cursor: default }

/* One primary per surface. It is the action that moves the work forward. */
.bf-primary {
  background: var(--bf-accent) !important;
  border-color: var(--bf-accent) !important;
  color: #fff !important;
  font-weight: 600;
}
.bf-primary:hover:not(:disabled) { filter: brightness(1.07) }
.bf-quiet { border-color: transparent !important; color: var(--bf-muted) !important; padding: 6px 8px !important }
.bf-quiet:hover:not(:disabled) { color: var(--bf-text) !important }
.bf-danger-btn { border-color: var(--bf-danger) !important; color: var(--bf-danger) !important }

.bf-actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 14px 0 }

/* ---- forms ------------------------------------------------------------- */

.bf-panel input, .bf-panel select, .bf-state input, .bf-drawer input, .bf-card textarea {
  font: inherit;
  border: 1px solid var(--bf-line-strong);
  border-radius: 7px;
  padding: 7px 9px;
  color: inherit;
  background: var(--bf-surface);
  max-width: 100%;
}
.bf-panel input:focus-visible, .bf-card textarea:focus-visible { outline: 2px solid var(--bf-accent); outline-offset: 1px }

/* Numbered steps: the import panel is a sequence, so it should look like one. */
.bf-steps { counter-reset: bf-step; display: grid; gap: 18px; margin: 4px 0 0 }
.bf-step { position: relative; padding-left: 34px }
.bf-step::before {
  counter-increment: bf-step; content: counter(bf-step);
  position: absolute; left: 0; top: 0;
  width: 23px; height: 23px; border-radius: 50%;
  background: var(--bf-accent-soft); color: var(--bf-accent);
  font-size: 12px; font-weight: 700;
  display: grid; place-items: center;
}
.bf-step > h3 { margin: 2px 0 8px }

/* A file row that shows the chosen filename instead of the browser's own English
   "No file chosen", which is the single most out-of-place string in the product. */
.bf-files { display: grid; gap: 8px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)) }
.bf-file {
  display: flex; align-items: center; gap: 10px;
  border: 1px dashed var(--bf-line-strong); border-radius: 9px;
  padding: 10px 12px; cursor: pointer; min-width: 0;
  transition: border-color .12s, background .12s;
}
.bf-file:hover { border-color: var(--bf-accent); background: var(--bf-accent-soft) }
.bf-file[data-filled=true] { border-style: solid; border-color: var(--bf-ok); background: var(--bf-ok-bg) }
.bf-file input { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none }
.bf-file-name { display: block; font-size: 12px; color: var(--bf-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.bf-file[data-filled=true] .bf-file-name { color: var(--bf-ok) }
.bf-file:focus-within { outline: 2px solid var(--bf-accent); outline-offset: 2px }

/* ---- callouts: a state and what to do about it -------------------------- */

.bf-callout {
  border: 1px solid var(--bf-line);
  border-left: 3px solid var(--bf-muted);
  border-radius: 8px;
  padding: 12px 14px;
  margin: 12px 0;
  background: var(--bf-surface-2);
}
.bf-callout h3 { font-size: 13px; margin: 0 0 4px }
.bf-callout p { margin: 0 }
.bf-callout[data-tone=warn] { border-left-color: var(--bf-warn); background: var(--bf-warn-bg); color: var(--bf-warn) }
.bf-callout[data-tone=danger] { border-left-color: var(--bf-danger); background: var(--bf-danger-bg); color: var(--bf-danger) }
.bf-callout[data-tone=ok] { border-left-color: var(--bf-ok); background: var(--bf-ok-bg); color: var(--bf-ok) }
.bf-callout[data-tone=info] { border-left-color: var(--bf-accent); background: var(--bf-accent-soft) }
.bf-error { color: var(--bf-danger) }

/* ---- status band ------------------------------------------------------- */

.bf-band { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin: 0 0 2px }
.bf-band .bf-period { font-size: 22px; font-weight: 660; letter-spacing: -.02em }
.bf-stats { display: flex; gap: 20px; flex-wrap: wrap; margin: 14px 0 }
.bf-stat { min-width: 74px }
.bf-stat b { display: block; font-size: 21px; font-weight: 640; line-height: 1.2 }
.bf-stat span { font-size: 12px; color: var(--bf-muted) }

/* ---- tabs -------------------------------------------------------------- */

.bf-tabs { display: flex; gap: 2px; flex-wrap: wrap; margin: 18px 0 0; border-bottom: 1px solid var(--bf-line); padding-bottom: 0 }
.bf-tabs button {
  border: 0 !important; border-radius: 8px 8px 0 0 !important;
  background: transparent !important; color: var(--bf-muted) !important;
  padding: 9px 14px !important; margin-bottom: -1px;
  border-bottom: 2px solid transparent !important;
}
.bf-tabs button:hover:not(:disabled) { color: var(--bf-text) !important }
.bf-tabs button[aria-pressed=true] {
  color: var(--bf-text) !important; font-weight: 620;
  border-bottom-color: var(--bf-accent) !important;
}
.bf-tabs button[aria-pressed=true] .bf-badge { background: var(--bf-accent-soft); color: var(--bf-accent) }

/* ---- chips ------------------------------------------------------------- */

.bf-chip, .bf-badge {
  display: inline-flex; align-items: center; gap: 5px;
  border-radius: 999px; padding: 2px 9px;
  font-size: 11px; font-weight: 650; letter-spacing: .01em;
  background: var(--bf-surface-2); color: var(--bf-muted);
  white-space: nowrap;
}
.bf-handoff-head { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px }
.bf-handoff-head .bf-chip { width: auto; flex: none }
.bf-handoff-draft { display: grid; gap: 10px; margin-top: 10px }
.bf-chip[data-status=attention], .bf-chip[data-status=partial], .bf-chip[data-status=upstream_revised],
.bf-chip[data-status=needs_review], .bf-chip[data-status=unvalidated],
.bf-chip[data-status=needs_input], .bf-chip[data-status=ready_for_review], .bf-chip[data-status=waiting], .bf-chip[data-status=inferred],
.bf-chip[data-status=proposed], .bf-chip[data-status=draft], .bf-chip[data-status=notice_pending], .bf-chip[data-status=notice_failed] { color: var(--bf-warn); background: var(--bf-warn-bg) }
.bf-chip[data-status=validated], .bf-chip[data-status=ready],
.bf-chip[data-status=ok], .bf-chip[data-status=allowed_once],
.bf-chip[data-status=data_ready], .bf-chip[data-status=completed], .bf-chip[data-status=approved], .bf-chip[data-status=confirmed], .bf-chip[data-status=notice_sent] { color: var(--bf-ok); background: var(--bf-ok-bg) }
.bf-chip[data-status=rejected], .bf-chip[data-status=needs_configuration],
.bf-chip[data-status=submit_failed], .bf-chip[data-status=returned], .bf-chip[data-status=conflict], .bf-chip[data-status=missing], .bf-chip[data-status=notice_abandoned] { color: var(--bf-danger); background: var(--bf-danger-bg) }

/* ---- tables ------------------------------------------------------------ */

.bf-scroll { overflow: auto; max-height: 46vh; border: 1px solid var(--bf-line); border-radius: 10px }
.bf-panel table { border-collapse: separate; border-spacing: 0; font-size: 13px; min-width: 100% }
.bf-panel th, .bf-panel td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--bf-line);
  text-align: left; vertical-align: top;
}
/* Never wrap a header one character per line. Columns take the width they need and
   the container scrolls; squeezing 17 columns into one screen reads as damage. */
.bf-panel th { position: sticky; top: 0; z-index: 1; background: var(--bf-surface-2); white-space: nowrap; font-weight: 620; font-size: 12px; color: var(--bf-muted) }
.bf-panel th small { display: block; font-weight: 500; font-size: 10px; opacity: .8; text-transform: uppercase; letter-spacing: .04em }
.bf-panel td { max-width: 320px; min-width: 84px; overflow-wrap: anywhere }
.bf-panel td[data-numeric=true] { text-align: right; white-space: nowrap }
.bf-panel td[data-empty=true] { color: var(--bf-muted) }
.bf-panel tbody tr:last-child td { border-bottom: 0 }
.bf-panel tbody tr:hover td { background: var(--bf-surface-2) }
.bf-cellnote { display: block; font-size: 11px; color: var(--bf-muted); margin-top: 2px }
.bf-pager { display: flex; align-items: center; gap: 10px; margin: 12px 0 0 }
.bf-pager .bf-hint { margin-right: auto }

/* ---- empty states ------------------------------------------------------ */

.bf-empty {
  border: 1px dashed var(--bf-line-strong); border-radius: 10px;
  padding: 30px 24px; text-align: center; color: var(--bf-muted);
}
.bf-empty strong { display: block; color: var(--bf-text); font-size: 14px; margin-bottom: 4px }

/* ---- the orientation card on a blank session --------------------------- */

.bf-hero {
  border: 1px solid var(--bf-line); border-radius: 12px;
  background: var(--bf-surface); box-shadow: var(--bf-shadow);
  padding: 18px 20px; margin: 0 auto 12px;
  /* The input dock spans the whole conversation column; the composer card below it
     does not. Measured at 774px, so the card and the guidance above it line up
     instead of the guidance running 32px wider on each side. If the host ever
     narrows its composer this reads slightly wide, which is the benign direction. */
  width: 100%; max-width: 774px;
}
.bf-hero h3 { font-size: 15px; margin: 0 0 2px }
.bf-hero ol { margin: 14px 0 0; padding: 0; list-style: none; display: grid; gap: 10px; counter-reset: bf-flow }
.bf-hero li { position: relative; padding-left: 30px; font-size: 13px; line-height: 1.5 }
.bf-hero li::before {
  counter-increment: bf-flow; content: counter(bf-flow);
  position: absolute; left: 0; top: 1px;
  width: 20px; height: 20px; border-radius: 50%;
  background: var(--bf-accent-soft); color: var(--bf-accent);
  font-size: 11px; font-weight: 700; display: grid; place-items: center;
}
.bf-hero li b { font-weight: 620 }
.bf-hero li span { color: var(--bf-muted) }

/* ---- the decision card ------------------------------------------------- */

/* The approval takeover replaces the composer, so it is the only thing on screen
   at that moment. It gets the layout of a decision: what is being asked, the note
   the reviewer may leave, then the two answers with reject first. */
.bf-decision header, .bf-card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 8px }
.bf-decision .bf-callout { margin: 0 0 12px }
/* The structured decision summary: label column narrow, value column wraps. */
.bf-approval-detail { display: grid; grid-template-columns: minmax(90px, max-content) 1fr; gap: 4px 12px; margin: 8px 0 0; font-size: 13px }
.bf-approval-detail dt { color: var(--bf-muted) }
.bf-approval-detail dd { margin: 0; overflow-wrap: anywhere }
.bf-field { display: block; margin: 0 0 4px }
.bf-field > span:first-child { display: block; font-size: 12px; color: var(--bf-muted); margin-bottom: 5px }
.bf-field > .bf-hint { display: block; text-align: right; margin-top: 3px }
.bf-decision .bf-actions { justify-content: flex-end; margin-bottom: 0 }

/* ---- one check in the department report --------------------------------- */

.bf-check { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin: 10px 0 2px }
.bf-check-title { font-weight: 620; flex: 1; min-width: 120px }
.bf-check b { font-size: 18px; font-weight: 650; letter-spacing: -.01em }
.bf-check b small { font-size: 11px; font-weight: 500; color: var(--bf-muted); margin-left: 3px }

.bf-state-head { margin-bottom: 18px }
.bf-state-head h2 { margin-bottom: 2px }

/* ---- cards, report, drawer, state map ---------------------------------- */

.bf-card {
  padding: 14px 16px; border: 1px solid var(--bf-line); border-radius: var(--bf-radius);
  margin: 8px 0; font-size: 13px; overflow-wrap: anywhere; background: var(--bf-surface);
}
.bf-card strong { font-size: 14px; font-weight: 640 }
.bf-card pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 180px; overflow: auto; font-size: 12px; background: var(--bf-surface-2); border-radius: 7px; padding: 10px; margin: 8px 0 }
.bf-card textarea { display: block; width: 100%; box-sizing: border-box; min-height: 70px }
.bf-card a, .bf-state a { color: inherit; text-decoration: underline }

.bf-report-roles { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 330px), 1fr)); gap: 12px }
.bf-report-roles .bf-card { margin: 0 }
.bf-report summary { cursor: pointer; font-size: 12px; color: var(--bf-muted) }
.bf-report details { margin: 8px 0 }
.bf-report p { margin: 6px 0 }
.bf-attention { border-left: 3px solid var(--bf-warn); padding-left: 12px }

.bf-state {
  position: relative; z-index: 9; padding: 24px; overflow: auto; height: 100%;
  box-sizing: border-box; max-width: 1200px; width: 100%; min-width: 0; margin: auto; padding-bottom: 160px;
}
.bf-state nav { display: flex; gap: 8px; flex-wrap: wrap; margin: 15px 0 }
.bf-state-map { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 210px), 1fr)); gap: 14px; margin: 24px 0 }
.bf-state-map section { border: 1px solid var(--bf-line); border-radius: var(--bf-radius); padding: 14px; background: var(--bf-surface) }
.bf-state-map h3 { margin: 0 0 10px; font-size: 13px; color: var(--bf-muted) }
.bf-state-map button { display: block; width: 100%; text-align: left; margin: 6px 0; font-size: 13px }
.bf-state-map button[data-current=true] { box-shadow: inset 3px 0 var(--bf-accent); background: var(--bf-accent-soft) }
.bf-state-map button[aria-pressed=true] { outline: 2px solid var(--bf-accent) }

.bf-drawer {
  pointer-events: auto; position: fixed; right: 0; top: 0; bottom: 0;
  width: min(420px, 94vw); overflow: auto; background: var(--bf-surface);
  box-shadow: -6px 0 34px #0b162433; border-left: 1px solid var(--bf-line);
  padding: 22px; box-sizing: border-box;
}
.bf-drawer h2 { font-size: 17px; margin: 0 0 4px }
.bf-drawer label { display: block }
.bf-drawer input[type=month] { display: block; width: 100% ; box-sizing: border-box }

/* The one entry point into the product. It should not be the faintest control on
   the screen, which is what an outline button in the sidebar footer was — and what
   it briefly became again when this rule used tokens the sidebar had never been
   given, so every colour resolved to nothing. It carries its own token scope above. */
.bf-open { width: 100%; font-weight: 600; background: var(--bf-accent); border-color: var(--bf-accent); color: #fff }
.bf-open:hover { filter: brightness(1.07); background: var(--bf-accent) }

@media (max-width: 760px) {
  .bf-report-roles, .bf-state-map { grid-template-columns: 1fr }
  .bf-panel-body { padding: 16px }
  .bf-panel-head { padding: 14px 16px 12px }
}

/* ---- dark ---------------------------------------------------------------
   Redefined tokens only. Every colour above resolves through one of these, so
   the dark theme is a palette swap rather than a second stylesheet. */

body[data-ds-dark-theme] .bf-panel, body[data-ds-dark-theme] .bf-state,
body[data-ds-dark-theme] .bf-card, body[data-ds-dark-theme] .bf-drawer,
body[data-ds-dark-theme] .bf-hero, body[data-ds-dark-theme] .bf-open {
  --bf-surface: #161e28;
  --bf-surface-2: #1e2833;
  --bf-line: #2f3d4b;
  --bf-line-strong: #46586a;
  --bf-text: #e9f0f7;
  --bf-muted: #9fb1c3;
  --bf-accent: #5c9bff;
  --bf-accent-soft: #1b2b42;
  --bf-warn: #f2c879;
  --bf-warn-bg: #3b2f19;
  --bf-ok: #86ddaa;
  --bf-ok-bg: #17352a;
  --bf-danger: #ff9d95;
  --bf-danger-bg: #3a1f1c;
  --bf-shadow: 0 1px 2px #0006, 0 10px 30px #0007;
  color: var(--bf-text);
}
body[data-ds-dark-theme] .bf-primary, body[data-ds-dark-theme] .bf-open { color: #0b1420 !important }
body[data-ds-dark-theme] .bf-panel::backdrop { background: #04080d9e }

.bf-eyebrow { color: var(--bf-muted); font-size: 11px; letter-spacing: .09em; font-weight: 650; margin-bottom: 6px }
.bf-source-item { display: flex; flex-direction: column; gap: 5px; padding: 12px 0; border-bottom: 1px solid var(--bf-line); font-size: 13px }
.bf-source-item:last-child { border-bottom: 0 }
.bf-source-pending { color: var(--bf-muted); font-size: 11px }
.bf-notebook-note { background: var(--bf-accent-soft); border-radius: 12px; padding: 14px; margin: 16px 0; font-size: 13px }
.bf-notebook-empty { padding: 56px 8px; text-align: center; color: var(--bf-muted) }
.bf-quotation-paper { border: 1px solid var(--bf-line); padding: 24px; margin: 24px 0; border-radius: 4px; box-shadow: 0 3px 12px #0f172a08 }
.bf-quotation-paper header { border-bottom: 2px solid var(--bf-text); padding-bottom: 16px }
.bf-quotation-paper dl { margin: 16px 0 }
.bf-quotation-paper dl > div { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; border-bottom: 1px solid var(--bf-line); padding: 12px 0; font-size: 13px }
.bf-quotation-paper dd { margin: 0; color: var(--bf-muted); font-size: 12px }
.bf-formulas { margin-top: 16px; font-size: 12px }
.bf-formulas summary { cursor: pointer; color: var(--bf-accent) }
.bf-formulas code { white-space: normal; overflow-wrap: anywhere }
.bf-state button:disabled { opacity: .45; cursor: default }
/* Evidence grades (E13-UC06): the label always carries the grade; colour only supports it. */
.bf-grade { display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: .02em; border-radius: 5px; padding: 1px 5px; margin-left: 6px; vertical-align: middle; border: 1px solid currentColor; cursor: help }
.bf-grade[data-grade=G1] { color: var(--bf-ok) }
.bf-grade[data-grade=G2] { color: var(--bf-accent) }
.bf-grade[data-grade=G3] { color: var(--bf-warn); background: var(--bf-warn-bg) }
.bf-grade[data-grade=G4] { color: var(--bf-muted) }
.bf-grade[data-grade=missing] { color: var(--bf-danger); background: var(--bf-danger-bg) }
/* Period-on-period change (E13-UC02): direction is never colour alone; the sign carries it. */
.bf-change { margin-left: 8px; font-size: 11px; font-weight: 600; white-space: nowrap }
.bf-disposition { font-size: .85em; border: 1px solid currentColor; border-radius: .6em; padding: 0 .4em; margin-left: .4em; }
.bf-disposition[data-closed=true] { opacity: .65; text-decoration: line-through; }
.bf-chart-card { margin: 12px 0; }
.bf-chart { width: 100%; max-width: 560px; height: auto; }
.bf-chart-line { fill: none; stroke: currentColor; stroke-width: 2; }
.bf-chart-threshold { stroke: currentColor; stroke-dasharray: 4 4; opacity: .6; }
.bf-chart-label { font-size: 10px; fill: currentColor; opacity: .75; }
.bf-chart-point { fill: currentColor; cursor: pointer; }
.bf-chart-point[data-breach=true] { stroke: currentColor; stroke-width: 3; fill: var(--bf-surface, #fff); }
.bf-chart-bars { display: grid; gap: 4px; max-width: 560px; }
.bf-chart-bar { display: grid; grid-template-columns: 10rem 1fr 7rem; gap: 8px; align-items: center; text-align: left; background: none; border: 0; padding: 2px 0; cursor: pointer; }
.bf-chart-bar-track { background: color-mix(in srgb, currentColor 12%, transparent); height: 12px; border-radius: 6px; }
.bf-chart-bar-track > span { display: block; height: 100%; border-radius: 6px; background: currentColor; }
.bf-chart-bar-track > span[data-negative=true] { background: repeating-linear-gradient(45deg, currentColor 0 4px, transparent 4px 8px); }
.bf-chart-bar[data-breach=true] .bf-chart-bar-label { font-weight: 700; }
.bf-chart-bar-value { text-align: right; font-variant-numeric: tabular-nums; }
.bf-chart-table { margin-top: 6px; }
.bf-inbox ul { list-style: none; margin: 8px 0; padding: 0; display: grid; gap: 8px; }
.bf-inbox li { border-left: 3px solid var(--bf-warn, #8a6100); padding: 4px 0 4px 10px; }
.bf-inbox label { display: block; margin: 6px 0; }
.bf-checklist ol { list-style: none; margin: 8px 0; padding: 0; display: grid; gap: 8px; }
.bf-checklist li { border-left: 3px solid currentColor; padding: 4px 0 4px 10px; }
.bf-checklist li[data-state=done] { color: var(--bf-ok, #1c6b3a); }
.bf-checklist li[data-state=open] { color: var(--bf-warn, #8a6100); }
.bf-checklist li[data-state=blocked] { color: var(--bf-danger, #a12b2b); }
.bf-checklist li[data-state=unknown] { color: var(--bf-muted, #6b6b6b); }
.bf-checklist li b, .bf-checklist li .bf-hint, .bf-checklist li button { color: initial; }
.bf-step-state { font-size: .85em; border: 1px solid currentColor; border-radius: .6em; padding: 0 .4em; margin-right: .4em; }
.bf-convention { font-size: .85em; padding: 0 .4em; border-radius: .6em; border: 1px solid currentColor; }
.bf-convention[data-state=unconfirmed] { color: var(--bf-warn, #8a6100); }
.bf-convention[data-state=confirmed] { color: var(--bf-ok, #1c6b3a); }
.bf-convention[data-state=replacement_requested] { color: var(--bf-info, #1f4f8f); }
.bf-change[data-state=up] { color: var(--bf-ok) }
.bf-change[data-state=down] { color: var(--bf-warn) }
.bf-change[data-state=flat], .bf-change[data-state=none] { color: var(--bf-muted); font-weight: 500 }
/* One-page monthly brief (E13-UC01). */
.bf-brief h4 { margin: 18px 0 8px; font-size: 13px }
.bf-brief-headline { font-size: 14px; margin: 8px 0 }
.bf-brief-headline strong { font-size: 20px; font-weight: 650 }
.bf-brief-metrics { display: grid; gap: 8px; margin: 0 }
.bf-brief-metrics > div { border: 1px solid var(--bf-line); border-radius: 8px; padding: 8px 10px }
.bf-brief-metrics dt { font-size: 12px; color: var(--bf-muted) }
.bf-brief-metrics dd { margin: 2px 0 0 }
.bf-brief-metrics dd b { font-size: 16px; font-weight: 650 }
.bf-brief-metrics dd small { display: block; color: var(--bf-muted); font-size: 11px; margin-top: 2px; overflow-wrap: anywhere }
.bf-brief-attention { padding-left: 18px; margin: 0 }
.bf-brief-attention li { margin: 0 0 12px }
.bf-brief-attention p { margin: 2px 0 }
.bf-brief-open { padding-left: 18px; margin: 0 }
.bf-brief-open button { margin-left: 8px; font-size: 11px; padding: 2px 8px }
.bf-document button:focus-visible, .bf-document summary:focus-visible { outline: 2px solid var(--bf-accent); outline-offset: 3px }

.bf-discovery form { display: grid; gap: 12px; margin: 16px 0 }
.bf-discovery label { display: grid; gap: 5px; font-size: 13px }
.bf-discovery input, .bf-discovery select, .bf-discovery textarea { width: 100%; min-width: 0; box-sizing: border-box }
.bf-discovery textarea { min-height: 160px; font-family: monospace }
.bf-discovery article { padding: 12px 0; border-bottom: 1px solid var(--bf-border) }
.bf-discovery article strong { overflow-wrap: anywhere }
.bf-discovery pre { font-size: 12px; max-height: 360px; overflow: auto }

/* ---- destinations: tasks, data, records -------------------------------- */

.bf-studio-group {
  font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
  color: var(--bf-muted); margin: 10px 4px 2px;
}
.bf-studio-tools .bf-badge { margin-left: auto }

.bf-studio-facts { margin-top: 14px }
.bf-facts { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 8px 0 }
.bf-facts dt { font-size: 12px; color: var(--bf-muted) }
.bf-facts dd { margin: 0; font-size: 13px; font-weight: 600 }

.bf-tasks-split { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start }
.bf-tasks-split > * { flex: 1 1 340px; min-width: 0 }
.bf-checklist li[data-focused=true] { background: var(--bf-accent-soft); border-radius: 8px }
.bf-tasks-workflow { margin-top: 14px }
.bf-tasks-workflow > summary { font-size: 13px; color: var(--bf-muted); cursor: pointer }

.bf-data-steps {
  list-style: none; margin: 10px 0; padding: 0;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px;
}
.bf-data-steps li {
  display: flex; gap: 8px; align-items: center;
  border: 1px solid var(--bf-line); border-radius: var(--bf-radius); padding: 8px 10px;
}
.bf-data-steps li > span:first-child {
  flex: 0 0 auto; width: 22px; height: 22px; border-radius: 999px;
  background: var(--bf-accent-soft); color: var(--bf-accent);
  display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700;
}
.bf-data-steps strong { display: block; font-size: 13px }
.bf-data-steps small { display: block; font-size: 11px; color: var(--bf-muted); line-height: 1.5 }

.bf-data-split { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start }
.bf-data-files { flex: 3 1 380px; min-width: 0 }
.bf-data-quality { flex: 1 1 260px; min-width: 0 }
.bf-data-files { display: grid; gap: 10px; align-content: start }
.bf-data-row { border: 1px solid var(--bf-line); border-radius: var(--bf-radius); padding: 10px 12px }
.bf-data-row[data-state=missing] { border-style: dashed }
.bf-data-row-head { display: flex; gap: 10px; align-items: center; flex-wrap: wrap }
.bf-data-row-head > strong { min-width: 5em }
.bf-data-row-head .bf-hint { flex: 1 1 12em; min-width: 0 }
.bf-data-row .bf-resupply { margin-top: 8px }
.bf-data-row .bf-template-download { display: inline-flex; align-items: center; gap: 8px }

.bf-data-quality ul { list-style: none; margin: 8px 0; padding: 0; display: grid; gap: 6px }
.bf-data-quality li > button {
  width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 10px;
}

.bf-records-list { list-style: none; margin: 6px 0 14px; padding: 0; display: grid; gap: 8px }
.bf-records-list li {
  display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap;
  border-left: 3px solid var(--bf-line-strong); padding-left: 10px;
}
.bf-records h4 { font-size: 13px; margin: 14px 0 4px }

.bf-brief-layer {
  font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--bf-muted);
  margin: 18px 0 4px; padding-top: 10px; border-top: 1px solid var(--bf-line);
}
.bf-brief-layer[data-layer="1"] { margin-top: 6px; border-top: 0; padding-top: 0 }
.bf-brief-fold > summary { font-size: 14px; font-weight: 640; cursor: pointer; padding: 4px 0 }

/* ---- decision journal and acceptance report ---------------------------- */

.bf-journal { margin-top: 18px }
.bf-journal-summary { grid-template-columns: auto 1fr auto 1fr }
.bf-journal-reasons { list-style: none; margin: 6px 0 0; padding: 0; display: grid; gap: 4px }
.bf-journal-reasons li { display: flex; gap: 10px; align-items: baseline; font-size: 12px }
.bf-journal-reasons li > span:first-child { flex: 1 1 auto; min-width: 0 }

.bf-journal-list { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 2px }
.bf-journal-list li {
  display: grid; align-items: baseline; gap: 8px;
  grid-template-columns: 4.5rem 4.5rem minmax(8rem, 1fr) 4rem;
  padding: 5px 6px; border-radius: 6px; font-size: 12px;
}
.bf-journal-list li:nth-child(odd) { background: var(--bf-surface-2) }
/* A refusal is the interesting line, so it gets the whole row and the accent. */
.bf-journal-list li[data-outcome=refused] { grid-template-columns: 4.5rem 4.5rem minmax(8rem, 1fr) 4rem; box-shadow: inset 2px 0 var(--bf-danger) }
.bf-journal-time, .bf-journal-ms, .bf-journal-trace { color: var(--bf-muted); font-variant-numeric: tabular-nums }
.bf-journal-ms { text-align: right }
.bf-journal-outcome { font-weight: 640 }
.bf-journal-outcome[data-outcome=refused] { color: var(--bf-danger) }
.bf-journal-outcome[data-outcome=wrote] { color: var(--bf-warn) }
.bf-journal-outcome[data-outcome=served] { color: var(--bf-muted) }
.bf-journal-surface { overflow-wrap: anywhere }
.bf-journal-reason { grid-column: 2 / -1; color: var(--bf-text); line-height: 1.5 }
.bf-journal-trace { grid-column: 1 / -1; font-size: 11px; opacity: .55 }

.bf-eval { margin-top: 18px }

/* ---- agent runs -------------------------------------------------------- */

.bf-runs { margin-top: 18px }
.bf-run-list { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 8px }
.bf-run-list > li { border: 1px solid var(--bf-line); border-radius: var(--bf-radius); overflow: hidden }
.bf-run-head {
  width: 100%; display: grid; gap: 10px; align-items: baseline; text-align: left;
  grid-template-columns: 4.5rem minmax(0, 1fr) minmax(0, 12rem);
  background: none; border: 0; padding: 10px 12px; cursor: pointer; font-size: 13px;
}
.bf-run-head:hover { background: var(--bf-surface-2) }
.bf-run-when { color: var(--bf-muted); font-variant-numeric: tabular-nums }
.bf-run-tools { overflow-wrap: anywhere }
.bf-run-detail { padding: 4px 12px 12px; border-top: 1px solid var(--bf-line) }

.bf-run-lanes { display: grid; gap: 6px; margin: 10px 0 12px }
.bf-run-lane { display: grid; grid-template-columns: 8rem minmax(0, 1fr); gap: 10px; align-items: center }
.bf-run-lane-name { font-size: 12px; color: var(--bf-muted); overflow-wrap: anywhere }
.bf-run-lane-track {
  position: relative; display: block; height: 26px; border-radius: 6px;
  background: var(--bf-surface-2); box-shadow: inset 0 0 0 1px var(--bf-line);
}
.bf-run-mark {
  position: absolute; top: 3px; bottom: 3px; min-width: 14px; padding: 0 6px;
  border: 1px solid var(--bf-accent); border-radius: 5px; background: var(--bf-accent-soft);
  color: var(--bf-text); font: inherit; font-size: 11px; line-height: 18px; cursor: help;
  overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
}
/* A refusal is marked by shape as well as colour: dashed border, and a ✕ in the label. */
.bf-run-mark[data-outcome=refused] { border-style: dashed; border-color: var(--bf-danger); background: var(--bf-danger-bg) }
.bf-run-mark[data-outcome=wrote] { border-color: var(--bf-warn); background: var(--bf-warn-bg) }
.bf-run-mark-label { pointer-events: none }

.bf-run-steps { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px }
.bf-run-steps > li {
  display: grid; gap: 8px; align-items: baseline; font-size: 12px; padding: 4px 6px; border-radius: 6px;
  grid-template-columns: 7rem minmax(6rem, 1fr) 4rem 3.5rem;
}
.bf-run-steps > li:nth-child(odd) { background: var(--bf-surface-2) }
.bf-run-steps > li[data-outcome=refused] { box-shadow: inset 2px 0 var(--bf-danger) }
.bf-run-step-reason { grid-column: 2 / -1; color: var(--bf-text); line-height: 1.5 }
`
