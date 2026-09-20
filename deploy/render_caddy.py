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
    return f"""{host} {{
    forward_auth 127.0.0.1:{portal_port} {{
        uri /verify
    }}
    reverse_proxy 127.0.0.1:{port}
}}"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("domain")
    parser.add_argument("--seats", default=str(ROOT / "data/mappings/seats.yaml"),
                        help="seat registry; absence = legacy single-console shape")
    parser.add_argument("--portal-port", type=int, default=8100)
    parser.add_argument("--web-port", type=int, default=3080,
                        help="only used in the legacy shape")
    args = parser.parse_args()

    template = (ROOT / "deploy/Caddyfile.template").read_text(encoding="utf-8")
    seats_path = Path(args.seats)
    if not seats_path.exists():
        sys.stdout.write(render_legacy(template, args.domain, args.web_port, args.portal_port))
        return 0
    try:
        registry = yaml.safe_load(seats_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        print(f"seat registry is not valid YAML ({seats_path}): {exc}", file=sys.stderr)
        return 1
    seats = registry.get("seats") or []
    if not seats:
        sys.stdout.write(render_legacy(template, args.domain, args.web_port, args.portal_port))
        return 0

    apex_redirect = "    redir https://portal." + args.domain + "{uri} permanent"
    blocks = [
        f"# Rendered by deploy/render_caddy.py from {seats_path} — do not edit by hand.",
        f"{args.domain} {{",
        "    # Seat deployments: the apex is the front door, the portal; consoles",
        f"    # live at <seat>.console.{args.domain}.",
        apex_redirect,
        "}",
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
