"""HTML pages for the portal: one layout, a few small views.

No framework and no static files on purpose: the portal is an edge service,
and its pages must render even when everything downstream is down. All user
input passes through html.escape — a name from Feishu is data, never markup.

The look follows ``docs/design/01-portal.html`` (screens P01–P06): the same
Claude Design System purpose tokens the app itself uses, so signing in stops
looking like a different product. Dark mode swaps token values only — there is
no second stylesheet, which is why every rule below reads --surface-* /
--text-* / --bg-* / --border-* / --fill-* and never a literal colour.
"""

from __future__ import annotations

import html

BRAND = "BridgeFlow AI"

_CSS = """
:root {
  color-scheme: light dark;
  --surface-1: #f2f1ea; --surface-2: #ffffff;
  --text-primary: #191917; --text-secondary: #5f5e5a; --text-muted: #8a8880;
  --text-accent: #185fa5; --text-success: #3b6d11; --text-warning: #854f0b; --text-danger: #a32d2d;
  --bg-accent: #e6f1fb; --bg-warning: #faeeda; --bg-danger: #fcebeb; --bg-neutral: #f1efe8;
  --border: rgba(25, 25, 23, .10); --border-strong: rgba(25, 25, 23, .17);
  --border-stronger: rgba(25, 25, 23, .34);
  --border-warning: #ef9f27; --border-danger: #f09595;
  --fill-accent: #378add; --fill-brand: #c96442; --on-accent: #ffffff;
  --radius: 8px; --radius-card: 12px;
  --font-sans: "Anthropic Sans", ui-sans-serif, -apple-system, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, "Cascadia Mono", monospace;
  --shadow-panel: 0 1px 2px rgba(25, 25, 23, .06), 0 12px 32px rgba(25, 25, 23, .10);
}
@media (prefers-color-scheme: dark) {
  :root {
    --surface-1: #262624; --surface-2: #30302e;
    --text-primary: #f5f4ee; --text-secondary: #b4b2a9; --text-muted: #8a8880;
    --text-accent: #85b7eb; --text-success: #97c459; --text-warning: #ef9f27; --text-danger: #f09595;
    --bg-accent: #0c447c; --bg-warning: #633806; --bg-danger: #791f1f; --bg-neutral: #3a3a38;
    --border: rgba(255, 255, 255, .11); --border-strong: rgba(255, 255, 255, .19);
    --border-stronger: rgba(255, 255, 255, .36);
    --border-warning: #854f0b; --border-danger: #a32d2d;
    --shadow-panel: 0 1px 2px rgba(0, 0, 0, .3), 0 14px 36px rgba(0, 0, 0, .38);
  }
}

* { box-sizing: border-box; margin: 0 }
body { min-height: 100vh; display: grid; place-items: center; padding: 24px;
  background: var(--surface-1); color: var(--text-primary);
  font-family: var(--font-sans); font-size: 15px; line-height: 1.7;
  font-variant-numeric: tabular-nums; }
:focus-visible { outline: 2px solid var(--fill-accent); outline-offset: 2px }

.card { width: 100%; max-width: 372px; padding: 30px 28px;
  background: var(--surface-2); border: .5px solid var(--border);
  border-radius: var(--radius-card); box-shadow: var(--shadow-panel); }
.card.center { text-align: center }
.brand { font-size: 19px; font-weight: 500; letter-spacing: -.01em }
.brand span { color: var(--fill-brand) }
.sub { font-size: 12.5px; color: var(--text-secondary); margin-top: 3px }
.sec { margin: 22px 0 10px; font-size: 11px; letter-spacing: .1em;
  color: var(--text-muted); text-transform: uppercase; }
.muted { color: var(--text-secondary); font-size: 13px }
.hint { color: var(--text-muted); font-size: 12px; line-height: 1.6 }
.hint.center { text-align: center; margin-top: 12px }
.act { margin-top: 14px }

.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  border: .5px solid var(--border-strong); border-radius: var(--radius);
  background: var(--surface-2); color: var(--text-primary);
  padding: 6px 13px; font: inherit; font-size: 13.5px; text-decoration: none; cursor: pointer; }
.btn:hover { border-color: var(--border-stronger) }
.btn.full { width: 100%; }
.btn.lg { padding: 11px 16px; gap: 10px; font-size: 14.5px; font-weight: 500 }
.btn.primary { background: var(--fill-accent); border-color: var(--fill-accent);
  color: var(--on-accent); font-weight: 500 }
.btn.primary:hover { filter: brightness(.94) }
.btn.quiet { border-color: transparent; background: transparent;
  color: var(--text-secondary); padding: 6px 8px }
.btn.quiet:hover { color: var(--text-primary) }
.btn svg { flex: none }

a.enter { display: flex; align-items: center; justify-content: space-between; gap: 10px;
  margin-top: 8px; padding: 10px 14px; border: .5px solid var(--border-strong);
  border-radius: var(--radius); font-size: 13.5px;
  color: var(--text-primary); text-decoration: none; }
a.enter:hover { border-color: var(--border-stronger) }
a.enter::after { content: "→"; color: var(--text-accent) }

.user { display: flex; align-items: center; gap: 12px; margin-top: 22px }
.avatar { width: 44px; height: 44px; border-radius: 50%; flex: none; overflow: hidden;
  display: grid; place-items: center; font-size: 15px; font-weight: 500;
  background: var(--bg-accent); color: var(--text-accent); }
.avatar img { width: 100%; height: 100%; object-fit: cover }
.user .who { min-width: 0 }
.user .name { font-weight: 500 }
.logout { margin-top: 20px; text-align: center }

.callout { margin-top: 18px; padding: 11px 14px; background: var(--surface-1);
  border: .5px solid var(--border); border-left: 3px solid var(--text-muted); }
.callout h4 { font-size: 13px; font-weight: 500; margin-bottom: 2px }
.callout p { font-size: 13px; line-height: 1.6; color: inherit }
.callout.warn { border-left-color: var(--border-warning); background: var(--bg-warning);
  color: var(--text-warning) }
.callout.bad { border-left-color: var(--border-danger); background: var(--bg-danger);
  color: var(--text-danger) }

details { margin-top: 14px }
summary { cursor: pointer }
.checks { margin-top: 8px; font-family: var(--font-mono); font-size: 11.5px;
  color: var(--text-secondary); line-height: 1.85 }
.checks div { display: flex; justify-content: space-between; gap: 12px }
.checks .ok { color: var(--text-success) }
.checks .missing { color: var(--text-danger) }

.bar { height: 6px; max-width: 180px; margin: 14px auto 0; border-radius: 3px;
  background: var(--bg-neutral); overflow: hidden }
.bar > span { display: block; height: 100%; width: 65%; background: var(--fill-accent) }
.detail { margin-top: 8px; font-size: 13px; color: var(--text-secondary); word-break: break-all }
"""

#: The official Feishu mark, taken verbatim (coordinates rounded to 0.01) from
#: the logo published by the Feishu open platform. Its colours are the brand's
#: own, so the sign-in button stays a light surface rather than a filled accent
#: — a coloured mark on a blue fill muddies into the background.
_FEISHU_LOGO = (
    '<svg width="20" height="18" viewBox="0 0 36 32" fill="none" aria-hidden="true" focusable="false">'
    '<path d="M16.93 16.54L16.99 16.48C17.04 16.43 17.08 16.39 17.12 16.35L17.21 16.26L17.48 15.99L17.85'
    ' 15.63L18.16 15.32L18.46 15.03L18.77 14.72L19.05 14.44L19.45 14.05C19.52 13.98 19.6 13.91 19.68 13.84C19.82'
    ' 13.7 19.97 13.58 20.12 13.46C20.26 13.35 20.4 13.24 20.54 13.14C20.75 12.99 20.96 12.86 21.17 12.73C21.39'
    ' 12.6 21.6 12.49 21.82 12.38C22.03 12.28 22.25 12.19 22.46 12.1C22.58 12.06 22.71 12.01 22.83 11.97C22.89'
    ' 11.95 22.95 11.93 23.02 11.91C22.47 9.75 21.46 7.74 20.07 6.01C19.94 5.84 19.77 5.71 19.58 5.62C19.39 5.52'
    ' 19.18 5.48 18.97 5.48L7.61 5.48C7.56 5.48 7.52 5.49 7.48 5.52C7.44 5.54 7.42 5.58 7.4 5.62C7.39 5.67 7.39'
    ' 5.71 7.4 5.76C7.42 5.8 7.44 5.83 7.48 5.86C11.36 8.7 14.57 12.36 16.9 16.57L16.93 16.54Z" fill="#00D6B9"/>'
    '<path d="M26.06 18.52L26.06 18.53L26.07 18.52L26.12 18.42C26.1 18.45 26.08 18.49 26.06 18.52Z"'
    ' fill="#133C92"/>'
    '<path d="M26.31 18.06L26.32 18.03L26.33 18.02L26.31 18.06Z" fill="#133C92"/>'
    '<path d="M29.65 12.41C27.67 11.44 25.4 11.23 23.28 11.83C23.19 11.85 23.1 11.88 23.02 11.91C22.95 11.93'
    ' 22.89 11.95 22.83 11.97C22.71 12.01 22.58 12.06 22.46 12.1C22.25 12.19 22.03 12.28 21.82 12.38C21.6 12.49'
    ' 21.39 12.6 21.17 12.73C20.96 12.86 20.75 12.99 20.54 13.14C20.4 13.24 20.26 13.35 20.12 13.46C19.97 13.58'
    ' 19.82 13.7 19.68 13.84C19.6 13.91 19.52 13.98 19.45 14.05L19.05 14.44L18.77 14.72L18.46 15.03L18.16'
    ' 15.32L17.85 15.63L17.48 15.99L17.21 16.26L17.12 16.35C17.08 16.39 17.04 16.43 16.99 16.48L16.93 16.54C16.89'
    ' 16.57 16.86 16.6 16.82 16.64C16.79 16.67 16.75 16.71 16.71 16.74C15.74 17.64 14.65 18.41 13.48 19.03C13.55'
    ' 19.06 13.62 19.1 13.69 19.13C13.74 19.15 13.8 19.18 13.85 19.21C13.91 19.23 13.96 19.25 14.02 19.28C14.07'
    ' 19.3 14.12 19.33 14.18 19.35C14.23 19.38 14.29 19.4 14.35 19.43C14.42 19.46 14.49 19.49 14.55 19.51C14.62'
    ' 19.54 14.68 19.57 14.75 19.6C14.83 19.63 14.92 19.67 15 19.7C15.07 19.73 15.14 19.76 15.2 19.79C15.31'
    ' 19.83 15.41 19.87 15.52 19.91C15.62 19.95 15.72 19.99 15.82 20.03C15.89 20.05 15.97 20.08 16.04 20.11C16.17'
    ' 20.16 16.3 20.21 16.43 20.25C16.49 20.28 16.56 20.3 16.62 20.32C16.71 20.35 16.81 20.39 16.9 20.42C16.97'
    ' 20.44 17.05 20.47 17.12 20.49C17.24 20.53 17.35 20.57 17.46 20.6C17.57 20.64 17.69 20.68 17.81 20.72C17.95'
    ' 20.76 18.1 20.8 18.24 20.85C18.34 20.88 18.43 20.91 18.53 20.93C18.72 20.99 18.92 21.04 19.12 21.1C19.19'
    ' 21.12 19.26 21.13 19.33 21.15C19.46 21.18 19.59 21.21 19.73 21.23C19.88 21.26 20.03 21.28 20.18 21.3C20.39'
    ' 21.32 20.59 21.33 20.8 21.34C20.98 21.34 21.17 21.34 21.35 21.32C21.52 21.31 21.7 21.29 21.87 21.26C22.1'
    ' 21.23 22.33 21.18 22.56 21.12C22.72 21.07 22.87 21.02 23.02 20.97C23.15 20.92 23.29 20.86 23.42 20.8C23.57'
    ' 20.74 23.73 20.66 23.87 20.58C23.94 20.54 24.02 20.5 24.09 20.45C24.15 20.41 24.22 20.37 24.29 20.32C24.39'
    ' 20.25 24.49 20.18 24.6 20.1C24.68 20.04 24.77 19.97 24.85 19.9C25 19.77 25.14 19.64 25.28 19.49C25.34'
    ' 19.42 25.41 19.35 25.47 19.28C25.55 19.18 25.63 19.09 25.71 18.99C25.77 18.91 25.83 18.83 25.89 18.75C26.05'
    ' 18.51 26.2 18.27 26.33 18.02L26.48 17.71L27.86 14.97L27.86 14.98C28.29 14.02 28.9 13.15 29.65 12.41Z"'
    ' fill="#133C9A"/>'
    '<path d="M12.42 26.54C15.2 26.54 17.94 25.8 20.33 24.39C22.73 22.98 24.71 20.95 26.06 18.52C26.16 18.35'
    ' 26.25 18.18 26.34 18.01C26.2 18.26 26.05 18.51 25.89 18.75C25.83 18.83 25.77 18.91 25.71 18.99C25.63'
    ' 19.09 25.55 19.18 25.47 19.28C25.41 19.35 25.34 19.42 25.28 19.49C25.14 19.64 25 19.77 24.85 19.9C24.77'
    ' 19.97 24.68 20.04 24.6 20.1C24.49 20.18 24.39 20.25 24.29 20.32C24.22 20.37 24.15 20.41 24.09 20.45C24.02'
    ' 20.5 23.94 20.54 23.87 20.58C23.73 20.66 23.57 20.74 23.42 20.8C23.29 20.86 23.15 20.92 23.02 20.97C22.87'
    ' 21.02 22.72 21.07 22.56 21.12C22.33 21.18 22.1 21.23 21.87 21.26C21.7 21.29 21.52 21.31 21.35 21.32C21.17'
    ' 21.34 20.98 21.34 20.8 21.34C20.59 21.33 20.39 21.32 20.18 21.3C20.03 21.28 19.88 21.26 19.73 21.23C19.59'
    ' 21.21 19.46 21.18 19.33 21.15C19.26 21.13 19.19 21.12 19.12 21.1C18.92 21.04 18.72 20.99 18.53 20.93C18.43'
    ' 20.91 18.34 20.88 18.24 20.85C18.1 20.81 17.95 20.76 17.81 20.72C17.69 20.68 17.57 20.64 17.46 20.6C17.35'
    ' 20.57 17.23 20.53 17.12 20.49C17.05 20.47 16.97 20.44 16.9 20.42C16.81 20.39 16.71 20.35 16.62 20.32C16.56'
    ' 20.3 16.49 20.28 16.43 20.25C16.3 20.21 16.17 20.16 16.04 20.11C15.97 20.08 15.89 20.05 15.82 20.03C15.72'
    ' 19.99 15.62 19.95 15.52 19.91C15.41 19.87 15.31 19.83 15.2 19.79C15.14 19.76 15.07 19.73 15 19.7C14.92'
    ' 19.67 14.83 19.63 14.75 19.6C14.68 19.57 14.62 19.54 14.55 19.51C14.49 19.49 14.42 19.46 14.35 19.43C14.29'
    ' 19.4 14.23 19.38 14.18 19.35C14.12 19.33 14.07 19.3 14.02 19.28C13.96 19.25 13.91 19.23 13.85 19.21C13.8'
    ' 19.18 13.74 19.15 13.69 19.13C13.62 19.1 13.55 19.06 13.48 19.03C13.4 19 13.33 18.96 13.26 18.93C13.18'
    ' 18.89 13.1 18.85 13.02 18.81C12.96 18.78 12.89 18.75 12.82 18.71C9.34 16.97 6.19 14.63 3.53 11.78C3.5'
    ' 11.75 3.46 11.73 3.42 11.72C3.38 11.71 3.33 11.71 3.29 11.73C3.25 11.75 3.22 11.77 3.2 11.81C3.17 11.84'
    ' 3.16 11.88 3.16 11.93L3.17 21.95V22.77C3.16 23 3.22 23.23 3.33 23.43C3.44 23.64 3.6 23.82 3.79 23.95C6.35'
    ' 25.64 9.35 26.55 12.42 26.54" fill="#3370FF"/>'
    "</svg>"
)


def _layout(title: str, body: str, *, head: str = "", center: bool = False) -> str:
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · {BRAND}</title><style>{_CSS}</style>{head}</head>
<body><main class="card{' center' if center else ''}">
<p class="brand">BridgeFlow<span> AI</span></p>
{body}
</main></body></html>"""


def _checklist(checks: dict[str, bool]) -> str:
    """The operator's view of a misconfigured deploy: names and set/unset, never values.

    Only reachable once the page already says sign-in is unconfigured, so it adds
    no fact an anonymous visitor could not already see — and a deploy is fixed by
    knowing WHICH variable is missing.
    """
    rows = "".join(
        f'<div><span>{html.escape(name)}</span>'
        f'<span class="{"ok" if ok else "missing"}">{"ok" if ok else "未设置"}</span></div>'
        for name, ok in checks.items())
    return f"""<details><summary class="hint">管理员检查项</summary>
<div class="checks">{rows}</div>
<p class="hint" style="margin-top:6px">引导变量只能由启动 shell export，不能写进项目携带的 .env。</p>
</details>"""


def index(session: dict | None, registry: dict[str, dict], feishu_ready: bool,
          checks: dict[str, bool] | None = None) -> str:
    """The one page: sign-in methods when anonymous, the way into apps when signed in.

    The app is never a choice here — BridgeFlow is fixed, the visitor only picks
    HOW to prove identity (today: Feishu; the list is the extension point).

    With no credentials configured, do not draw a button that cannot be pressed:
    say it is a deployment problem and give the operator something to act on.
    """
    if session is None:
        if feishu_ready:
            # The section heading only earns its place above an actual choice.
            body = ('<p class="sec">选择登录方式</p>'
                    f'<a class="btn full lg" href="/login">{_FEISHU_LOGO}<span>飞书登录</span></a>'
                    '<p class="hint center">登录后，门户只把一枚短期令牌交给 BridgeFlow，'
                    '不转交你的飞书凭据。</p>')
        else:
            body = ('<div class="callout warn"><h4>飞书登录未配置</h4>'
                    '<p>请联系平台管理员。</p></div>'
                    f'{_checklist(checks) if checks else ""}')
        return _layout("统一登录门户", f"""<p class="sub">统一登录门户</p>
{body}""")

    name = html.escape(str(session.get("name") or session["sub"]))
    email = html.escape(str(session.get("email") or ""))
    avatar_url = str(session.get("avatar") or "")
    avatar = (f'<img src="{html.escape(avatar_url, quote=True)}" alt="">'
              if avatar_url else html.escape(name[:1].upper()))
    entries = "".join(
        f'<a class="enter" href="{html.escape(entry["redirect_uri"], quote=True)}">'
        f'<span>进入 {html.escape(app_name)}</span></a>'
        for app_name, entry in registry.items())
    return _layout("已登录", f"""<p class="sub">统一登录门户</p>
<div class="user"><div class="avatar">{avatar}</div>
<div class="who"><p class="name">{name}</p><p class="hint">{email}</p></div></div>
<p class="sec">应用</p>
{entries}
<form class="logout" method="post" action="/logout">
<button class="btn quiet" type="submit">退出登录</button></form>""")


def error_page(title: str, detail: str, *, tone: str = "bad", again: bool = False) -> str:
    """Browser-facing failures (bad state, Feishu refusal, not configured).

    Each failure gets its own next step rather than one shared "something went
    wrong": ``again`` offers login as the primary action, and only failures that
    a fresh login actually fixes should set it. ``tone`` is warn for "this will
    work if you retry" and bad for "this needs someone to change something".
    """
    action = ('<p class="act"><a class="btn primary full" href="/login">重新登录</a></p>'
              if again else
              '<p class="act"><a class="btn quiet" href="/">返回首页重新登录</a></p>')
    css = "warn" if tone == "warn" else "bad"
    return _layout("出错了", f"""<p class="sub">统一登录门户</p>
<div class="callout {css}"><h4>{html.escape(title)}</h4>
<p>{html.escape(detail)}</p></div>
{action}""")


def login_required(portal_url: str) -> str:
    """The 401 body Caddy forward_auth hands to anonymous browsers.

    A meta refresh plus a visible link: browsers land on the portal either way,
    and the target comes from the portal's own config, never from the request.
    """
    target = html.escape(portal_url.rstrip("/") + "/", quote=True)
    return _layout("需要登录", f"""<p class="muted" style="margin-top:18px">需要先登录，
正在跳转到统一登录门户……</p>
<p class="act"><a class="btn" href="{target}">立即跳转</a></p>""",
                   head=f'<meta http-equiv="refresh" content="0; url={target}">', center=True)


def entering(target: str) -> str:
    """The page that ends the cross-site login chain, instead of one more redirect.

    dsh web's native session cookie is ``SameSite=Strict``. The whole login is a
    single navigation whose redirect chain starts at ``open.feishu.cn`` — cross
    site — so browsers withhold that cookie on the last hop and dsh answers its
    own 401 ("dsh web authentication required"), which is why a manual reload
    used to be needed. This page breaks the chain: the browser stops here on the
    portal, and the jump into the app is a NEW navigation started by this
    document. ``portal.<domain>`` and ``<domain>`` share a registrable domain, so
    that navigation is same-site and the cookie rides along.

    Never answer /enter with a Location header again — that restores the chain.
    """
    href = html.escape(target, quote=True)
    return _layout("正在进入", f"""<p class="muted" style="margin-top:18px">正在进入 {BRAND}……</p>
<div class="bar"><span></span></div>
<p class="act"><a class="btn quiet" id="go" href="{href}">立即进入</a></p>
<script>location.replace(document.getElementById("go").href)</script>""",
                   head=('<meta name="referrer" content="no-referrer">'
                         f'<meta http-equiv="refresh" content="0; url={href}">'),
                   center=True)
