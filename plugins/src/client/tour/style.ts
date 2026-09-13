export const tourStyle = `
.bf-tour-shade { position:fixed; z-index:2147483000; background:rgba(14,25,43,.54); pointer-events:auto; }
.bf-tour-ring { position:fixed; z-index:2147483001; border:2px solid #6ba3ff; border-radius:12px; box-shadow:0 0 0 4px rgba(97,155,255,.18); pointer-events:none; transition: top .15s ease,left .15s ease,width .15s ease,height .15s ease; }
.bf-tour-card { position:fixed; z-index:2147483002; box-sizing:border-box; color:var(--bf-shell-text,#242629); background:var(--bf-shell-pane,#fff); border:1px solid var(--bf-shell-border,#dbe0e7); border-radius:20px; box-shadow:0 24px 90px rgba(0,15,45,.3); padding:22px; overflow:auto; overscroll-behavior:contain; font-family:inherit; font-size:14px; line-height:1.55; pointer-events:auto; animation:bf-tour-in .16s ease-out; }
.bf-tour-card:focus { outline:none; }
.bf-tour-card h2 { font-size:22px;line-height:1.22;letter-spacing:-.025em;margin:12px 0; }
.bf-tour-card p { margin:10px 0;line-height:1.55;font-size:14px; }
.bf-tour-eyebrow { color:#4075be;font-size:10px;letter-spacing:.12em;font-weight:700;display:block;padding-right:25px; }
.bf-tour-close { position:absolute;right:12px;top:10px; }
.bf-tour-card button { font:inherit;cursor:pointer;border:1px solid var(--bf-shell-border,#dbe0e7);background:var(--bf-shell-pane,#fff);color:inherit;border-radius:9px;padding:8px 12px;min-height:38px; }
.bf-tour-card button:disabled { opacity:.45;cursor:default; }
.bf-tour-card button:focus-visible,.bf-tour-card summary:focus-visible { outline:3px solid #6ba3ff;outline-offset:3px; }
.bf-tour-card .bf-tour-primary { color:white;background:#315ea7;border-color:#315ea7; }
.bf-tour-card .bf-tour-close { border:0;padding:4px 10px;font-size:20px; }
.bf-tour-actions { display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:18px; }
.bf-tour-actions button:last-child { margin-left:auto; }
.bf-tour-task { padding:12px 14px;background:color-mix(in srgb,#709fed 11%,var(--bf-shell-pane,#fff));border-radius:12px;border-left:3px solid #739bdd;margin-top:14px; }
.bf-tour-task b,.bf-tour-expected b { font-size:10px;letter-spacing:.08em;display:block;margin-bottom:4px; }
.bf-tour-expected { color:var(--bf-shell-muted,#606773);margin-top:12px; }
.bf-tour-card details { font-size:12px;margin-top:12px;color:var(--bf-shell-muted,#606773); }
.bf-tour-card summary { cursor:pointer; }
.bf-tour-progress { height:4px;background:var(--bf-shell-border,#dbe0e7);border-radius:4px;margin-top:16px;overflow:hidden; }
.bf-tour-progress span { display:block;height:100%;background:#6794d8;transition:width .2s ease; }
.bf-tour-wait { font-size:12px!important;color:var(--bf-shell-muted,#606773); }
.bf-tour-mark { display:grid;place-items:center;width:48px;height:48px;border-radius:16px;background:linear-gradient(140deg,#e1ecff,#edf5f4);color:#315ea7;font-size:24px;margin-bottom:16px; }
.bf-tour-list { display:grid;gap:8px;margin-top:16px; }
.bf-tour-list button { text-align:left; }
.bf-tour-storage { color:var(--bf-shell-muted,#606773);font-size:11px!important; }
body[data-bf-tour-active] [data-tour-id]:focus-visible { outline:3px solid #6898e4;outline-offset:3px; }
.bf-master-cell { white-space:nowrap; border:0!important;padding:0!important;background:transparent!important;color:inherit!important;font:inherit!important;text-align:inherit;cursor:pointer;text-decoration:underline;text-decoration-style:dotted;text-underline-offset:4px; }
.bf-cell-evidence { border:1px solid var(--bf-shell-border);border-radius:12px;padding:14px;margin:12px 0;overflow-wrap:anywhere; }
.bf-master-questions { margin:12px 0; }
.bf-master-questions > summary { cursor:pointer;padding:10px;border-radius:10px;background:var(--bf-shell-bg); }
@keyframes bf-tour-in { from { opacity:0;transform:translateY(4px) } to { opacity:1;transform:none } }
@media(prefers-reduced-motion:reduce) { .bf-tour-card,.bf-tour-ring,.bf-tour-progress span {animation:none;transition:none} }
@media(max-width:760px) { .bf-tour-card {padding:16px;border-radius:16px} .bf-tour-card h2 {font-size:19px} .bf-tour-card p {font-size:13px} .bf-tour-actions {position:sticky;bottom:-16px;background:var(--bf-shell-pane,#fff);padding:8px 0} }
`
