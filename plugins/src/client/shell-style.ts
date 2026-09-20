/** rc.1's public data-slot style anchors retain all native occupants and stores.
 * No private CSS module names, DOM reparenting, second React root or DSH fork. */
export const shellStyle = `
/* Every colour here resolves from the host's own alias tokens, which the theme plugin
 * declares on \`body\` and swaps wholesale on \`body[data-ds-dark-theme]\`. That is the
 * whole reason there is no dark-mode block below: following the user's theme is the
 * host's job, and a second palette of our own was the thing to delete. Each fallback
 * is the value this shell shipped with, for a host build that publishes no alias. */
body[data-bf-notebook] {
  --bf-shell-top-height: 52px;
  --bf-shell-left: clamp(240px, 25vw, 440px); --bf-shell-right: clamp(280px, 26vw, 460px);
  --bf-shell-pane: var(--dsw-alias-bg-layer-1, #fff);
  /* In light mode the host paints base, layer-1 and layer-2 the same white, so a canvas
     taken straight from bg-base would erase the three-pane separation that carries the
     whole notebook layout. Tinting the base with its own ink keeps the two apart in
     either theme without inventing a colour. */
  --bf-shell-bg: color-mix(in srgb, var(--dsw-alias-label-primary, #242629) 4%, var(--dsw-alias-bg-base, #fff));
  --bf-shell-border: var(--dsw-alias-border-l3, #dbe0e7);
  --bf-shell-text: var(--dsw-alias-label-primary, #242629);
  --bf-shell-muted: var(--dsw-alias-label-secondary, #606773);
  --bf-shell-accent: var(--dsw-alias-state-business-primary, #4176e6);
  --bf-shell-accent-bg: var(--dsw-alias-state-business-tertiary, #e4edfd);
  --bf-shell-accent-ink: color-mix(in srgb, var(--bf-shell-accent) 60%, var(--bf-shell-text));
  --bf-shell-hover: var(--dsw-alias-interactive-bg-hover, #2631480f);
  /* The host's warn label is one amber for both themes, which reads at about 2.4:1 on
     white — too thin for an 11px "unsaved". Pulling it toward the page ink clears 4.5:1
     in light and stays amber in dark, from one declaration. */
  --bf-shell-warn: color-mix(in srgb, var(--dsw-alias-state-warn-label, #dd8629) 72%, var(--bf-shell-text));
  --bf-shell-scrim: var(--dsw-alias-bg-mask-1, #0000003d);
  /* Studio tile hues, named but unchanged. Collapsing these five onto F04's single
     accent is a deliberate later decision, not an oversight. */
  --bf-tone-blue: #859feb; --bf-tone-gold: #c4b66b; --bf-tone-green: #809f83;
  --bf-tone-pink: #b58cae; --bf-tone-teal: #6f9fa6;
}
/* AppFrame wrappers contain public slot anchors; native detail transitions stay. */
body[data-bf-notebook] [data-slot="root"] > div {
  grid-template-columns: 0 minmax(0, 1fr) 0 !important;
  padding: var(--bf-shell-top-height) calc(var(--bf-shell-right) + 24px) 14px calc(var(--bf-shell-left) + 24px);
  box-sizing: border-box; background: var(--bf-shell-bg);
}
body[data-bf-notebook] [data-slot="root"] > div > [data-side] { display: none }
body[data-bf-notebook] [data-slot="root"] > div > div:has(> [data-slot="conversation"]) {
  grid-column: 2; grid-row: 1; border-radius: 16px; background: var(--bf-shell-pane); padding-top: 36px; position: relative;
}
body[data-bf-notebook] [data-slot="root"] > div > div:has(> [data-slot="conversation"])::before {
  content: 'Chat'; position: absolute; left: 16px; top: 14px; color: var(--bf-shell-text);
  font-weight: 500; font-size: 12.5px; line-height: 18px;
}
body[data-bf-notebook] [data-slot="conversation"] > div {
  --dsw-alias-bg-base: var(--bf-shell-pane); --dsw-alias-bg-layer-1: var(--bf-shell-pane);
  --dsw-alias-bg-layer-2: var(--bf-shell-bg); --dsw-alias-border-l3: var(--bf-shell-border);
  border-top: 1px solid var(--bf-shell-border);
}
body[data-bf-notebook] [data-phase="hero"] [data-composer-seat] { flex: 1; min-height: 500px }
body[data-bf-notebook] [data-phase="hero"] div:has(> [data-slot="conversation.composer.bar"]) { flex: 1; width: 100%; padding: 30px 0 12px }
body[data-bf-notebook] [data-phase="hero"] [data-slot="conversation.composer.bar"] { display: block !important; margin-top: auto }
body[data-bf-notebook] div:has(> div > div > span > [data-slot="conversation.hero.brand.mark"]) { height: auto; padding: 0 30px }
body[data-bf-notebook] div:has(> span > [data-slot="conversation.hero.brand.mark"]) { display: block; margin-bottom: 14px }
body[data-bf-notebook] span:has(> [data-slot="conversation.hero.brand.mark"]) ~ span { display: none }
.bf-welcome { color: var(--bf-shell-text); text-align: left }
.bf-welcome > span { color: var(--bf-shell-accent); font-size: 36px }
.bf-welcome h2 { margin: 14px 0; font-size: 25px; line-height: 1.45; font-weight: 500 }
.bf-welcome p { margin: 0; color: var(--bf-shell-muted); font-size: 13px; line-height: 1.8 }
/* S02 is one surface: the ✦ heading above (.bf-welcome, in the host's hero mark slot)
   and this card under it. The card used to render its own heading and lead and then
   hide both, leaving a bare row of buttons under somebody else's title. */
body[data-bf-notebook] .bf-hero { box-sizing: border-box; background: var(--bf-shell-pane); border: 1px solid var(--bf-shell-border); box-shadow: none; border-radius: 14px; padding: 18px 20px; margin: 0 30px 24px; color: var(--bf-shell-text) }
body[data-bf-notebook] .bf-hero > h3 { margin: 0; font-size: 14px; font-weight: 500 }
body[data-bf-notebook] .bf-hero > p { margin: 4px 0 0 }
body[data-bf-notebook] .bf-hero .bf-actions { display: flex; flex-wrap: wrap; gap: 8px }
body[data-bf-notebook] .bf-hero button { background: transparent !important; color: var(--bf-shell-text) !important; border: 1px solid var(--bf-shell-border); border-radius: 24px; padding: 8px 14px; width: auto; font-size: 12px; font-weight: 400 }
/* F04: one accent per screen. With three actions on the card, a row of identical pills
   is back to telling you nothing about which one starts the work. */
body[data-bf-notebook] .bf-hero button.bf-primary { background: var(--bf-shell-accent) !important; color: var(--dsw-alias-label-primary-inverted, #fff) !important; border-color: transparent }
body[data-bf-hide-sources] [data-slot="root"] > div { padding-left: 12px }
body[data-bf-hide-studio] [data-slot="root"] > div { padding-right: 12px }
body[data-bf-hide-sources] .bf-shell-sources, body[data-bf-hide-studio] .bf-shell-studio { display: none !important }
/* Navigation remains a native drawer, including settings and workspaces. */
body[data-bf-notebook] [data-slot="root"] > div > div:has(> [data-slot="sidebar"]) {
  position: fixed; left: 12px; top: var(--bf-shell-top-height); bottom: 14px; width: 300px; z-index: 45;
  border-radius: 16px; box-shadow: 0 12px 40px var(--bf-shell-scrim); display: none;
}
body[data-bf-notebook][data-bf-nav] [data-slot="root"] > div > div:has(> [data-slot="sidebar"]) { display: block }
body[data-bf-notebook] [data-slot="root"] > div > div:has(> [data-slot="details"]) {
  position: fixed; right: 12px; top: var(--bf-shell-top-height); bottom: 14px; width: var(--bf-shell-right);
  z-index: 35; background: var(--bf-shell-pane); border-radius: 16px;
}
body[data-bf-notebook] [data-slot="root"] > [data-details-collapsed] > div:has(> [data-slot="details"]) { width: 0; border: 0 }
.bf-shell-top { position: fixed; inset: 0 0 auto; height: var(--bf-shell-top-height); padding: 0 18px; display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--bf-shell-text); pointer-events: auto }
.bf-shell-brand { display: flex; align-items: center; gap: 8px; min-width: 0 }
.bf-shell-title { font-size: 13px; color: var(--bf-shell-muted) }
.bf-shell-top nav { display: flex; align-items: center; gap: 8px }
/* The notebook menu. <details> because the disclosure, the Escape key and the tab order
   are the browser's to get right, and a hand-rolled popup gets one of the three wrong. */
.bf-shell-menu { position: relative }
.bf-shell-menu > summary { list-style: none; cursor: pointer; display: grid; place-items: center; width: 29px; height: 29px; border-radius: 8px; font-size: 15px }
.bf-shell-menu > summary::-webkit-details-marker { display: none }
.bf-shell-menu > summary:hover, .bf-shell-menu[open] > summary { background: var(--bf-shell-hover) }
.bf-shell-menu-list { position: absolute; left: 0; top: calc(100% + 6px); z-index: 60; display: grid; min-width: 180px; padding: 6px; border-radius: 12px; background: var(--bf-shell-pane); border: 1px solid var(--bf-shell-border); box-shadow: 0 12px 40px var(--bf-shell-scrim) }
.bf-shell-menu-list button { text-align: left; border: 0; background: transparent; border-radius: 8px; padding: 9px 10px; font-size: 13px }
.bf-shell-menu-list button:hover:not(:disabled) { background: var(--bf-shell-hover) }
.bf-purpose-chip { font-size: 11px; padding: 4px 10px; border-radius: 999px; background: var(--bf-shell-accent-bg); color: var(--bf-shell-accent-ink); white-space: nowrap }
.bf-shell-top button, .bf-shell-pane button { font: inherit; cursor: pointer; color: inherit }
.bf-shell-top button { border: 1px solid var(--bf-shell-border); background: transparent; border-radius: 24px; padding: 5px 12px; font-size: 12px }
.bf-shell-pane.bf-state {
  position: fixed; top: var(--bf-shell-top-height); bottom: 14px; height: auto; margin: 0; border-radius: 16px; padding: 0;
  display: flex; flex-direction: column; overflow: hidden; pointer-events: auto;
  background: var(--bf-shell-pane); color: var(--bf-shell-text); font-size: 13px;
  --bf-surface: var(--bf-shell-pane); --bf-surface-2: var(--bf-shell-bg); --bf-line: var(--bf-shell-border);
  --bf-text: var(--bf-shell-text); --bf-muted: var(--bf-shell-muted);
  --bf-accent: var(--bf-shell-accent); --bf-accent-soft: var(--bf-shell-accent-bg);
}
.bf-shell-sources { left: 12px; width: var(--bf-shell-left) }
.bf-shell-studio { right: 12px; width: var(--bf-shell-right) }
/* S01's .panetitle: a label, not a title bar. The 40px band and its rule drew three
   heavy horizontal lines across a screen whose panes are already separated by their
   own edges — the same information, three times, in the most expensive way. */
.bf-shell-pane > header { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; padding: 14px 14px 0 }
.bf-shell-pane > header h2 { font-size: 12.5px; font-weight: 500 }
.bf-shell-scroll { padding: 8px 14px 14px; flex: 1; min-height: 0; overflow: auto }
.bf-add-source { width: 100%; border: 1px solid var(--bf-shell-border); border-radius: 22px; background: transparent; padding: 8px; font-size: 12px }
.bf-add-source:hover, .bf-resource-list button:hover, .bf-artifact:hover { background: color-mix(in srgb, var(--bf-shell-text) 7%, transparent) }
.bf-source-batch { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 20px 0 12px }
.bf-source-batch code { width: 100%; font-size: 10px; overflow-wrap: anywhere; color: var(--bf-shell-muted) }
.bf-source-batch button { background: transparent; border: 0; font-size: 11px; margin-left: auto }
.bf-resource-list { list-style: none; padding: 0; margin: 0 }
.bf-resource-list button { border: 0; border-radius: 10px; background: transparent; display: flex; gap: 12px; align-items: center; padding: 13px 8px; text-align: left; width: 100% }
.bf-resource-list button > span:nth-child(2), .bf-artifact > span:nth-child(2) { flex: 1; min-width: 0 }
.bf-resource-list strong, .bf-artifact strong { display: block; font-size: 13px; font-weight: 500; overflow-wrap: anywhere }
.bf-resource-list small, .bf-artifact small { display: block; font-size: 11px; color: var(--bf-shell-muted); margin-top: 5px }
.bf-resource-list button[aria-pressed=true], .bf-artifact[aria-pressed=true] { background: color-mix(in srgb, var(--bf-shell-accent) 17%, transparent); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--bf-shell-accent) 40%, transparent) }
.bf-file-icon { font-size: 23px; color: var(--bf-shell-muted) }
.bf-shell-empty { min-height: 320px; height: 48vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; color: var(--bf-shell-muted); font-size: 12px }
.bf-shell-empty > span { font-size: 32px; margin-bottom: 12px }
.bf-shell-empty p { max-width: 260px }
.bf-existing { color: var(--bf-shell-muted); font-size: 12px; margin-top: 20px }
.bf-existing form { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px }
.bf-existing input { min-width: 0; width: 100%; background: transparent; color: inherit; border: 1px solid var(--bf-shell-border); border-radius: 8px; padding: 8px }
.bf-studio-tools { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px }
.bf-studio-tools button { display: grid; grid-template-columns: 1fr auto; text-align: left; gap: 10px; align-content: space-between; min-height: 78px; border: 0; border-radius: 12px; padding: 12px; font-size: 12px }
.bf-studio-tools button > span:first-child { grid-column: 1 / -1; font-size: 15px }
.bf-studio-tools [data-tone=blue] { background: color-mix(in srgb, var(--bf-tone-blue) 20%, var(--bf-shell-pane)) }
.bf-studio-tools [data-tone=gold] { background: color-mix(in srgb, var(--bf-tone-gold) 20%, var(--bf-shell-pane)) }
.bf-studio-tools [data-tone=green] { background: color-mix(in srgb, var(--bf-tone-green) 20%, var(--bf-shell-pane)) }
.bf-studio-tools [data-tone=pink] { background: color-mix(in srgb, var(--bf-tone-pink) 20%, var(--bf-shell-pane)) }
.bf-studio-tools [data-tone=teal] { background: color-mix(in srgb, var(--bf-tone-teal) 20%, var(--bf-shell-pane)) }
.bf-shell-pane button:disabled { opacity: .5; cursor: default }
.bf-artifacts { border-top: 1px solid var(--bf-shell-border); margin-top: 18px; padding-top: 16px }
.bf-artifacts > header, .bf-inline-preview > header { display: flex; align-items: center; gap: 8px; margin-bottom: 14px }
.bf-artifacts > header h3, .bf-inline-preview > header h3 { flex: 1; margin: 0; font-size: 13px }
.bf-artifacts > header button, .bf-inline-preview > header button { background: transparent; border: 1px solid var(--bf-shell-border); border-radius: 16px; padding: 5px 8px; font-size: 11px }
.bf-artifact { display: flex; align-items: center; gap: 10px; border: 0; border-radius: 10px; padding: 12px 8px; text-align: left; width: 100%; background: transparent; margin-bottom: 6px }
.bf-artifact .bf-chip { margin-top: 8px }
.bf-inline-preview { margin-top: 22px; border-top: 1px solid var(--bf-shell-border); padding-top: 16px }
.bf-source-table { overflow: auto; max-height: 55vh; border: 1px solid var(--bf-shell-border); border-radius: 8px }
.bf-source-table table { border-collapse: collapse; white-space: nowrap; font-size: 12px; width: 100% }
.bf-source-table th, .bf-source-table td { padding: 8px 12px; border-bottom: 1px solid var(--bf-shell-border); text-align: left; max-width: 480px; overflow: hidden; text-overflow: ellipsis }
.bf-source-table thead { position: sticky; top: 0; background: var(--bf-shell-pane, var(--bf-surface)) }
.bf-inline-preview code { overflow-wrap: anywhere; font-size: 10px }
.bf-inline-preview .bf-actions { font-size: 11px; gap: 6px }
.bf-inline-preview .bf-actions button { padding: 5px 8px }
.bf-document { padding: 0; min-width: 0 }
.bf-document-evidence { margin: 20px 0 }
.bf-document-checks { border-top: 1px solid var(--bf-line); padding-top: 16px }
.bf-studio-state { margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--bf-shell-border) }
.bf-shell-pane .bf-state-map { display: flex; flex-direction: column }
.bf-shell-pane .bf-report { padding: 0 }
.bf-shell-pane .bf-quotation-paper { padding: 16px }
.bf-shell-pane .bf-quotation-paper dl > div { display: block }
.bf-shell-pane .bf-quotation-paper dd { margin: 6px 0 0 }
body[data-bf-notebook] .bf-drawer { top: var(--bf-shell-top-height); right: 12px; bottom: 14px; height: auto; z-index: 50; border-radius: 16px }
.bf-mobile-close { display: none }
.bf-source-import { max-width: 740px }
.bf-expanded-preview .bf-document { padding: 16px }
.bf-shell-top button:focus-visible, .bf-shell-pane button:focus-visible, .bf-shell-menu > summary:focus-visible { outline: 2px solid var(--bf-shell-accent); outline-offset: 3px }
.bf-shell-top button[aria-expanded=true], .bf-shell-top button[aria-pressed=true] { background: var(--bf-shell-accent-bg); color: var(--bf-shell-accent-ink); border-color: color-mix(in srgb, var(--bf-shell-accent) 45%, transparent); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--bf-shell-accent) 45%, transparent) }
.bf-shell-pane .bf-studio-tools button[aria-pressed=true] { box-shadow: inset 0 0 0 2px var(--bf-shell-accent); background: color-mix(in srgb, var(--bf-shell-accent) 32%, var(--bf-shell-pane)) }
.bf-shell-top .bf-notebook-title { width: clamp(120px, 15vw, 260px); min-width: 70px; background: transparent; border: 1px solid transparent; border-radius: 6px; color: inherit; padding: 5px; font: inherit; font-size: 13px }
.bf-notebook-title:hover, .bf-notebook-title:focus { border-color: var(--bf-shell-border) }
.bf-save-state { font-size: 11px; white-space: nowrap; color: var(--bf-shell-muted) }
.bf-save-state[data-dirty=true] { color: var(--bf-shell-warn) }
.bf-notebook-purpose { display: flex; gap: 8px; align-items: center; justify-content: space-between }
.bf-notebook-purpose select { max-width: 65%; border: 1px solid var(--bf-shell-border); border-radius: 7px; background: var(--bf-shell-pane); color: inherit; padding: 6px }
.bf-source-provenance dt { font-weight:600; margin-top:10px }
.bf-source-provenance dd { margin:4px 0; overflow-wrap:anywhere }
.bf-panel.bf-notebook-dialog { width: min(560px, calc(100vw - 40px)); padding: 24px; color: var(--bf-shell-text); background: var(--bf-shell-pane); border: 1px solid var(--bf-shell-border); border-radius: 16px }
.bf-panel.bf-notebook-dialog header { display:flex; justify-content:space-between; align-items:center }
.bf-panel.bf-notebook-dialog p { font-size:13px; line-height:1.8; color:var(--bf-shell-muted) }
.bf-panel.bf-notebook-dialog input { display:block; width:100%; box-sizing:border-box; margin-top:8px; padding:10px; border:1px solid var(--bf-shell-border); border-radius:8px; background:transparent; color:inherit }
.bf-panel.bf-notebook-dialog button, .bf-quotation-progress button, .bf-shell-empty button { border:1px solid var(--bf-shell-border); border-radius:16px; padding:7px 12px; background:transparent; color:inherit; cursor:pointer }
.bf-panel.bf-notebook-dialog .bf-notebook-list { list-style:none; padding:0; max-height:55vh; overflow:auto }
.bf-panel.bf-notebook-dialog .bf-notebook-list button { display:flex; width:100%; justify-content:space-between; gap:12px; text-align:left; border:0; border-radius:10px; padding:14px 8px }
.bf-panel.bf-notebook-dialog .bf-notebook-list button:hover, .bf-panel.bf-notebook-dialog .bf-notebook-list button[aria-current=page] { background:color-mix(in srgb,var(--bf-shell-accent) 18%,transparent) }
.bf-panel.bf-notebook-dialog .bf-notebook-list small { color:var(--bf-shell-muted); white-space:nowrap }
.bf-panel-resizer { position:fixed; top:var(--bf-shell-top-height); bottom:14px; width:12px; z-index:32; cursor:col-resize; pointer-events:auto; touch-action:none; border-radius:6px }
.bf-panel-resizer-left { left:calc(var(--bf-shell-left) + 12px) }
.bf-panel-resizer-right { right:calc(var(--bf-shell-right) + 12px) }
.bf-panel-resizer:hover, .bf-panel-resizer:focus-visible, .bf-panel-resizer:active { background:color-mix(in srgb,var(--bf-shell-accent) 30%,transparent); outline:none }
.bf-quotation-progress { border:1px solid var(--bf-shell-border); border-radius:10px; padding:12px; margin-bottom:14px }
.bf-quotation-progress h3 { margin-top:0 }
@media (max-width: 1100px) {
  /* The bar used to be forced onto two rows here because eight buttons could not fit
     beside the name. Five can, so the second row — 48px across every screen in this
     band — goes back to the work. Below 760 it still wraps; see that block. */
  .bf-shell-top { flex-wrap:wrap; align-content:center; gap:6px }
  .bf-shell-top nav { overflow-x:auto; white-space:nowrap }
  .bf-shell-top .bf-notebook-title { flex:1 }
  body[data-bf-notebook] { --bf-shell-left: 235px; --bf-shell-right: 300px }
  body[data-bf-notebook] [data-slot="root"] > div { padding-right: 14px }
  .bf-shell-studio { display: none !important; z-index: 30; box-shadow: 0 10px 40px var(--bf-shell-scrim) }
  .bf-shell-studio[data-mobile-open=true] { display: flex !important }
  .bf-shell-studio .bf-mobile-close { display: block; border: 0; background: transparent; font-size: 11px }
}
@media (max-width: 760px) {
  body[data-bf-notebook] { --bf-shell-top-height: 92px }
  .bf-shell-brand { width:100% }
  body[data-bf-notebook] [data-slot="root"] > div { padding-left: 12px }
  .bf-shell-sources { display: none !important; width: min(340px, calc(100vw - 24px)); z-index: 30; box-shadow: 0 10px 40px var(--bf-shell-scrim) }
  .bf-shell-sources[data-mobile-open=true] { display: flex !important }
  .bf-shell-sources .bf-mobile-close { display: block; border: 0; background: transparent; font-size: 11px }
  .bf-shell-studio { width: min(380px, calc(100vw - 24px)) }
  .bf-shell-title, .bf-purpose-chip { display: none }
  .bf-shell-brand { gap: 6px }
  .bf-shell-top { padding: 0 12px }
  .bf-shell-top nav { gap: 4px; width:100%; overflow-x:auto; white-space:nowrap; padding-bottom:4px; }
  .bf-shell-top button { padding: 5px 7px; font-size: 11px }
}
/* Heading, one sentence, then the way out — stacked, because the way out is a real
   action now and an action squeezed beside the text reads as an afterthought. */
/* height/padding/overflow are reset on purpose: the notice carries .bf-state only to
   pick up the token scope, and .bf-state's own full-height, 160px-footed page padding
   wins on specificity — which blew this toast up into a near-full-height box. */
.bf-route-notice { position: fixed; z-index: 2147483000; top: 64px; left: 50%; transform: translateX(-50%); max-width: min(560px, calc(100vw - 32px)); height: auto; overflow: visible; padding: 12px 14px; display: grid; gap: 10px; box-shadow: 0 8px 24px var(--bf-shell-scrim) }
.bf-route-notice .bf-actions { margin: 0; justify-content: flex-end }
/* Feishu user-identity browser (docs/30). These lines and fills used to be white at low
   alpha, which assumed a dark page and left every hover state invisible in light mode. */
.bf-feishu { margin-top: 14px; border-top: 1px solid var(--bf-shell-border); padding-top: 10px }
.bf-feishu > summary { cursor: pointer; font-weight: 600 }
.bf-feishu-crumbs { display: flex; flex-wrap: wrap; gap: 4px; margin: 8px 0 }
.bf-feishu-crumbs button { border: 0; background: transparent; color: inherit; cursor: pointer; padding: 2px 4px; border-radius: 4px; opacity: 0.75 }
.bf-feishu-crumbs button[aria-current=true] { opacity: 1; font-weight: 600 }
.bf-feishu-crumbs button:hover { background: var(--bf-shell-hover) }
.bf-feishu-folder { display: block; width: 100%; text-align: left; border: 0; background: transparent; color: inherit; cursor: pointer; padding: 6px 8px; border-radius: 6px }
.bf-feishu-folder:hover { background: var(--bf-shell-hover) }
.bf-feishu-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px }
.bf-feishu-item[data-disabled=true] { opacity: 0.5 }
.bf-feishu-item select { margin-left: auto }
.bf-feishu-dept { margin-left: auto; border: 1px solid var(--bf-shell-border); background: transparent; color: inherit; cursor: pointer; padding: 3px 10px; border-radius: 999px; opacity: 0.75 }
.bf-feishu-dept[aria-pressed=true] { opacity: 1; font-weight: 600; background: var(--bf-shell-hover) }
.bf-feishu-go { display: flex; gap: 8px; align-items: center; margin-top: 10px }
.bf-feishu-upload-dialog .bf-feishu-browser, .bf-feishu-import .bf-feishu-browser { max-height: 46vh; overflow-y: auto }
.bf-feishu-mode { display: flex; gap: 6px; margin: 8px 0 }
.bf-feishu-mode button { border: 1px solid var(--bf-shell-border); background: transparent; color: inherit; cursor: pointer; padding: 3px 10px; border-radius: 999px; opacity: 0.75 }
.bf-feishu-mode button[aria-pressed=true] { opacity: 1; font-weight: 600; background: var(--bf-shell-hover) }
`
