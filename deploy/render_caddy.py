#!/usr/bin/env python3
"""Render the Caddyfile for the apex, the portal and every seat (docs/35).

Without a seat registry the output is exactly the legacy shape: the apex site
IS the single console behind forward_auth. With seats the apex redirects to
the portal and each seat gets its own site block under an explicit hostname —
seven seats need no wildcard certificate, only seven DNS records.

The portal's /verify sees the original Host (Caddy's reverse_proxy keeps it),
which is what the seat-binding check keys on; /verify also accepts
X-Forwarded-Host if a different front door rewrites Host.

Render only — the caller installs with sudo:

    .venv/bin/python deploy/render_caddy.py example.com | sudo tee /etc/caddy/Caddyfile
    sudo systemctl reload caddy

Idempotence is the caller's diff, not this script's business.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def render_legacy(template: str, domain: str, web_port: int, portal_port: int) -> str:
    return (template.replace("__DOMAIN__", domain)
                    .replace("__WEB_PORT__", str(web_port))
                    .replace("__PORTAL_PORT__", str(portal_port)))


def seat_site(host: str, port: int, portal_port: int) -> str:
    """One seat's site block.

    `header_up -Connection` / `-Upgrade` are load-bearing, not tidying: see the
    same two lines (and the full reasoning) in deploy/Caddyfile.template. Short
    version — without them a WebSocket upgrade reaches /verify as an upgrade,
    uvicorn answers 403 because the portal serves no ws route, forward_auth
    rejects the connection, and `/api/remote.mux` never opens. That socket
    carries every Remote stream, and the Workspace projection has no unary
    fallback, so the seat opens with no workspace and no way to start a chat.
    """
    return f"""{host} {{
    forward_auth 127.0.0.1:{portal_port} {{
        uri /verify
        header_up -Connection
        header_up -Upgrade
    }}
    reverse_proxy 127.0.0.1:{port}
}}"""


def demo_site(domain: str, port: int, portal_port: int) -> str:
    """The public demo on the apex (docs/36 §3–4): the guest console, no sign-in in front.

    No forward_auth — it is public on purpose and holds sample data only. dsh web still wants
    its per-boot launch token before it mints a session, and that cannot be switched off, so a
    browser opening the page without a session is sent to /__enter: the portal's /guest
    handover, served on this host, which carries the token back in. Only a page load of `/`
    without a token is redirected; API, asset and WebSocket 401s stay 401 (a redirect would
    hand an XHR an HTML page), and `/?token=` that still fails stays 401 instead of looping.
    """
    return f"""{domain} {{
    handle /__enter {{
        rewrite * /guest
        reverse_proxy 127.0.0.1:{portal_port}
    }}
    handle {{
        reverse_proxy 127.0.0.1:{port} {{
            @unauth status 401
            handle_response @unauth {{
                @page {{
                    method GET
                    path /
                    header Accept *text/html*
                    expression `{{http.request.uri.query.token}} == ""`
                }}
                route {{
                    redir @page /__enter 302
                    copy_response
                }}
            }}
        }}
    }}
}}"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("domain")
    parser.add_argument("--seats", default=str(ROOT / "data/mappings/seats.yaml"),
                        help="seat registry; absence = legacy single-console shape")
    parser.add_argument("--portal-port", type=int, default=8100)
    parser.add_argument("--web-port", type=int, default=3080,
                        help="only used in the legacy shape")
    parser.add_argument("--guest-port", type=int, default=0,
                        help="serve the guest instance as the public demo on the apex (docs/36); 0 = none")
    args = parser.parse_args()
    demo = demo_site(args.domain, args.guest_port, args.portal_port) if args.guest_port else ""

    template = (ROOT / "deploy/Caddyfile.template").read_text(encoding="utf-8")
    if demo:
        # The apex belongs to the demo; the single console moves to console.<domain>
        # (its portal app entry's app_uri/origins must follow — docs/36 §9).
        template = template.replace("\n__DOMAIN__ {", "\nconsole.__DOMAIN__ {", 1)
    seats_path = Path(args.seats)
    if not seats_path.exists():
        sys.stdout.write(render_legacy(template, args.domain, args.web_port, args.portal_port)
                         + (f"\n{demo}\n" if demo else ""))
        return 0
    try:
        registry = yaml.safe_load(seats_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        print(f"seat registry is not valid YAML ({seats_path}): {exc}", file=sys.stderr)
        return 1
    seats = registry.get("seats") or []
    if not seats:
        sys.stdout.write(render_legacy(template, args.domain, args.web_port, args.portal_port)
                         + (f"\n{demo}\n" if demo else ""))
        return 0

    if demo:
        apex = [demo]
    else:
        apex = [
            f"{args.domain} {{",
            "    # Seat deployments: the apex is the front door, the portal; consoles",
            f"    # live at <seat>.console.{args.domain}.",
            "    redir https://portal." + args.domain + "{uri} permanent",
            "}",
        ]
    blocks = [
        f"# Rendered by deploy/render_caddy.py from {seats_path} — do not edit by hand.",
        *apex,
        "",
        f"portal.{args.domain} {{",
        f"    reverse_proxy 127.0.0.1:{args.portal_port}",
        "}",
    ]
    for seat in seats:
        name, port = seat.get("name"), seat.get("port")
        if not name or not port:
            print(f"seat entry missing name/port ({seat}); run provision_seat.sh, "
                  "do not hand-edit the registry", file=sys.stderr)
            return 1
        blocks.append("")
        blocks.append(seat_site(f"{name}.console.{args.domain}", int(port), args.portal_port))
    sys.stdout.write("\n".join(blocks) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
