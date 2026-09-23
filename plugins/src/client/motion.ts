/**
 * Motion for the BridgeFlow surfaces.
 *
 * Kept apart from `style.ts` so the rules about movement live in one place:
 *
 * - **Motion explains a change, it does not decorate one.** Things that appear (a dialog,
 *   a drawer, a preview, a report) arrive from where they come from; things that change
 *   state (a pressed tab, a selected file, a hovered row) cross-fade. Nothing loops except
 *   an honest "still loading".
 * - **Short and front-loaded.** 120 ms for state, 180–240 ms for arrivals, all on a
 *   decelerating curve, so a click never waits on an animation.
 * - **Only opacity and transform move**, with one exception: when a studio page opens or
 *   closes, the panes glide to the reading layout once. Dragging a divider and long tables
 *   are never animated; that would stutter.
 * - **Reduced motion is respected.** With `prefers-reduced-motion: reduce`, arrivals and
 *   the loading pulse are removed and only colour changes remain.
 */
export const motion = `
:root {
  --bf-ease-out: cubic-bezier(.22, .8, .26, 1);
  --bf-ease-in-out: cubic-bezier(.45, 0, .2, 1);
  --bf-dur-state: 120ms;
  --bf-dur-enter: 200ms;
  --bf-dur-panel: 240ms;
}

@keyframes bf-rise { from { opacity: 0; transform: translateY(6px) } to { opacity: 1; transform: none } }
@keyframes bf-fade { from { opacity: 0 } to { opacity: 1 } }
@keyframes bf-dialog-in { from { opacity: 0; transform: translateY(10px) scale(.985) } to { opacity: 1; transform: none } }
@keyframes bf-from-right { from { opacity: 0; transform: translateX(16px) } to { opacity: 1; transform: none } }
@keyframes bf-from-left { from { opacity: 0; transform: translateX(-16px) } to { opacity: 1; transform: none } }
@keyframes bf-notice-in { from { opacity: 0; transform: translate(-50%, -8px) } to { opacity: 1; transform: translate(-50%, 0) } }
@keyframes bf-page-in { from { opacity: 0; transform: translateY(-6px) } to { opacity: 1; transform: none } }
@keyframes bf-sweep { from { background-position: 120% 0 } to { background-position: -120% 0 } }
@keyframes bf-pulse { 0%, 100% { opacity: 1 } 50% { opacity: .45 } }

/* ---- state changes: cross-fade colour, border and shadow ---------------- */

.bf-panel button, .bf-card button, .bf-state button, .bf-drawer button, .bf-open,
.bf-shell-top button, .bf-add-source, .bf-artifact, .bf-resource-list button,
.bf-studio-tools button, .bf-notebook-list button, .bf-file, .bf-notebook-title,
.bf-panel input, .bf-panel select, .bf-state input, .bf-drawer input, .bf-card textarea,
.bf-chip, .bf-badge, .bf-save-state, .bf-panel-resizer, .bf-panel-body > details > summary,
.bf-panel td, .bf-source-table td {
  transition-property: background-color, border-color, color, box-shadow, opacity, filter, transform, outline-color;
  transition-duration: var(--bf-dur-state);
  transition-timing-function: var(--bf-ease-out);
}

/* A press is acknowledged at once, before anything else responds. */
.bf-panel button:active:not(:disabled), .bf-card button:active:not(:disabled),
.bf-state button:active:not(:disabled), .bf-drawer button:active:not(:disabled),
.bf-shell-top button:active:not(:disabled), .bf-open:active, .bf-add-source:active {
  transform: scale(.97);
  transition-duration: 60ms;
}

/* The studio tiles are the only card-like controls; they lift slightly under the pointer. */
.bf-studio-tools button:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 14px #0f172a1a }
.bf-studio-tools button:active:not(:disabled) { transform: translateY(0) scale(.98); box-shadow: none }
.bf-artifact:active:not(:disabled), .bf-resource-list button:active:not(:disabled) { transform: scale(.99) }

/* Focus rings grow in instead of snapping. */
.bf-panel input:focus-visible, .bf-card textarea:focus-visible { box-shadow: 0 0 0 4px var(--bf-accent-soft) }

/* ---- reading layout ---------------------------------------------------- */

/* Opening a studio page widens the studio and narrows Sources; the panes glide there
   once. Only while the attribute is set, so dragging a divider never lags behind. */
body[data-bf-reflow] .bf-shell-pane.bf-state { transition: width var(--bf-dur-panel) var(--bf-ease-in-out) }
body[data-bf-reflow][data-bf-notebook] [data-slot="root"] > div { transition: padding var(--bf-dur-panel) var(--bf-ease-in-out) }
body[data-bf-reflow] .bf-panel-resizer { transition: left var(--bf-dur-panel) var(--bf-ease-in-out), right var(--bf-dur-panel) var(--bf-ease-in-out) }

/* ---- arrivals ----------------------------------------------------------- */

.bf-panel[open] { animation: bf-dialog-in var(--bf-dur-panel) var(--bf-ease-out) }
.bf-panel[open]::backdrop { animation: bf-fade var(--bf-dur-panel) var(--bf-ease-out) }

/* Drawers and the narrow-screen panes slide in from the edge they are attached to. */
.bf-drawer, .bf-shell-studio[data-mobile-open=true] { animation: bf-from-right var(--bf-dur-panel) var(--bf-ease-out) }
.bf-shell-sources[data-mobile-open=true] { animation: bf-from-left var(--bf-dur-panel) var(--bf-ease-out) }
body[data-bf-notebook][data-bf-nav] [data-slot="root"] > div > div:has(> [data-slot="sidebar"]) {
  animation: bf-from-left var(--bf-dur-panel) var(--bf-ease-out);
}

/* The notebook panes settle in once when the page opens or a hidden pane comes back. */
.bf-shell-pane.bf-state { animation: bf-fade var(--bf-dur-panel) var(--bf-ease-out) }

/* Content that appears in place rises a few pixels, so the eye follows where it landed. */
.bf-inline-preview, .bf-callout, .bf-empty, .bf-shell-empty, .bf-notebook-empty,
.bf-report, .bf-quotation-paper, .bf-hero, .bf-state-head {
  animation: bf-rise var(--bf-dur-enter) var(--bf-ease-out) both;
}
.bf-route-notice { animation: bf-notice-in var(--bf-dur-enter) var(--bf-ease-out) both }

/* Department cards arrive in reading order; the stagger stops after six. */
.bf-report-roles > *, .bf-state-map > section, .bf-studio-tools > * {
  animation: bf-rise var(--bf-dur-enter) var(--bf-ease-out) both;
}
.bf-report-roles > :nth-child(2), .bf-state-map > section:nth-child(2), .bf-studio-tools > :nth-child(2) { animation-delay: 30ms }
.bf-report-roles > :nth-child(3), .bf-state-map > section:nth-child(3), .bf-studio-tools > :nth-child(3) { animation-delay: 60ms }
.bf-report-roles > :nth-child(4), .bf-state-map > section:nth-child(4), .bf-studio-tools > :nth-child(4) { animation-delay: 90ms }
.bf-report-roles > :nth-child(5), .bf-state-map > section:nth-child(5), .bf-studio-tools > :nth-child(5) { animation-delay: 120ms }
.bf-report-roles > :nth-child(n+6), .bf-state-map > section:nth-child(n+6), .bf-studio-tools > :nth-child(n+6) { animation-delay: 150ms }

/* Expanding a section reveals its content rather than dropping it in. */
.bf-panel details[open] > :not(summary), .bf-report details[open] > :not(summary),
.bf-hero details[open] > :not(summary), .bf-formulas[open] > :not(summary) {
  animation: bf-rise var(--bf-dur-enter) var(--bf-ease-out) both;
}

/* A studio page is remounted per destination, so switching pages reads as arriving
   somewhere new: the page slides in from the tiles above, then its parts settle in order. */
.bf-inline-preview { animation: bf-page-in var(--bf-dur-panel) var(--bf-ease-out) both }
.bf-inline-preview > :not(header) > *, .bf-brief > * { animation: bf-rise var(--bf-dur-enter) var(--bf-ease-out) both }
.bf-inline-preview > :not(header) > :nth-child(2), .bf-brief > :nth-child(2) { animation-delay: 40ms }
.bf-inline-preview > :not(header) > :nth-child(3), .bf-brief > :nth-child(3) { animation-delay: 80ms }
.bf-inline-preview > :not(header) > :nth-child(4), .bf-brief > :nth-child(4) { animation-delay: 120ms }
.bf-inline-preview > :not(header) > :nth-child(n+5), .bf-brief > :nth-child(n+5) { animation-delay: 160ms }
.bf-brief-attention > li { animation: bf-rise var(--bf-dur-enter) var(--bf-ease-out) both }
.bf-brief-attention > li:nth-child(2) { animation-delay: 60ms }
.bf-brief-attention > li:nth-child(n+3) { animation-delay: 120ms }
.bf-explain[open] > ul { animation: bf-rise var(--bf-dur-enter) var(--bf-ease-out) both }

/* The start page's flow is read top to bottom: each step arrives in turn and the line
   to the next one draws after it, so the order is shown rather than stated. */
@keyframes bf-draw { from { transform: scaleY(0) } to { transform: scaleY(1) } }
.bf-flow > li { animation: bf-rise var(--bf-dur-enter) var(--bf-ease-out) both }
.bf-flow > li:not(:last-child)::after { animation: bf-draw 260ms var(--bf-ease-out) both }
.bf-flow > li:nth-child(1) { animation-delay: 60ms } .bf-flow > li:nth-child(1)::after { animation-delay: 180ms }
.bf-flow > li:nth-child(2) { animation-delay: 200ms } .bf-flow > li:nth-child(2)::after { animation-delay: 320ms }
.bf-flow > li:nth-child(3) { animation-delay: 340ms } .bf-flow > li:nth-child(3)::after { animation-delay: 460ms }
.bf-flow > li:nth-child(4) { animation-delay: 480ms }

/* ---- waiting ------------------------------------------------------------ */
/* Work in flight says so by movement as well as by word: a light sweeps across the
   chip while the captain is dispatching departments. */
.bf-chip[data-status=dispatching], .bf-chip[data-status=running] {
  background-image: linear-gradient(100deg, transparent 20%, color-mix(in srgb, var(--bf-accent) 22%, transparent) 50%, transparent 80%);
  background-size: 220% 100%; animation: bf-sweep 1.6s var(--bf-ease-in-out) infinite;
}

.bf-loading { animation: bf-pulse 1.4s var(--bf-ease-in-out) infinite }

/* ---- reduced motion ----------------------------------------------------- */

@media (prefers-reduced-motion: reduce) {
  .bf-panel[open], .bf-panel[open]::backdrop, .bf-drawer, .bf-shell-pane.bf-state,
  .bf-shell-studio[data-mobile-open=true], .bf-shell-sources[data-mobile-open=true],
  body[data-bf-notebook][data-bf-nav] [data-slot="root"] > div > div:has(> [data-slot="sidebar"]),
  .bf-inline-preview, .bf-callout, .bf-empty, .bf-shell-empty, .bf-notebook-empty,
  .bf-report, .bf-quotation-paper, .bf-hero, .bf-state-head, .bf-route-notice,
  .bf-report-roles > *, .bf-state-map > section, .bf-studio-tools > *,
  .bf-panel details[open] > :not(summary), .bf-report details[open] > :not(summary),
  .bf-hero details[open] > :not(summary), .bf-formulas[open] > :not(summary), .bf-loading,
  .bf-inline-preview > :not(header) > *, .bf-brief > *, .bf-brief-attention > li, .bf-explain[open] > ul,
  .bf-chip[data-status=dispatching], .bf-chip[data-status=running], .bf-flow > li, .bf-flow > li::after {
    animation: none !important;
  }
  body[data-bf-reflow] .bf-shell-pane.bf-state, body[data-bf-reflow][data-bf-notebook] [data-slot="root"] > div,
  body[data-bf-reflow] .bf-panel-resizer { transition: none !important }
  .bf-panel button, .bf-card button, .bf-state button, .bf-drawer button, .bf-open,
  .bf-shell-top button, .bf-add-source, .bf-artifact, .bf-resource-list button, .bf-studio-tools button {
    transform: none !important;
  }
  .bf-studio-tools button:hover:not(:disabled) { box-shadow: none }
}
`
