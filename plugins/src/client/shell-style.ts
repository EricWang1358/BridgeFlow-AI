/** rc.1's public data-slot style anchors retain all native occupants and stores.
 * No private CSS module names, DOM reparenting, second React root or DSH fork. */
export const shellStyle = `
body[data-bf-notebook] {
  --bf-shell-top-height: 52px; --bf-shell-bg: #eef1f5; --bf-shell-pane: #fff; --bf-shell-border: #e1e5eb;
  --bf-shell-text: #1f2328; --bf-shell-muted: #5f6773; --bf-shell-accent: #2f6bd8; --bf-shell-accent-soft: #eaf1fd;
  --bf-shell-shadow: 0 1px 2px #0f172a0a, 0 0 0 1px #0f172a0d;
  --bf-shell-font: Inter, system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', 'PingFang SC',
    'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans SC', 'Noto Sans CJK SC', sans-serif;
  --bf-shell-left: clamp(240px, 25vw, 440px); --bf-shell-right: clamp(280px, 26vw, 460px);
}
body[data-bf-notebook][data-ds-dark-theme] {
  --bf-shell-bg: #16181c; --bf-shell-pane: #1f2328; --bf-shell-border: #30353c;
  --bf-shell-text: #e6e8eb; --bf-shell-muted: #a2a9b3; --bf-shell-accent: #8fb3f5; --bf-shell-accent-soft: #22324c;
  --bf-shell-shadow: 0 0 0 1px #ffffff0d, 0 1px 3px #0006;
}
/* AppFrame wrappers contain public slot anchors; native detail transitions stay. */
body[data-bf-notebook] [data-slot="root"] > div {
  grid-template-columns: 0 minmax(0, 1fr) 0 !important;
  padding: var(--bf-shell-top-height) calc(var(--bf-shell-right) + 24px) 14px calc(var(--bf-shell-left) + 24px);
  box-sizing: border-box; background: var(--bf-shell-bg);
}
body[data-bf-notebook] [data-slot="root"] > div > [data-side] { display: none }
body[data-bf-notebook] [data-slot="root"] > div > div:has(> [data-slot="conversation"]) {
  grid-column: 2; grid-row: 1; border-radius: 16px; background: var(--bf-shell-pane); padding-top: 40px; position: relative;
  box-shadow: var(--bf-shell-shadow);
}
body[data-bf-notebook] [data-slot="root"] > div > div:has(> [data-slot="conversation"])::before {
  content: var(--bf-chat-label, 'Chat'); position: absolute; left: 16px; top: 11px; color: var(--bf-shell-text); font: 600 13px/20px var(--bf-shell-font); letter-spacing: -.005em;
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
.bf-welcome > span { display: inline-grid; place-items: center; width: 48px; height: 48px; border-radius: 14px; color: var(--bf-shell-accent); background: var(--bf-shell-accent-soft) }
.bf-welcome h2 { margin: 16px 0 10px; font-size: 24px; line-height: 1.35; font-weight: 600; letter-spacing: -.02em }
.bf-welcome p { margin: 0; color: var(--bf-shell-muted); font-size: 13px; line-height: 1.8 }
body[data-bf-notebook] .bf-hero { box-sizing: border-box; width: 100%; background: transparent; border: 0; box-shadow: none; padding: 8px 30px; margin: 0 0 24px }
body[data-bf-notebook] .bf-hero > h3, body[data-bf-notebook] .bf-hero > p { display: none }
.bf-hero details { margin: 14px 0; font-size: 12px; color: var(--bf-shell-muted) }
.bf-flow-title { margin: 18px 0 12px; font-size: 12px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--bf-shell-muted) }
.bf-loaded-summary { max-width: 520px; margin: 0 0 18px; color: var(--bf-shell-muted); font-size: 13px; line-height: 1.6 }
.bf-flow { list-style: none; margin: 0 0 22px; padding: 0; counter-reset: bf-flow; max-width: 520px }
.bf-flow > li { counter-increment: bf-flow; position: relative; display: grid; grid-template-columns: 28px minmax(0, 1fr); column-gap: 14px; padding: 0 0 18px; color: var(--bf-shell-text) }
.bf-flow > li::before { content: counter(bf-flow); grid-column: 1; grid-row: 1 / span 3; display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; font-size: 12px; font-weight: 700; background: var(--bf-flow-tone-soft); color: var(--bf-flow-tone) }
.bf-flow > li:not(:last-child)::after { content: ''; position: absolute; left: 13px; top: 32px; bottom: 4px; width: 2px; border-radius: 1px; background: var(--bf-shell-border); transform-origin: top }
.bf-flow > li { --bf-flow-tone: #5f6b7a; --bf-flow-tone-soft: #eef1f5 }
.bf-flow > li[data-actor=agents] { --bf-flow-tone: #2f6bd8; --bf-flow-tone-soft: #e8f0fd }
.bf-flow > li[data-actor=person] { --bf-flow-tone: #1c7a4a; --bf-flow-tone-soft: #e6f4ec }
body[data-ds-dark-theme] .bf-flow > li { --bf-flow-tone: #b3bdca; --bf-flow-tone-soft: #2c323a }
body[data-ds-dark-theme] .bf-flow > li[data-actor=agents] { --bf-flow-tone: #8fb3f5; --bf-flow-tone-soft: #243452 }
body[data-ds-dark-theme] .bf-flow > li[data-actor=person] { --bf-flow-tone: #7fd1a3; --bf-flow-tone-soft: #1f3a2c }
.bf-flow > li > * { grid-column: 2 }
.bf-flow-actor { justify-self: start; font-size: 10px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; color: var(--bf-flow-tone); margin: 1px 0 2px }
.bf-flow > li > b { font-size: 14px; font-weight: 600; line-height: 1.35 }
.bf-flow > li > span:last-child { font-size: 12px; line-height: 1.55; color: var(--bf-shell-muted) }
body[data-bf-notebook] .bf-hero .bf-actions { display: flex; flex-wrap: wrap; gap: 8px }
body[data-bf-notebook] .bf-hero button { background: var(--bf-shell-pane) !important; color: var(--bf-shell-text) !important; border: 1px solid var(--bf-shell-border); border-radius: 24px; padding: 7px 14px; width: auto; font-size: 12px; font-weight: 500; box-shadow: 0 1px 2px #0f172a0a }
body[data-bf-notebook] .bf-hero button:hover { border-color: color-mix(in srgb, var(--bf-shell-accent) 45%, var(--bf-shell-border)); color: var(--bf-shell-accent) !important }
body[data-bf-hide-sources] [data-slot="root"] > div { padding-left: 12px }
body[data-bf-hide-studio] [data-slot="root"] > div { padding-right: 12px }
body[data-bf-hide-sources] .bf-shell-sources, body[data-bf-hide-studio] .bf-shell-studio { display: none !important }
/* Navigation remains a native drawer, including settings and workspaces. */
body[data-bf-notebook] [data-slot="root"] > div > div:has(> [data-slot="sidebar"]) {
  position: fixed; left: 12px; top: var(--bf-shell-top-height); bottom: 14px; width: 300px; z-index: 45;
  border-radius: 16px; box-shadow: 0 12px 40px #0004; display: none;
}
body[data-bf-notebook][data-bf-nav] [data-slot="root"] > div > div:has(> [data-slot="sidebar"]) { display: block }
body[data-bf-notebook] [data-slot="root"] > div > div:has(> [data-slot="details"]) {
  position: fixed; right: 12px; top: var(--bf-shell-top-height); bottom: 14px; width: var(--bf-shell-right);
  z-index: 35; background: var(--bf-shell-pane); border-radius: 16px;
}
body[data-bf-notebook] [data-slot="root"] > [data-details-collapsed] > div:has(> [data-slot="details"]) { width: 0; border: 0 }
.bf-shell-top { position: fixed; inset: 0 0 auto; height: var(--bf-shell-top-height); padding: 0 18px; display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--bf-shell-text); pointer-events: auto; font-family: var(--bf-shell-font); -webkit-font-smoothing: antialiased }
.bf-shell-brand { display: flex; align-items: center; gap: 12px; min-width: 0 }
.bf-shell-brand > span:first-child { display: grid; place-items: center; width: 28px; height: 28px; background: linear-gradient(135deg, #3d7be6, #2554b8); color: #fff; border-radius: 8px; font-size: 14px; font-weight: 700; box-shadow: 0 1px 2px #1d4ed840, inset 0 1px 0 #ffffff33 }
.bf-shell-brand strong { font-size: 16px; font-weight: 650; letter-spacing: -.015em }
.bf-shell-title { font-size: 13px; color: var(--bf-shell-muted) }
.bf-shell-top nav { display: flex; align-items: center; gap: 14px }
/* Three kinds of control, three weights: notebook actions are quiet text, the pane
   switches read as one segmented control, and Help keeps its own outline. */
.bf-top-group { display: flex; align-items: center; gap: 2px }
.bf-top-group[data-kind=notebook] button { border-color: transparent; color: var(--bf-shell-muted) }
.bf-top-group[data-kind=notebook] button:hover:not(:disabled) { background: color-mix(in srgb, var(--bf-shell-text) 7%, transparent); color: var(--bf-shell-text) }
.bf-top-group[data-kind=panes] { border: 1px solid var(--bf-shell-border); border-radius: 24px; padding: 2px; background: var(--bf-shell-pane); box-shadow: 0 1px 2px #0f172a0a }
.bf-top-group[data-kind=panes] button { border-color: transparent }
.bf-shell-top button, .bf-shell-pane button { font: inherit; cursor: pointer; color: inherit }
.bf-shell-top button { border: 1px solid var(--bf-shell-border); background: transparent; border-radius: 24px; padding: 5px 12px; font-size: 12px; font-weight: 500; white-space: nowrap; transition: background .12s, color .12s, border-color .12s }
/* A 1280-wide laptop or projector: labels stay on one line and the groups tighten
   instead of wrapping "Create notebook" into two lines. */
@media (max-width: 1400px) {
  .bf-shell-top nav { gap: 8px }
  .bf-shell-top button { padding: 4px 9px }
  .bf-shell-brand { gap: 8px }
}
.bf-shell-pane.bf-state {
  position: fixed; top: var(--bf-shell-top-height); bottom: 14px; height: auto; margin: 0; border-radius: 16px; padding: 0;
  display: flex; flex-direction: column; overflow: hidden; pointer-events: auto;
  background: var(--bf-shell-pane); color: var(--bf-shell-text); font-size: 13px; box-shadow: var(--bf-shell-shadow);
  --bf-surface: var(--bf-shell-pane); --bf-surface-2: var(--bf-shell-bg); --bf-line: var(--bf-shell-border);
  --bf-text: var(--bf-shell-text); --bf-muted: var(--bf-shell-muted);
}
.bf-shell-sources { left: 12px; width: var(--bf-shell-left) }
.bf-shell-studio { right: 12px; width: var(--bf-shell-right) }
.bf-shell-pane > header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--bf-shell-border); height: 40px; flex-shrink: 0; padding: 0 14px }
.bf-shell-pane > header h2 { font-size: 13px; font-weight: 600; letter-spacing: -.005em }
.bf-shell-scroll { padding: 16px 18px; flex: 1; min-height: 0; overflow: auto }
.bf-add-source { width: 100%; border: 1px dashed color-mix(in srgb, var(--bf-shell-accent) 45%, var(--bf-shell-border)) !important; border-radius: 10px !important; background: color-mix(in srgb, var(--bf-shell-accent-soft) 60%, transparent) !important; color: var(--bf-shell-accent) !important; padding: 9px !important; font-size: 13px !important; font-weight: 600 !important; box-shadow: none !important }
.bf-add-source:hover { background: var(--bf-shell-accent-soft) !important }
.bf-resource-list button:hover, .bf-artifact:hover { background: color-mix(in srgb, var(--bf-shell-text) 5%, transparent) }
.bf-source-batch { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 20px 0 12px }
.bf-source-batch code { width: 100%; font-size: 10px; overflow-wrap: anywhere; color: var(--bf-shell-muted) }
.bf-source-batch button { background: transparent; border: 0; font-size: 11px; margin-left: auto }
.bf-resource-list { list-style: none; padding: 0; margin: 0 }
.bf-resource-list button { border: 0; border-radius: 10px; background: transparent; box-shadow: none; display: flex; gap: 10px; align-items: center; padding: 10px 6px; margin-bottom: 2px; text-align: left; width: 100% }
.bf-resource-list button > span:last-child, .bf-artifact > span:last-child { color: var(--bf-shell-muted); opacity: .7 }
.bf-resource-list button > span:nth-child(2), .bf-artifact > span:nth-child(2) { flex: 1; min-width: 0 }
.bf-resource-list strong, .bf-artifact strong { display: block; font-size: 13px; font-weight: 500; overflow-wrap: anywhere }
.bf-resource-list small, .bf-artifact small { display: block; font-size: 11px; color: var(--bf-shell-muted); margin-top: 3px }
.bf-resource-list button[aria-pressed=true], .bf-artifact[aria-pressed=true] { background: var(--bf-shell-accent-soft); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--bf-shell-accent) 35%, transparent) }
/* Icon tiles: one tinted square per row, so files and outputs line up as a list. */
.bf-file-icon, .bf-artifact > span:first-child { display: grid; place-items: center; flex: none; width: 30px; height: 30px; border-radius: 8px; color: var(--bf-shell-muted); background: color-mix(in srgb, var(--bf-shell-text) 5%, transparent) }
.bf-resource-list button[aria-pressed=true] .bf-file-icon, .bf-artifact[aria-pressed=true] > span:first-child { color: var(--bf-shell-accent); background: var(--bf-shell-pane) }
.bf-shell-empty { min-height: 320px; height: 48vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; color: var(--bf-shell-muted); font-size: 12px }
.bf-shell-empty > span { display: grid; place-items: center; width: 56px; height: 56px; border-radius: 16px; margin-bottom: 14px; color: var(--bf-shell-accent); background: var(--bf-shell-accent-soft) }
.bf-shell-empty p { max-width: 260px }
.bf-existing { color: var(--bf-shell-muted); font-size: 12px; margin-top: 20px }
.bf-existing form { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px }
.bf-existing input { min-width: 0; width: 100%; background: transparent; color: inherit; border: 1px solid var(--bf-shell-border); border-radius: 8px; padding: 8px }
.bf-studio-tools { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px }
/* Four destinations, one visual language: an icon line, a name, and the count that matters.
   Five different hues made the pane look like a sticker sheet and said nothing; the tone now
   only marks which one is open. */
.bf-studio-tools button {
  display: grid; grid-template-columns: auto 1fr auto; grid-template-rows: auto auto;
  gap: 8px 8px; align-items: center; text-align: left; min-height: 78px;
  border: 1px solid var(--bf-shell-border) !important; box-shadow: 0 1px 2px #0f172a0a !important;
  border-radius: 12px !important; padding: 12px !important; font-size: 13px;
  background: var(--bf-shell-pane) !important;
  transition: border-color .12s, box-shadow .12s, background .12s;
}
.bf-studio-tools button:hover { border-color: color-mix(in srgb, var(--bf-shell-accent) 40%, var(--bf-shell-border)) !important; box-shadow: 0 2px 8px #0f172a12 !important }
/* The icon sits in a tinted square: a quiet mark of where each entry leads. */
.bf-studio-tools button > span:first-child { grid-row: 1; display: grid; place-items: center; width: 30px; height: 30px; border-radius: 8px; color: var(--bf-shell-accent); background: var(--bf-shell-accent-soft) }
.bf-studio-tools button > span:nth-child(2) { grid-row: 2; grid-column: 1 / -1; font-size: 13px; font-weight: 600; letter-spacing: -.005em }
/* The chevron sits on the icon line, so a long name can never push it onto its own row. */
.bf-studio-tools button > span:last-child { grid-row: 1; grid-column: 3; display: grid; color: var(--bf-shell-muted); opacity: .6 }
.bf-studio-tools button .bf-badge { grid-row: 1; grid-column: 2; justify-self: end; margin: 0 }
.bf-studio-tools button[data-span=all] { grid-column: 1 / -1; min-height: 0; grid-template-rows: auto }
.bf-studio-tools button[data-span=all] > span:nth-child(2) { grid-row: 1; grid-column: 2 }
.bf-studio-tools .bf-studio-group { grid-column: 1 / -1; margin: 14px 2px 2px; font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--bf-shell-muted) }
.bf-studio-tools button[data-secondary=true] {
  grid-column: 1 / -1; grid-template-columns: auto 1fr auto; grid-template-rows: auto;
  min-height: 0; padding: 8px 12px 8px 8px !important;
}
.bf-studio-tools button[data-secondary=true] > span:first-child { grid-row: 1; width: 26px; height: 26px; border-radius: 7px; color: var(--bf-shell-muted); background: color-mix(in srgb, var(--bf-shell-text) 5%, transparent) }
.bf-studio-tools button[data-secondary=true] > span:nth-child(2) { grid-row: 1; grid-column: 2; justify-self: start; font-weight: 400 }
.bf-studio-tools button[data-secondary=true] > span:last-child { grid-row: 1 }
.bf-shell-pane button:disabled { opacity: .5; cursor: default }
.bf-artifacts { border-top: 1px solid var(--bf-shell-border); margin-top: 18px; padding-top: 16px }
.bf-artifacts > header, .bf-inline-preview > header { display: flex; align-items: center; gap: 8px; margin-bottom: 14px }
.bf-artifacts > header h3, .bf-inline-preview > header h3 { flex: 1; margin: 0; font-size: 13px }
.bf-artifacts > header button, .bf-inline-preview > header button { background: transparent; border: 1px solid var(--bf-shell-border); border-radius: 16px; padding: 4px 10px; font-size: 11px; box-shadow: none }
.bf-artifact { display: flex; align-items: center; gap: 12px; border: 0 !important; border-radius: 10px !important; padding: 8px !important; text-align: left; width: 100%; background: transparent; box-shadow: none !important; margin-bottom: 4px }
.bf-artifact .bf-chip { margin-top: 8px }
.bf-inline-preview { margin-top: 22px; border-top: 1px solid var(--bf-shell-border); padding-top: 16px }
.bf-source-table { overflow: auto; max-height: 55vh; border: 1px solid var(--bf-shell-border); border-radius: 10px }
.bf-source-table table { border-collapse: collapse; white-space: nowrap; font-size: 12px; width: 100% }
.bf-source-table th, .bf-source-table td { padding: 8px 12px; border-bottom: 1px solid var(--bf-shell-border); text-align: left; max-width: 480px; overflow: hidden; text-overflow: ellipsis }
.bf-source-table th { font-weight: 600; color: var(--bf-shell-muted) }
.bf-source-table thead { position: sticky; top: 0; background: color-mix(in srgb, var(--bf-shell-text) 3%, var(--bf-shell-pane)) }
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
.bf-shell-top button:focus-visible, .bf-shell-pane button:focus-visible { outline: 2px solid #7ea8ef; outline-offset: 3px }
.bf-shell-top button[aria-expanded=true], .bf-shell-top button[aria-pressed=true] { background: var(--bf-shell-accent-soft); color: #1f4f9e; border-color: color-mix(in srgb, var(--bf-shell-accent) 40%, transparent) }
body[data-ds-dark-theme] .bf-shell-top button[aria-expanded=true], body[data-ds-dark-theme] .bf-shell-top button[aria-pressed=true] { background: #2a3d5e; color: #e2edff; border-color: #5d7fb5 }
.bf-shell-pane .bf-studio-tools button[aria-pressed=true] {
  border-color: color-mix(in srgb, var(--bf-shell-accent) 65%, transparent) !important;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--bf-shell-accent) 16%, transparent) !important;
  background: color-mix(in srgb, var(--bf-shell-accent-soft) 55%, var(--bf-shell-pane)) !important;
}
.bf-shell-pane .bf-studio-tools button[aria-pressed=true] > span:first-child { color: #fff; background: var(--bf-shell-accent) }
body[data-ds-dark-theme] .bf-shell-pane .bf-studio-tools button[aria-pressed=true] > span:first-child { color: #0b1420 }
.bf-shell-top .bf-notebook-title { width: clamp(120px, 15vw, 260px); min-width: 70px; background: transparent; border: 1px solid transparent; border-radius: 6px; color: inherit; padding: 5px; font: inherit; font-size: 13px }
.bf-notebook-title:hover, .bf-notebook-title:focus { border-color: var(--bf-shell-border) }
.bf-save-state { font-size: 11px; white-space: nowrap; color: var(--bf-shell-muted) }
.bf-save-state[data-dirty=true] { color: #986711 }
body[data-ds-dark-theme] .bf-save-state[data-dirty=true] { color: #dfbd76 }
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
.bf-panel.bf-notebook-dialog .bf-notebook-list button:hover, .bf-panel.bf-notebook-dialog .bf-notebook-list button[aria-current=page] { background:color-mix(in srgb,#7ea8ef 18%,transparent) }
.bf-panel.bf-notebook-dialog .bf-notebook-list small { color:var(--bf-shell-muted); white-space:nowrap }
.bf-panel-resizer { position:fixed; top:var(--bf-shell-top-height); bottom:14px; width:12px; z-index:32; cursor:col-resize; pointer-events:auto; touch-action:none; border-radius:6px }
.bf-panel-resizer-left { left:calc(var(--bf-shell-left) + 12px) }
.bf-panel-resizer-right { right:calc(var(--bf-shell-right) + 12px) }
.bf-panel-resizer:hover, .bf-panel-resizer:focus-visible, .bf-panel-resizer:active { background:color-mix(in srgb,#7ea8ef 30%,transparent); outline:none }
.bf-quotation-progress { border:1px solid var(--bf-shell-border); border-radius:10px; padding:12px; margin-bottom:14px }
.bf-quotation-progress h3 { margin-top:0 }
@media (max-width: 1100px) {
  .bf-shell-top { flex-wrap:wrap; align-content:center; gap:6px }
  .bf-shell-top nav { width:100%; overflow-x:auto; white-space:nowrap }
  .bf-shell-brand { width:100% }
  .bf-shell-top .bf-notebook-title { flex:1 }
  body[data-bf-notebook] { --bf-shell-top-height: 100px; --bf-shell-left: 235px; --bf-shell-right: 300px }
  body[data-bf-notebook] [data-slot="root"] > div { padding-right: 14px }
  .bf-shell-studio { display: none !important; z-index: 30; box-shadow: 0 10px 40px #0005 }
  .bf-shell-studio[data-mobile-open=true] { display: flex !important }
  .bf-shell-studio .bf-mobile-close { display: block; border: 0; background: transparent; font-size: 11px }
}
@media (max-width: 760px) {
  body[data-bf-notebook] [data-slot="root"] > div { padding-left: 12px }
  .bf-shell-sources { display: none !important; width: min(340px, calc(100vw - 24px)); z-index: 30; box-shadow: 0 10px 40px #0005 }
  .bf-shell-sources[data-mobile-open=true] { display: flex !important }
  .bf-shell-sources .bf-mobile-close { display: block; border: 0; background: transparent; font-size: 11px }
  .bf-shell-studio { width: min(380px, calc(100vw - 24px)) }
  .bf-shell-title { display: none }
  .bf-shell-brand strong { font-size: 14px }
  .bf-shell-brand { gap: 7px }
  .bf-shell-top { padding: 0 12px }
  .bf-shell-top nav { gap: 4px; width:100%; overflow-x:auto; white-space:nowrap; padding-bottom:4px; }
  .bf-top-group { flex-shrink: 0 }
  .bf-shell-top button { padding: 5px 7px; font-size: 11px }
}
.bf-route-notice.bf-state { height: auto; min-height: 0; padding: 14px 18px; max-height: calc(100vh - 96px); overflow: auto }
.bf-route-notice { position: fixed; z-index: 2147483000; top: 64px; left: 50%; transform: translateX(-50%); max-width: min(560px, calc(100vw - 32px)); display: flex; gap: 12px; align-items: center; box-shadow: 0 8px 24px rgb(0 0 0 / 30%) }
/* Feishu user-identity browser (docs/30) */
.bf-feishu { margin-top: 14px; border-top: 1px solid #ffffff1a; padding-top: 10px }
.bf-feishu > summary { cursor: pointer; font-weight: 600 }
.bf-feishu-crumbs { display: flex; flex-wrap: wrap; gap: 4px; margin: 8px 0 }
.bf-feishu-crumbs button { border: 0; background: transparent; color: inherit; cursor: pointer; padding: 2px 4px; border-radius: 4px; opacity: 0.75 }
.bf-feishu-crumbs button[aria-current=true] { opacity: 1; font-weight: 600 }
.bf-feishu-crumbs button:hover { background: #ffffff14 }
.bf-feishu-folder { display: flex; align-items: center; gap: 6px; width: 100%; text-align: left; border: 0; background: transparent; color: inherit; cursor: pointer; padding: 6px 8px; border-radius: 6px }
.bf-feishu-folder:hover { background: #ffffff14 }
.bf-feishu-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px }
.bf-feishu-up { display: inline-flex; align-items: center; gap: 4px }
.bf-feishu-item[data-disabled=true] { opacity: 0.5 }
.bf-feishu-item select { margin-left: auto }
.bf-feishu-go { display: flex; gap: 8px; align-items: center; margin-top: 10px }
.bf-feishu-upload-dialog .bf-feishu-browser, .bf-feishu-import .bf-feishu-browser { max-height: 46vh; overflow-y: auto }
.bf-feishu-mode { display: flex; gap: 6px; margin: 8px 0 }
.bf-feishu-mode button { border: 1px solid #ffffff2a; background: transparent; color: inherit; cursor: pointer; padding: 3px 10px; border-radius: 999px; opacity: 0.75 }
.bf-feishu-mode button[aria-pressed=true] { opacity: 1; font-weight: 600; background: #ffffff14 }
/* The way out of a folder, said out loud (#244): crumbs navigated but read as labels. */
.bf-feishu-up { border: 1px solid #ffffff2a; border-radius: 999px; padding: 2px 10px !important; opacity: 1 !important }
.bf-feishu-up:hover { background: #ffffff1f }
/* Every pick visible and removable wherever the browser is (#244): a pick used to
   live only on its own row, in its own folder. */
.bf-feishu-chosen { border: 1px solid #ffffff1a; border-radius: 10px; padding: 8px 10px; margin-top: 10px }
.bf-feishu-chosen h4 { margin: 0 0 4px; font-size: 13px }
.bf-feishu-chosen ul { list-style: none; padding: 0; margin: 0 }
.bf-feishu-chosen li { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 4px 0 }
.bf-feishu-chosen-name { min-width: 0; overflow-wrap: anywhere }
.bf-feishu-chosen select, .bf-feishu-chosen input[type="number"] { max-width: 12em }
.bf-feishu-remove { border: 0; background: transparent; color: inherit; cursor: pointer; opacity: 0.6; padding: 2px 6px; border-radius: 6px; margin-left: auto }
.bf-feishu-remove:hover { opacity: 1; background: #ffffff14 }
`
