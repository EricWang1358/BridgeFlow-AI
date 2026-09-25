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
  --bf-surface-2: #f5f7fa;
  --bf-line: #e2e7ee;
  --bf-line-strong: #cbd3dd;
  --bf-text: var(--foreground, #101b27);
  --bf-muted: #5b6b7c;
  --bf-accent: #2f6bd8;
  --bf-chart-mark: #2f6bd8;
  --bf-chart-critical: #9d271c;
  --bf-accent-soft: #e8f0fd;
  --bf-warn: #8a4b06;
  --bf-warn-bg: #fdf3e0;
  --bf-ok: #10643d;
  --bf-ok-bg: #e6f5ec;
  --bf-danger: #9d271c;
  --bf-danger-bg: #fdeceb;
  /* One sans family everywhere. The serif headings asked for fonts that are never
     loaded, so every system substituted its own serif and the product looked
     different on each machine. System faces render crisply wherever it runs. */
  --bf-sans: Inter, system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', 'PingFang SC',
    'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans SC', 'Noto Sans CJK SC', sans-serif;
  --bf-radius: 10px;
  --bf-shadow-sm: 0 1px 2px #0f172a0f;
  --bf-shadow: 0 1px 2px #0f172a0d, 0 6px 20px #0f172a12;
  --bf-shadow-lg: 0 2px 6px #0f172a14, 0 24px 60px #0f172a2e;
  color: var(--bf-text);
  font-family: var(--bf-sans);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  font-variant-numeric: tabular-nums;
}

/* ---- typography -------------------------------------------------------- */

.bf-icon { display: inline-block; flex: none; vertical-align: -.2em }

.bf-panel h2, .bf-state h2 { font-size: 18px; font-weight: 650; line-height: 1.3; margin: 0; letter-spacing: -.015em }
.bf-brief-headline, .bf-card-head h3 { letter-spacing: -.01em }
.bf-panel h3, .bf-state h3 { font-size: 14px; font-weight: 620; margin: 0 0 6px; letter-spacing: -.005em }
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
  border-radius: 16px;
  box-shadow: var(--bf-shadow-lg);
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
.bf-panel::backdrop { background: #0b162466; backdrop-filter: blur(3px) }
.bf-panel:not([open]) { display: none }

.bf-panel-head {
  display: flex; align-items: flex-start; gap: 16px;
  padding: 18px 24px 16px;
  border-bottom: 1px solid var(--bf-line);
  background: var(--bf-surface);
}
.bf-panel-head > div:first-child, .bf-panel-head > h2:first-child { flex: 1; min-width: 0 }
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
  font-size: 13px;
  font-weight: 520;
  line-height: 18px;
  border: 1px solid var(--bf-line-strong);
  border-radius: 8px;
  padding: 6px 12px;
  background: var(--bf-surface);
  box-shadow: var(--bf-shadow-sm);
  color: inherit;
  cursor: pointer;
  transition: background .12s, border-color .12s, box-shadow .12s;
}
.bf-panel button:hover:not(:disabled), .bf-card button:hover:not(:disabled),
.bf-state button:hover:not(:disabled), .bf-open:hover { background: var(--bf-surface-2); border-color: color-mix(in srgb, var(--bf-line-strong) 70%, var(--bf-text)) }
.bf-panel button:disabled, .bf-card button:disabled, .bf-drawer button:disabled { opacity: .45; cursor: default }

/* One primary per surface. It is the action that moves the work forward. */
.bf-primary {
  background: var(--bf-accent) !important;
  border-color: var(--bf-accent) !important;
  color: #fff !important;
  font-weight: 600;
  box-shadow: 0 1px 2px #1d4ed833, inset 0 1px 0 #ffffff26 !important;
}
.bf-primary:hover:not(:disabled) { filter: brightness(1.07) }
.bf-quiet { border-color: transparent !important; background: transparent !important; box-shadow: none !important; color: var(--bf-muted) !important; padding: 6px 8px !important }
.bf-quiet:hover:not(:disabled) { color: var(--bf-text) !important }
.bf-danger-btn { border-color: var(--bf-danger) !important; color: var(--bf-danger) !important }

.bf-actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 14px 0 }

/* ---- forms ------------------------------------------------------------- */

.bf-panel input, .bf-panel select, .bf-state input, .bf-drawer input, .bf-card textarea {
  font: inherit;
  font-size: 13px;
  border: 1px solid var(--bf-line-strong);
  border-radius: 8px;
  padding: 7px 10px;
  color: inherit;
  background: var(--bf-surface);
  max-width: 100%;
}
.bf-panel input:focus-visible, .bf-panel select:focus-visible, .bf-card textarea:focus-visible { outline: 0; border-color: var(--bf-accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--bf-accent) 22%, transparent) }
.bf-panel button:focus-visible, .bf-card button:focus-visible, .bf-state button:focus-visible { outline: 2px solid color-mix(in srgb, var(--bf-accent) 70%, transparent); outline-offset: 2px }

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

/* A tinted panel with a hairline in its own tone: the colour carries the state,
   so no heavy side bar is needed to announce it. */
.bf-callout {
  --bf-tone: var(--bf-muted);
  border: 1px solid color-mix(in srgb, var(--bf-tone) 20%, transparent);
  border-radius: 10px;
  padding: 12px 14px;
  margin: 12px 0;
  background: var(--bf-surface-2);
}
.bf-callout h3 { font-size: 13px; margin: 0 0 4px }
.bf-callout p { margin: 0 }
.bf-callout[data-tone=warn] { --bf-tone: var(--bf-warn); background: var(--bf-warn-bg); color: var(--bf-warn) }
.bf-callout[data-tone=danger] { --bf-tone: var(--bf-danger); background: var(--bf-danger-bg); color: var(--bf-danger) }
.bf-callout[data-tone=ok] { --bf-tone: var(--bf-ok); background: var(--bf-ok-bg); color: var(--bf-ok) }
.bf-callout[data-tone=info] { --bf-tone: var(--bf-accent); background: var(--bf-accent-soft) }
.bf-error { color: var(--bf-danger) }

/* ---- status band ------------------------------------------------------- */

.bf-band { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin: 0 0 2px }
.bf-band .bf-period { font-size: 22px; font-weight: 660; letter-spacing: -.02em }
/* The status's debt to its reader: the sentence under the chip and its one action (#244). */
.bf-next { margin: 8px 0 0; padding: 10px 12px; border: 1px solid color-mix(in srgb, var(--bf-accent) 20%, transparent); border-radius: 10px; background: var(--bf-accent-soft) }
.bf-next .bf-actions { margin: 6px 0 0 }
.bf-stats { display: flex; gap: 20px; flex-wrap: wrap; margin: 14px 0 }
.bf-stat { min-width: 74px }
.bf-stat b { display: block; font-size: 22px; font-weight: 650; line-height: 1.2; letter-spacing: -.02em }
.bf-stat span { font-size: 12px; color: var(--bf-muted) }

/* ---- tabs -------------------------------------------------------------- */

.bf-tabs { display: flex; gap: 2px; flex-wrap: wrap; margin: 18px 0 0; border-bottom: 1px solid var(--bf-line); padding-bottom: 0 }
.bf-tabs button {
  border: 0 !important; border-radius: 8px 8px 0 0 !important;
  background: transparent !important; color: var(--bf-muted) !important;
  padding: 9px 12px !important; margin-bottom: -1px;
  border-bottom: 2px solid transparent !important;
  box-shadow: none !important; font-size: 13px !important;
}
.bf-tabs button:hover:not(:disabled) { color: var(--bf-text) !important }
.bf-tabs button[aria-pressed=true] {
  color: var(--bf-text) !important; font-weight: 600;
  border-bottom-color: var(--bf-accent) !important;
}
.bf-tabs button[aria-pressed=true] .bf-badge { background: var(--bf-accent-soft); color: var(--bf-accent) }

/* ---- chips ------------------------------------------------------------- */

.bf-chip, .bf-badge {
  display: inline-flex; align-items: center; gap: 5px;
  border-radius: 999px; padding: 1px 8px;
  font-size: 11px; line-height: 18px; font-weight: 600; letter-spacing: .01em;
  background: var(--bf-surface-2); color: var(--bf-muted);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, currentColor 16%, transparent);
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
/* Inside a scroller, columns take their content's width (capped by the cell's max-width)
   instead of being squeezed to fit: a squeezed text column wrapped a roll-up note into a
   270px-tall row and pushed every other cell of that row apart. */
.bf-scroll > table { width: max-content }
/* Content-heavy windows keep one height: rows arriving must not resize the window around them. */
.bf-panel.bf-tables-dialog[open], .bf-panel.bf-expanded-preview[open] { height: min(880px, 90vh) }
.bf-scroll[data-loading=true] { opacity: .55; transition: opacity .15s }
.bf-panel th, .bf-panel td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--bf-line);
  text-align: left; vertical-align: top;
}
/* Never wrap a header one character per line. Columns take the width they need and
   the container scrolls; squeezing 17 columns into one screen reads as damage. */
.bf-panel th { position: sticky; top: 0; z-index: 1; background: var(--bf-surface-2); white-space: nowrap; font-weight: 600; font-size: 12px; color: var(--bf-muted); box-shadow: inset 0 -1px 0 var(--bf-line) }
.bf-panel th small { display: block; font-weight: 500; font-size: 10px; opacity: .8; text-transform: uppercase; letter-spacing: .04em }
/* The business's own column name under its English display name (English interface only). */
th small.bf-original { display: block; font-weight: 500; font-size: 10px; color: var(--bf-muted); opacity: 1; text-transform: none; letter-spacing: 0 }
/* Studio tables scroll sideways like the panel's; a header never wraps one character per line. */
.bf-state .bf-scroll table { border-collapse: separate; border-spacing: 0; font-size: 12px }
.bf-state .bf-scroll th, .bf-state .bf-scroll td { padding: 7px 10px; border-bottom: 1px solid var(--bf-line); text-align: left; vertical-align: top }
.bf-state .bf-scroll th { white-space: nowrap; vertical-align: bottom; position: sticky; top: 0; z-index: 1; background: var(--bf-surface-2); font-weight: 600; color: var(--bf-muted) }
.bf-state .bf-scroll td { max-width: 260px; overflow-wrap: anywhere }
.bf-state .bf-scroll td[data-numeric=true] { text-align: right; white-space: nowrap }
.bf-state .bf-scroll tbody tr:last-child td { border-bottom: 0 }
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
  padding: 14px 16px; border: 1px solid var(--bf-line); border-radius: 12px;
  margin: 8px 0; font-size: 13px; overflow-wrap: anywhere; background: var(--bf-surface);
  box-shadow: var(--bf-shadow-sm);
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
  --bf-chart-mark: #4a86e8;
  --bf-chart-critical: #e0645a;
  --bf-accent-soft: #1b2b42;
  --bf-warn: #f2c879;
  --bf-warn-bg: #3b2f19;
  --bf-ok: #86ddaa;
  --bf-ok-bg: #17352a;
  --bf-danger: #ff9d95;
  --bf-danger-bg: #3a1f1c;
  --bf-shadow-sm: 0 1px 2px #0005;
  --bf-shadow: 0 1px 2px #0006, 0 10px 30px #0007;
  --bf-shadow-lg: 0 2px 6px #0007, 0 24px 60px #000a;
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
.bf-inbox ul { list-style: none; margin: 10px 0; padding: 0; display: grid; gap: 10px; }
.bf-inbox li { border-left: 3px solid var(--bf-warn, #8a6100); padding: 6px 0 6px 12px; line-height: 1.55; }
.bf-inbox label { display: block; margin: 6px 0; }
.bf-checklist ol { list-style: none; margin: 10px 0; padding: 0; display: grid; gap: 10px; }
.bf-checklist li { border-left: 3px solid currentColor; padding: 6px 0 6px 12px; line-height: 1.55; }
.bf-checklist li[data-state=done] { color: var(--bf-ok, #1c6b3a); }
.bf-checklist li[data-state=open] { color: var(--bf-warn, #8a6100); }
.bf-checklist li[data-state=blocked] { color: var(--bf-danger, #a12b2b); }
.bf-checklist li[data-state=unknown] { color: var(--bf-muted, #6b6b6b); }
.bf-checklist li b, .bf-checklist li button { color: var(--bf-text); }
.bf-checklist li .bf-hint { color: var(--bf-muted); }
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
.bf-facts dt { font-size: 12px; color: var(--bf-muted); white-space: nowrap }
.bf-facts dd { margin: 0; font-size: 13px; font-weight: 600; min-width: 0; overflow-wrap: anywhere }
.bf-facts dd code { white-space: normal; overflow-wrap: anywhere; font-weight: 400 }

.bf-tasks-split { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start }
.bf-tasks-split > * { flex: 1 1 340px; min-width: 0 }
.bf-demo-guide button { margin-top: 10px }
.bf-checklist li[data-focused=true] { background: var(--bf-accent-soft); border-radius: 8px }
.bf-tasks-workflow { margin-top: 14px }
.bf-tasks-workflow > summary { font-size: 13px; color: var(--bf-muted); cursor: pointer }

.bf-data-steps {
  list-style: none; margin: 10px 0; padding: 0;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(136px, 1fr)); gap: 8px;
}
.bf-data-steps li {
  display: flex; gap: 8px; align-items: flex-start;
  border: 1px solid var(--bf-line); border-radius: var(--bf-radius); padding: 9px 11px;
  background: color-mix(in srgb, var(--bf-text) 3%, transparent);
}
.bf-data-steps li > span:first-child {
  flex: 0 0 auto; width: 20px; height: 20px; border-radius: 999px; margin-top: 1px;
  background: color-mix(in srgb, var(--bf-accent) 18%, transparent); color: var(--bf-text);
  display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700;
}
.bf-data-steps strong { display: block; font-size: 13px; line-height: 1.35 }
.bf-data-steps small { display: block; font-size: 11px; color: var(--bf-muted); line-height: 1.5 }

.bf-data-split { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start }
.bf-data-files { flex: 3 1 380px; min-width: 0 }
.bf-data-quality { flex: 1 1 260px; min-width: 0 }
.bf-data-files { display: grid; gap: 10px; align-content: start }
.bf-data-row { border: 1px solid var(--bf-line); border-radius: var(--bf-radius); padding: 11px 12px }
.bf-data-row + .bf-data-row { margin-top: 0 }
.bf-data-row[data-state=missing] { border-style: dashed }
.bf-data-row-head { display: flex; gap: 6px 10px; align-items: baseline; flex-wrap: wrap }
.bf-data-row-head > strong { flex: 0 0 auto; font-size: 13px }
.bf-data-row-head .bf-hint { flex: 1 1 12em; min-width: 0; font-size: 11.5px }
.bf-data-row-head .bf-chip { order: 2; margin-left: auto }
/* The row's actions sit on their own line when the meta is long, instead of squeezing the
   filename into two characters. */
.bf-data-row-head .bf-actions { order: 3; flex: 1 1 100%; margin: 4px 0 0; gap: 6px }
.bf-data-row-head .bf-actions button { font-size: 12px; padding: 5px 10px }
.bf-data-row .bf-resupply { margin-top: 8px; border-top: 1px dashed var(--bf-line); padding-top: 8px }
.bf-data-row .bf-resupply > summary { font-size: 12px; color: var(--bf-muted); cursor: pointer; list-style: none }
.bf-data-row .bf-resupply > summary::-webkit-details-marker { display: none }
.bf-data-row .bf-resupply > summary::before { content: '＋ '; opacity: .7 }
.bf-data-row .bf-resupply[open] > summary::before { content: '－ ' }
.bf-data-row .bf-template-download { display: inline-flex; align-items: center; gap: 8px }

.bf-data-quality ul { list-style: none; margin: 8px 0; padding: 0; display: grid; gap: 6px }
.bf-data-quality { border: 1px solid var(--bf-line); border-radius: var(--bf-radius); padding: 12px 14px }
.bf-data-quality h4 { margin: 0 0 4px; font-size: 13px }
.bf-data-quality li > button {
  width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 10px;
  background: transparent; box-shadow: inset 0 0 0 1px var(--bf-line); font-size: 12.5px;
}
.bf-data-quality li > button:hover { background: color-mix(in srgb, var(--bf-text) 6%, transparent) }
/* A zero is not news: the rows that still hold something are the ones that should catch the eye. */
.bf-data-quality li > button .bf-badge { opacity: .45 }
.bf-data-quality li > button .bf-badge[data-open=true] { opacity: 1; background: var(--bf-danger-bg); color: var(--bf-danger) }

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
.bf-journal-summary { grid-template-columns: auto minmax(2rem, 1fr) }
.bf-journal-reasons { list-style: none; margin: 6px 0 0; padding: 0; display: grid; gap: 4px }
.bf-journal-reasons li { display: flex; gap: 10px; align-items: baseline; font-size: 12px }
.bf-journal-reasons li > span:first-child { flex: 1 1 auto; min-width: 0 }

.bf-journal-list { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 2px }
.bf-journal-list li {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 8px;
  padding: 5px 6px; border-radius: 6px; font-size: 12px;
}
.bf-journal-surface { flex: 1 1 9rem; min-width: 0 }
.bf-journal-list li:nth-child(odd) { background: var(--bf-surface-2) }
/* A refusal is the interesting line, so it gets the whole row and the accent. */
.bf-journal-list li[data-outcome=refused] { box-shadow: inset 2px 0 var(--bf-danger) }
.bf-journal-time, .bf-journal-ms, .bf-journal-trace { color: var(--bf-muted); font-variant-numeric: tabular-nums }
.bf-journal-ms { text-align: right }
.bf-journal-outcome { font-weight: 640 }
.bf-journal-outcome[data-outcome=refused] { color: var(--bf-danger) }
.bf-journal-outcome[data-outcome=wrote] { color: var(--bf-warn) }
.bf-journal-outcome[data-outcome=served] { color: var(--bf-muted) }
.bf-journal-surface { overflow-wrap: anywhere }
.bf-journal-reason { flex: 1 1 100%; color: var(--bf-text); line-height: 1.5 }
.bf-journal-trace { flex: 1 1 100%; font-size: 11px; opacity: .55 }

.bf-eval { margin-top: 18px }

/* ---- agent runs -------------------------------------------------------- */

.bf-runs { margin-top: 18px }
.bf-run-list { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 8px }
.bf-run-list > li { border: 1px solid var(--bf-line); border-radius: var(--bf-radius); overflow: hidden }
.bf-run-head {
  width: 100%; display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; text-align: left;
  background: none; border: 0; padding: 10px 12px; cursor: pointer; font-size: 13px;
}
.bf-run-summary { flex: 1 1 12rem; min-width: 0 }
.bf-run-tools { flex: 1 1 100%; }
.bf-run-head:hover { background: var(--bf-surface-2) }
.bf-run-when { color: var(--bf-muted); font-variant-numeric: tabular-nums }
.bf-run-tools { overflow-wrap: anywhere }
.bf-run-detail { padding: 4px 12px 12px; border-top: 1px solid var(--bf-line) }

/* The lanes need room to stay readable; in a narrow pane they scroll rather than shrink
   the marks into unlabelled slivers. */
.bf-run-lanes { display: grid; gap: 6px; margin: 10px 0 12px; overflow-x: auto; padding-bottom: 4px }
.bf-run-lane { min-width: 460px }
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
  display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: baseline; font-size: 12px;
  padding: 5px 6px; border-radius: 6px;
}
.bf-run-steps > li > span:nth-child(2) { flex: 1 1 8rem; min-width: 0; font-weight: 600 }
.bf-run-steps > li > span:nth-child(3), .bf-run-steps > li > span:nth-child(4) { color: var(--bf-muted) }
.bf-run-steps > li:nth-child(odd) { background: var(--bf-surface-2) }
.bf-run-steps > li[data-outcome=refused] { box-shadow: inset 2px 0 var(--bf-danger) }
.bf-run-step-reason { flex: 1 1 100%; color: var(--bf-text); line-height: 1.5 }

/* Business state's "what to do now": the month's five stages, then the clicks for this one. */
.bf-state-guide { border: 1px solid color-mix(in srgb, var(--bf-accent) 22%, transparent); border-radius: 12px; background: var(--bf-accent-soft); padding: 12px 14px; margin: 0 0 14px }
.bf-state-guide h3 { margin: 10px 0 4px; font-size: 14px }
.bf-stage-strip { list-style: none; display: flex; flex-wrap: wrap; gap: 4px; margin: 0; padding: 0; font-size: 11px; font-weight: 600 }
.bf-stage-strip li { padding: 3px 9px; border-radius: 999px; color: var(--bf-muted); background: var(--bf-surface) }
.bf-stage-strip li[data-state=done] { color: var(--bf-ok) }
.bf-stage-strip li[data-state=done]::before { content: '✓ ' }
.bf-stage-strip li[data-state=current] { color: #fff; background: var(--bf-accent) }

/* Company-wide pages say so: they are not part of the open notebook. */
.bf-shared { display: inline-flex; white-space: normal; line-height: 1.45; padding: 4px 10px; margin: 4px 0 10px; color: var(--bf-accent); background: var(--bf-accent-soft) }

/* How an open item gets settled, under its detail. */
.bf-settle { margin: 6px 0 0; font-size: 12px; line-height: 1.55; color: var(--bf-text) }
.bf-settle > b { font-weight: 600; color: var(--bf-muted) }

/* The captain's "where is it" answer: numbered clicks. */
.bf-guide-steps { margin: 6px 0 0; padding-left: 20px; line-height: 1.6 }
.bf-guide-steps > li + li { margin-top: 2px }

/* ---- clarity pass: explanations, logic chains, evidence --------------------- */

/* "How this works": the reasoning behind a page, one click from its instruction. */
.bf-explain { margin: 6px 0 16px; font-size: 12px }
.bf-explain > summary { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; color: var(--bf-accent); list-style: none; font-weight: 560 }
.bf-explain > summary::-webkit-details-marker { display: none }
.bf-explain > summary::before { content: 'i'; display: grid; place-items: center; width: 15px; height: 15px; border-radius: 50%; border: 1.5px solid currentColor; font: 700 10px/1 var(--bf-sans) }
.bf-explain > ul { margin: 8px 0 0; padding: 10px 14px 10px 30px; background: var(--bf-surface-2); border-radius: 10px; color: var(--bf-text); line-height: 1.6 }
.bf-explain > ul > li + li { margin-top: 6px }

/* An evidence grade carries its meaning as a word, not only a code. */
.bf-grade { display: inline-flex; align-items: baseline; gap: 4px }
.bf-grade > b { font: inherit; font-weight: 700 }
.bf-grade > small { font-size: 10px; font-weight: 500; letter-spacing: 0 }

/* Attention items read as cards: figure, why it is here, how it was computed, what next. */
.bf-brief-attention { list-style: none; padding: 0; margin: 0; counter-reset: bf-attention; display: grid; gap: 12px }
.bf-brief-attention > li { counter-increment: bf-attention; margin: 0; border: 1px solid var(--bf-line); border-radius: 12px; padding: 12px 14px 10px; background: var(--bf-surface) }
.bf-brief-attention .bf-check { margin-top: 0 }
.bf-brief-attention .bf-check-title::before { content: counter(bf-attention) '  '; color: var(--bf-muted); font-weight: 500 }
.bf-brief-attention p { margin: 4px 0 }
.bf-why { font-size: 13px; line-height: 1.55; color: var(--bf-text) }
.bf-why-arrow { color: var(--bf-muted); margin: 0 8px }
.bf-formula-line code { font-size: 11px; background: var(--bf-surface-2); border-radius: 4px; padding: 1px 5px; overflow-wrap: anywhere }

/* Source citations: department, row and column on one line, the file beneath. */
.bf-brief-sources > summary { cursor: pointer; font-size: 12px; color: var(--bf-accent); margin-top: 4px }
.bf-brief-sources ul { list-style: none; padding: 0; margin: 8px 0 4px; display: grid; gap: 6px }
.bf-brief-sources li { display: grid; grid-template-columns: max-content max-content minmax(0, 1fr); gap: 2px 10px; align-items: baseline; font-size: 12px; padding: 6px 8px; border-radius: 8px; background: var(--bf-surface-2) }
.bf-brief-sources li > button { border: 0 !important; background: transparent !important; color: var(--bf-accent) !important; padding: 0 !important; font-weight: 600; text-decoration: underline; text-underline-offset: 2px; cursor: pointer }
.bf-brief-sources li > small { grid-column: 1 / -1; color: var(--bf-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis }

/* Room to breathe: metrics sit in a grid once the studio is wide enough. */
.bf-brief-metrics { grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px }
.bf-brief-metrics > div { padding: 10px 12px; border-radius: 10px }
.bf-step-owner { display: block; margin-top: 2px }
.bf-count { font-variant-numeric: tabular-nums }

/* Tool-call marks are buttons; the generic button padding pushed their labels below the track. */
.bf-run-lane-track > .bf-run-mark { display: flex; align-items: center; padding: 0 6px; margin: 0; line-height: 1 }
/* Grades inside a big figure keep their own small size. */
.bf-check .bf-grade > b, .bf-brief-metrics dd .bf-grade > b { font-size: 10px; font-weight: 700; letter-spacing: .02em }
.bf-brief-attention .bf-brief-sources li { margin: 0 }
/* File names in Sources stay on one line; the full name is in the tooltip. */
.bf-resource-list strong { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.bf-run-mark-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }

/* The filling-and-handoff flow: every stage, who acts there, how many records sit there. */
.bf-pipeline { list-style: none; margin: 12px 0 16px; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(112px, 1fr)); gap: 8px }
.bf-pipeline > li { position: relative; display: grid; gap: 2px; padding: 10px 12px; border: 1px solid var(--bf-line); border-radius: 10px; background: var(--bf-surface-2); --bf-stage: var(--bf-muted) }
.bf-pipeline > li[data-actor=flowActorYou] { --bf-stage: var(--bf-ok) }
.bf-pipeline > li[data-actor=flowActorDownstream] { --bf-stage: var(--bf-accent) }
.bf-pipeline > li[data-active=true] { background: var(--bf-surface); border-color: var(--bf-stage); box-shadow: inset 3px 0 var(--bf-stage) }
.bf-pipeline-actor { font-size: 10px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; color: var(--bf-stage) }
.bf-pipeline > li > b { font-size: 13px; font-weight: 600; line-height: 1.3 }
.bf-pipeline-count { font-size: 20px; font-weight: 650; font-variant-numeric: tabular-nums; color: var(--bf-muted) }
.bf-pipeline > li[data-active=true] .bf-pipeline-count { color: var(--bf-text) }
.bf-blockers { margin: 4px 0 6px; padding-left: 18px; font-size: 12px; line-height: 1.55 }
.bf-sample-cases { margin: 10px 0; font-size: 12px }
.bf-sample-cases > summary { cursor: pointer; color: var(--bf-muted) }
.bf-sample-cases ul { list-style: none; padding: 0; margin: 8px 0 0; display: grid; gap: 6px }
.bf-sample-cases button { display: grid; gap: 2px; width: 100%; text-align: left; padding: 8px 10px; border: 1px solid var(--bf-line); border-radius: 10px; background: transparent; cursor: pointer }
.bf-sample-cases button small { color: var(--bf-muted); line-height: 1.45 }
.bf-decision .bf-handoff-draft th { white-space: nowrap; vertical-align: top }
/* Discovery → workflow scope, timelines and time limits. */
.bf-scope h3 { margin: 0 0 4px; font-size: 14px }
.bf-scope-list { margin: 6px 0; padding-left: 18px; font-size: 13px; line-height: 1.55 }
.bf-due { font-size: 11px; font-weight: 600; padding: 1px 8px; border-radius: 10px; background: var(--bf-surface-2); color: var(--bf-muted) }
.bf-due[data-overdue=true] { background: var(--bf-danger-bg); color: var(--bf-danger) }
.bf-pipeline-late { font-size: 11px; font-weight: 600; color: var(--bf-danger) }
.bf-pipeline > li[data-late=true] { box-shadow: inset 3px 0 var(--bf-danger) }
.bf-timeline { list-style: none; margin: 8px 0; padding: 0 0 0 14px; border-left: 2px solid var(--bf-line); display: grid; gap: 8px; font-size: 12px }
.bf-timeline > li { position: relative }
.bf-timeline > li::before { content: ''; position: absolute; left: -19px; top: 5px; width: 8px; height: 8px; border-radius: 50%; background: var(--bf-accent) }
.bf-timeline time { color: var(--bf-muted); margin-right: 8px; font-variant-numeric: tabular-nums }
.bf-timeline p { margin: 2px 0 0 }
/* Overview: KPI tiles, small multiples and bar lists. One mark colour, critical reserved for overdue/refused. */
.bf-overview { display: grid; gap: 16px }
.bf-ov-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap }
.bf-ov-head h3 { margin: 0 }
.bf-ov-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px }
.bf-ov-tile { display: grid; gap: 4px; text-align: left; padding: 14px; border: 1px solid var(--bf-line); border-radius: 12px; background: var(--bf-surface); color: var(--bf-text); cursor: pointer; transition: transform .18s ease, box-shadow .18s ease }
.bf-ov-tile:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgb(0 0 0 / 8%) }
.bf-ov-tile > span { font-size: 12px; color: var(--bf-muted) }
.bf-ov-tile > b { font-size: 28px; line-height: 1.1; font-variant-numeric: tabular-nums }
.bf-ov-tile > small { font-size: 12px; color: var(--bf-muted); display: grid; gap: 4px }
.bf-ov-tile[data-tone=critical] { border-color: var(--bf-chart-critical) }
.bf-ov-meter { display: block; height: 6px; border-radius: 3px; background: var(--bf-surface-2); overflow: hidden }
.bf-ov-meter > span { display: block; height: 100%; background: var(--bf-chart-mark); border-radius: 3px }
.bf-ov-critical { color: var(--bf-danger); font-weight: 600 }
.bf-ov-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(max(260px, 30%), 1fr)); gap: 12px }
.bf-ov-block { border: 1px solid var(--bf-line); border-radius: 12px; padding: 14px; background: var(--bf-surface); display: grid; gap: 10px; align-content: start; min-width: 0 }
.bf-ov-block[data-wide=true] { grid-column: 1 / -1 }
.bf-ov-block > header { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap }
.bf-ov-block h4 { margin: 0; font-size: 13px }
.bf-ov-block > header button { font-size: 12px; padding: 3px 10px; white-space: nowrap; width: auto }
.bf-ov-sparks { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px }
.bf-ov-sparks[data-bars=true] { grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr)) }
.bf-ov-spark { margin: 0; display: grid; gap: 4px }
.bf-ov-spark figcaption { display: grid; gap: 1px; font-size: 12px; color: var(--bf-muted) }
.bf-ov-spark figcaption b { font-size: 18px; color: var(--bf-text); font-variant-numeric: tabular-nums }
.bf-ov-spark figcaption b .bf-ov-critical { display: block; font-size: 11px; font-weight: 600 }
.bf-ov-spark svg { width: 100%; height: 64px; overflow: visible; cursor: crosshair }
.bf-ov-line { fill: none; stroke: var(--bf-chart-mark); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round }
.bf-ov-threshold { stroke: var(--bf-muted); stroke-width: 1; stroke-dasharray: 3 3 }
.bf-ov-cross { stroke: var(--bf-line); stroke-width: 1 }
.bf-ov-dot { fill: var(--bf-chart-mark); stroke: var(--bf-surface); stroke-width: 2 }
.bf-ov-dot[data-critical=true] { fill: var(--bf-chart-critical) }
.bf-ov-bars { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px }
.bf-ov-bars > li { position: relative; display: grid; grid-template-columns: minmax(0, 9.5em) 1fr auto; align-items: center; gap: 8px; font-size: 12px }
.bf-ov-bar-label { overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.25; color: var(--bf-text) }
.bf-ov-bar-track { display: flex; gap: 2px; height: 12px }
.bf-ov-bar { display: block; height: 100%; min-width: 2px; background: var(--bf-chart-mark); border-radius: 0 4px 4px 0; transition: width .5s cubic-bezier(.2,.8,.2,1) }
.bf-ov-bar[data-critical=true] { background: var(--bf-chart-critical) }
.bf-ov-bars > li[data-hover=true] .bf-ov-bar { filter: brightness(1.1) }
.bf-ov-bar-value { font-variant-numeric: tabular-nums; color: var(--bf-text); text-align: right }
.bf-ov-tip { position: absolute; right: 0; top: -26px; z-index: 2; padding: 3px 8px; border-radius: 6px; background: var(--bf-text); color: var(--bf-surface); font-size: 11px; white-space: nowrap; pointer-events: none }
@media (prefers-reduced-motion: reduce) { .bf-ov-tile, .bf-ov-bar { transition: none } }
.bf-row-actions { display: flex; gap: 8px; flex-wrap: wrap }
.bf-row-actions > button { flex: 0 0 auto; width: auto; padding: 4px 12px; font-size: 12px }
/* Guest mode: say what this instance is, and where Feishu would have been. */
.bf-guest-banner { display: grid; gap: 4px; margin: 0 0 14px; padding: 10px 12px; font-size: 12px; line-height: 1.5; border-radius: 10px; background: var(--bf-warn-bg); color: var(--bf-warn); border-left: 3px solid var(--bf-warn) }
.bf-guest-pill { margin-left: 10px; padding: 2px 9px; border-radius: 10px; font-size: 11px; font-weight: 600; background: rgb(230 150 40 / 20%); color: #b86e00 }
.bf-guest-banner strong { font-size: 12px }
.bf-guest-off { opacity: .8 }
/* Approval card: where it came from, what will happen, what to check; plumbing folded away. */
.bf-decision header { flex-wrap: wrap }
.bf-approval-area { flex-basis: 100%; display: block; font-size: 11px; font-weight: 600; letter-spacing: .04em; color: var(--bf-muted); margin-bottom: 2px }
.bf-approval-summary { font-size: 14px; line-height: 1.5; margin: 0 0 6px }
.bf-approval-check { margin: 8px 0 4px; font-size: 12px; font-weight: 600 }
.bf-approval-technical { margin-top: 8px; font-size: 12px; color: var(--bf-muted) }
.bf-approval-technical summary { cursor: pointer }
/* The chart keeps the size it was drawn at: stretched to a wide preview, its labels grew to
   headline size and the plot ran past the bottom of the window. */
.bf-quadrant { display: block; width: 100%; max-width: 560px; height: auto; max-height: 60vh; margin: 0 auto }
.bf-quadrant-label { fill: var(--bf-muted) }
.bf-quadrant-name { fill: var(--bf-text); font-weight: 600 }
.bf-quadrant-dot { fill: var(--bf-chart-mark); stroke: var(--bf-surface); stroke-width: 2; cursor: pointer }
`
