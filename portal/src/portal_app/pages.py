"""HTML pages for the portal: one layout, a few small views.

No framework and no static files on purpose: the portal is an edge service,
and its pages must render even when everything downstream is down. All user
input passes through html.escape — a name from Feishu is data, never markup.
"""

from __future__ import annotations

import html

BRAND = "BridgeFlow AI"

_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; margin: 0; }
body { min-height: 100vh; display: grid; place-items: center; padding: 24px;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
  background: linear-gradient(160deg, #0b1e3a 0%, #12305e 60%, #1b4a8f 100%); color: #1f2329; }
.card { width: 100%; max-width: 400px; background: #fff; border-radius: 16px;
  box-shadow: 0 24px 60px rgba(4, 20, 46, .35); padding: 40px 36px; }
.brand { font-size: 22px; font-weight: 700; letter-spacing: .5px; color: #12305e; }
.brand span { color: #3370ff; }
.subtitle { margin-top: 6px; font-size: 13px; color: #8f959e; }
.section { margin: 28px 0 12px; font-size: 12px; color: #8f959e; letter-spacing: 1px; text-transform: uppercase; }
a.method { display: flex; align-items: center; justify-content: center; gap: 10px;
  width: 100%; padding: 13px 16px; border-radius: 10px; text-decoration: none;
  font-size: 15px; font-weight: 600; background: #3370ff; color: #fff; }
a.method:hover { background: #295fd4; }
a.method.guest { margin-top: 14px; background: #fff; color: #1f2329; border: 1px solid #d0d3d6; }
a.method.guest:hover { background: #f2f3f5; }
.method-note { margin-top: 10px; font-size: 12px; color: #8f959e; text-align: center; }
a.enter { display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 13px 16px; margin-top: 10px; border-radius: 10px;
  text-decoration: none; font-size: 15px; font-weight: 600; background: #f2f3f5; color: #1f2329; }
a.enter:hover { background: #e5e6eb; }
a.enter::after { content: "→"; color: #3370ff; }
.user { display: flex; align-items: center; gap: 12px; margin-top: 28px; }
.avatar { width: 44px; height: 44px; border-radius: 50%; background: #3370ff; color: #fff;
  display: grid; place-items: center; font-size: 18px; font-weight: 700; overflow: hidden; flex: none; }
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.user .name { font-weight: 600; }
.user .mail { font-size: 12px; color: #8f959e; }
.logout { margin-top: 24px; text-align: center; }
.logout button { background: none; border: none; color: #8f959e; font-size: 13px;
  cursor: pointer; text-decoration: underline; }
.error-title { font-size: 17px; font-weight: 700; color: #d83931; margin-top: 24px; }
.error-detail { margin-top: 8px; font-size: 13px; color: #646a73; word-break: break-all; }
a.again { display: inline-block; margin-top: 20px; color: #3370ff; font-size: 14px; text-decoration: none; }
"""

_FEISHU_LOGO = """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
<path d="M3 5.5 10.5 3v6.5H3V5.5Z" fill="#fff" opacity=".95"/>
<path d="M12.5 3H21v6.5h-8.5V3Z" fill="#fff" opacity=".75"/>
<path d="M3 11.5h7.5V21L3 18.5v-7Z" fill="#fff" opacity=".75"/>
<path d="M12.5 11.5H21V21h-8.5v-9.5Z" fill="#fff" opacity=".95"/>
</svg>"""


def _layout(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · {BRAND}</title><style>{_CSS}</style></head>
<body><main class="card">
<div class="brand">BridgeFlow<span> AI</span></div>
{body}
</main></body></html>"""


def index(session: dict | None, registry: dict[str, dict], feishu_ready: bool, guest: bool = False) -> str:
    """The one page: sign-in methods when anonymous, the way into apps when signed in.

    The app is never a choice here — BridgeFlow is fixed, the visitor only picks
    HOW to prove identity (today: Feishu; the list is the extension point).
    """
    if session is None:
        if feishu_ready:
            method = f'<a class="method" href="/login">{_FEISHU_LOGO}Sign in with Feishu (Lark)</a>'
            note = ""
        else:
            method = ""
            note = '<p class="method-note">Feishu sign-in is not configured. Contact your administrator.</p>'
        visitor = ('<a class="method guest" href="/guest">Continue as guest</a>'
                   '<p class="method-note">No Feishu account needed: sample data only, separate from the '
                   'real service, reset nightly. Feishu features are unavailable.</p>') if guest else ""
        return _layout("Sign in", f"""<p class="subtitle">Sign-in portal</p>
<p class="section">Choose how to sign in</p>
{method}{note}{visitor}""")

    name = html.escape(str(session.get("name") or session["sub"]))
    email = html.escape(str(session.get("email") or ""))
    avatar_url = str(session.get("avatar") or "")
    avatar = (f'<img src="{html.escape(avatar_url, quote=True)}" alt="">'
              if avatar_url else html.escape(name[:1].upper()))
    entries = "".join(
        f'<a class="enter" href="{html.escape(entry["redirect_uri"], quote=True)}">'
        f'Open {html.escape(app_name)}</a>'
        for app_name, entry in registry.items())
    return _layout("Signed in", f"""<p class="subtitle">Sign-in portal</p>
<div class="user"><div class="avatar">{avatar}</div>
<div><div class="name">{name}</div><div class="mail">{email}</div></div></div>
<p class="section">Applications</p>
{entries}
<form class="logout" method="post" action="/logout"><button type="submit">Sign out</button></form>""")


def error_page(title: str, detail: str) -> str:
    """Browser-facing failures (bad state, Feishu refusal, not configured)."""
    return _layout("Something went wrong", f"""<p class="subtitle">Sign-in portal</p>
<p class="error-title">{html.escape(title)}</p>
<p class="error-detail">{html.escape(detail)}</p>
<a class="again" href="/">Back to sign-in →</a>""")


def console_blocked(title: str, detail: str, portal_url: str) -> str:
    """The body forward_auth hands a signed-in browser that may not pass (#229).

    Deliberately not error_page: that one offers "sign in again", and neither of
    these failures is fixed by signing in again — one is a missing grant, the
    other is a scope this portal could not confirm. The wording must not say the
    person was refused when the truth is that nobody could check.
    """
    home = html.escape(portal_url.rstrip("/") + "/", quote=True)
    return _layout(title, f"""<p class="subtitle">Sign-in portal</p>
<p class="error-title">{html.escape(title)}</p>
<p class="error-detail">{html.escape(detail)}</p>
<a class="again" href="{home}">Back to the portal →</a>""")


def login_required(portal_url: str) -> str:
    """The 401 body Caddy forward_auth hands to anonymous browsers.

    A meta refresh plus a visible link: browsers land on the portal either way,
    and the target comes from the portal's own config, never from the request.
    """
    target = html.escape(portal_url.rstrip("/") + "/", quote=True)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url={target}">
<title>Sign-in required · {BRAND}</title></head>
<body><p>Sign-in required. Taking you to the portal… <a href="{target}">Go now</a></p>
</body></html>"""


def restarting() -> str:
    """The public demo while its instance (re)starts and has no launch token yet (docs/36 §4).

    Reloads itself: the same URL again, which on the demo's own host is /__enter."""
    return _layout("Starting", """<meta http-equiv="refresh" content="15">
<p class="subtitle">The demo is starting. This page retries in 15 seconds.</p>
<a class="again" href="">Retry now →</a>""")


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
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="referrer" content="no-referrer">
<meta http-equiv="refresh" content="0; url={href}">
<title>Opening · {BRAND}</title></head>
<body><p>Opening {BRAND}… <a id="go" href="{href}">Continue</a></p>
<script>location.replace(document.getElementById("go").href)</script>
</body></html>"""
