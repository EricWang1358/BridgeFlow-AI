#!/usr/bin/env python3
"""BridgeFlow AI booth poster, "Confluence" edition (A1 portrait).

One SVG unit is one pixel at 150 dpi, so the canvas is 3508 x 4967 (594 x 841 mm).
Everything is vector; the 150 dpi figure only matters for the PNG export.

    python3 finale/poster/build_flow_poster.py            # SVG + HTML
    python3 finale/poster/build_flow_poster.py --export   # also PNG (3508 x 4967) and PDF via Chrome
    python3 finale/poster/build_flow_poster.py --bleed    # 3 mm bleed on every side (600 x 847 mm)

Fonts are macOS system fonts (Bodoni 72, Avenir Next). Send the printer the PDF, which embeds them.
"""

from __future__ import annotations

import argparse
import html
import math
import random
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD_POSTER = HERE / "bridgeflow-a1-poster.html"  # source of the two QR codes
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

W, H = 3508, 4967
MM = W / 594  # units per millimetre
BLEED = round(3 * MM)
M = 180  # page margin, about 30 mm

SERIF = "'Bodoni 72', Didot, 'Bodoni MT', serif"
SANS = "'Avenir Next', Avenir, 'Helvetica Neue', Arial, sans-serif"

NAVY = "#0B1F3A"
INK = "#33415C"
MUTED = "#5E6B82"
BLUE = "#1F6FB2"
LOGO_BLUE = "#1E74C0"
CYAN = "#5CCBEF"
GOLD = "#C9A24A"
GOLD_SOFT = "#E6CB86"
TEAL = "#1E9E8A"
CORAL = "#C8574D"
SLATE = "#8A97AE"
ON_DARK = "#D5E3F0"

# Middle section: three columns that share one top and bottom edge.
TOP, BOT = 1900, 3560
DEPT_X0, DEPT_X1 = M, 920
FLOW_X0, FLOW_X1 = 1260, 2200
CARD_X0, CARD_X1 = 2340, W - M
STAGE_H = (BOT - TOP) / 4
CONFLUENCE = (FLOW_X0, (TOP + BOT) / 2)


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def text(x, y, s, size, *, family=SANS, weight=500, fill=NAVY, anchor="start", spacing=0,
         italic=False, opacity=None, raw=False, extra="") -> str:
    attrs = [f'x="{x:g}"', f'y="{y:g}"', f'font-family="{family}"', f'font-size="{size}"',
             f'font-weight="{weight}"', f'fill="{fill}"']
    if anchor != "start":
        attrs.append(f'text-anchor="{anchor}"')
    if spacing:
        attrs.append(f'letter-spacing="{spacing:g}"')
    if italic:
        attrs.append('font-style="italic"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity}"')
    if extra:
        attrs.append(extra)
    return f'<text {" ".join(attrs)}>{s if raw else esc(s)}</text>'


# ---------- Icons: one family, drawn on a 48-unit grid with round caps ----------

ICONS = {
    "factory": '<path d="M5 41V23l10 6v-6l10 6v-6l10 6V9h7v32z"/><path d="M14 35h4M24 35h4"/>',
    "contract": '<rect x="10" y="8" width="28" height="34" rx="3"/><path d="M19 8V5h10v3M17 19h14M17 26h14M17 33h8"/>',
    "finance": '<path d="M6 41h36M12 35v-8M20 35V21M28 35v-9M36 35V13"/>',
    "people": '<circle cx="18" cy="17" r="6"/><path d="M6 39c0-7 5.5-11 12-11s12 4 12 11"/>'
              '<circle cx="33" cy="15" r="5"/><path d="M32 25c6 0 10 4 10 10"/>',
    "plus": '<path d="M24 12v24M12 24h24"/>',
    "layers": '<ellipse cx="24" cy="12" rx="14" ry="5"/><path d="M10 12v24c0 2.8 6.3 5 14 5s14-2.2 14-5V12"/>'
              '<path d="M10 24c0 2.8 6.3 5 14 5s14-2.2 14-5"/>',
    "radar": '<path d="M6 36l10-10 8 6 16-18"/><path d="M31 14h9v9"/><path d="M6 42h36"/>',
    "branch": '<circle cx="9" cy="24" r="4"/><path d="M13 24h7m0 0c6 0 8-10 14-10h3M20 24h17M20 24c6 0 8 10 14 10h3"/>'
              '<circle cx="40" cy="14" r="2.5"/><circle cx="40" cy="24" r="2.5"/><circle cx="40" cy="34" r="2.5"/>',
    "decide": '<circle cx="20" cy="15" r="7"/><path d="M6 41c0-8 6-13 14-13 3 0 5.5.7 7.5 2"/><path d="M29 36l5 5 9-10"/>',
    "clock": '<circle cx="24" cy="24" r="17"/><path d="M24 14v10l7 5"/>',
    "alert": '<path d="M24 7L43 40H5z"/><path d="M24 19v10"/><circle cx="24" cy="34.5" r="1.2"/>',
    "trace": '<rect x="6" y="9" width="36" height="30" rx="3"/><path d="M6 19h36M6 29h36M18 9v30M30 9v30"/>'
             '<rect x="30" y="29" width="12" height="10" fill="currentColor" stroke="none" opacity=".35"/>',
    "tag": '<path d="M8 8h15l18 18-15 15L8 23z"/><circle cx="15.5" cy="15.5" r="2.5"/>',
    "chart": '<path d="M6 41h36"/><path d="M8 33l9-9 7 5 14-15"/>',
    "clip": '<path d="M31 15L18 28a4 4 0 0 0 6 6l13-13a7.5 7.5 0 0 0-10.6-10.6L13 23.8a11 11 0 0 0 15.6 15.6L39 29"/>',
    "check": '<path d="M12 25l8 8 16-17"/>',
    "cross": '<path d="M15 15l18 18M33 15L15 33"/>',
}


def icon(name: str, cx: float, cy: float, size: float, color: str, stroke_px: float) -> str:
    s = size / 48
    return (f'<g transform="translate({cx - size / 2:g} {cy - size / 2:g}) scale({s:g})" fill="none" '
            f'stroke="{color}" color="{color}" stroke-width="{stroke_px / s:.2f}" stroke-linecap="round" '
            f'stroke-linejoin="round">{ICONS[name]}</g>')


def star(cx: float, cy: float, r_out: float, r_in: float) -> str:
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / 5
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return "M" + " L".join(pts) + "Z"


# ---------- Defs ----------

def defs() -> str:
    return f"""
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#E7EFF7"/>
    <stop offset=".55" stop-color="#F2EEEA"/>
    <stop offset="1" stop-color="#F7E3CB"/>
  </linearGradient>
  <radialGradient id="sun" cx="2950" cy="1640" r="1150" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#FFF4DE"/>
    <stop offset=".18" stop-color="#FCE6C2" stop-opacity=".85"/>
    <stop offset="1" stop-color="#F7E3CB" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="sea" x1="0" y1="1640" x2="0" y2="3800" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#C9D9E6"/>
    <stop offset=".028" stop-color="#93B4CF"/>
    <stop offset=".074" stop-color="#5684AF"/>
    <stop offset=".14" stop-color="#2F5F8E"/>
    <stop offset=".35" stop-color="#1B4370"/>
    <stop offset=".63" stop-color="#12345A"/>
    <stop offset="1" stop-color="#0C2643"/>
  </linearGradient>
  <linearGradient id="haze" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>
    <stop offset=".5" stop-color="#FFFFFF" stop-opacity=".55"/>
    <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="ivory" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FAF8F3"/>
    <stop offset="1" stop-color="#F3EFE6"/>
  </linearGradient>
  <linearGradient id="goldText" x1="1000" y1="0" x2="2500" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#A9823A"/>
    <stop offset=".42" stop-color="#D4B467"/>
    <stop offset=".62" stop-color="#C29A4A"/>
    <stop offset="1" stop-color="#A67E34"/>
  </linearGradient>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#E2C47A"/>
    <stop offset="1" stop-color="#B88F3E"/>
  </linearGradient>
  <linearGradient id="stream" x1="{DEPT_X1}" y1="0" x2="{FLOW_X0}" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{CYAN}" stop-opacity=".75"/>
    <stop offset="1" stop-color="#E9FAFF"/>
  </linearGradient>
  <linearGradient id="spine" x1="0" y1="{TOP}" x2="0" y2="{BOT}" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{CYAN}" stop-opacity=".55"/>
    <stop offset=".75" stop-color="#BFEFFF" stop-opacity=".85"/>
    <stop offset="1" stop-color="{GOLD_SOFT}"/>
  </linearGradient>
  <linearGradient id="glassDark" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#2B5079" stop-opacity=".62"/>
    <stop offset="1" stop-color="#0E2747" stop-opacity=".66"/>
  </linearGradient>
  <linearGradient id="glassPanel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#335C88" stop-opacity=".5"/>
    <stop offset="1" stop-color="#10294A" stop-opacity=".6"/>
  </linearGradient>
  <linearGradient id="logoFlow" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#1B6FBA"/>
    <stop offset="1" stop-color="#36A3DE"/>
  </linearGradient>
  <filter id="glow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="16"/></filter>
  <filter id="glowWide" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="34"/></filter>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="36"/></filter>
</defs>"""


# ---------- Background: dawn sky, distant skyline, the strait, the shore ----------

HORIZON = 1640


def skyline(rng: random.Random) -> str:
    """Hazy city on the right, low islands on the left, a few ships in the lane."""
    out = []
    # Low islands
    out.append(f'<path d="M-40 {HORIZON} C 120 {HORIZON - 40}, 380 {HORIZON - 62}, 620 {HORIZON - 30} '
               f'S 900 {HORIZON - 8}, 1000 {HORIZON}Z" fill="#BCCBDA" opacity=".75"/>')
    out.append(f'<path d="M1380 {HORIZON} C 1450 {HORIZON - 22}, 1560 {HORIZON - 26}, 1660 {HORIZON}Z" '
               f'fill="#C3D1DE" opacity=".7"/>')
    # Towers
    x, d = 2080, []
    while x < W + 40:
        w = rng.randint(30, 78)
        centre = 1 - min(abs(x - 3080) / 900, 1)  # taller in the business district
        h = int(rng.randint(24, 54) + centre * rng.randint(36, 104))
        if 2420 <= x <= 2800:  # leave room for the three hotel towers
            x = 2810
            continue
        d.append(f"M{x} {HORIZON}V{HORIZON - h}h{w}V{HORIZON}z")
        if w > 44 and rng.random() < 0.45:  # stepped crown
            inset = w // 4
            d.append(f"M{x + inset} {HORIZON - h}v-{rng.randint(12, 28)}h{w - 2 * inset}V{HORIZON - h}z")
        x += w + rng.randint(4, 22)
    # Three towers with a deck across the top
    for tx in (2470, 2580, 2690):
        d.append(f"M{tx} {HORIZON}l6 -118h34l6 118z")
    d.append(f"M2440 {HORIZON - 124}h340q6 0 6 6v4h-352v-4q0 -6 6 -6z")
    out.append(f'<path d="{" ".join(d)}" fill="#AFC0D2" opacity=".72"/>')
    # Observation wheel
    out.append(f'<g stroke="#AFC0D2" stroke-width="4" fill="none" opacity=".72">'
               f'<circle cx="2250" cy="{HORIZON - 62}" r="48"/>'
               f'<path d="M2250 {HORIZON - 62}l-26 62M2250 {HORIZON - 62}l26 62"/></g>')
    # Container ships on the horizon
    for sx, sc in ((520, 1.0), (1050, 0.8), (1820, 0.6)):
        out.append(f'<g transform="translate({sx} {HORIZON - 4}) scale({sc})" fill="#8EA4BA" opacity=".8">'
                   '<path d="M0 0h170l-12 16H10z"/><rect x="18" y="-14" width="104" height="14"/>'
                   '<rect x="30" y="-24" width="70" height="10"/><rect x="134" y="-30" width="16" height="30"/></g>')
    return "\n".join(out)


def sea_texture(rng: random.Random) -> str:
    """Bathymetric contours, closer together near the horizon, plus the sun's short reflection."""
    out = []
    n = 17
    for k in range(n):
        t = k / (n - 1)
        y = HORIZON + 60 + 2050 * t ** 1.55
        amp = 6 + 34 * t
        pts = [f"M-60 {y:.0f}"]
        x = -60
        while x < W + 60:
            step = rng.randint(380, 560)
            c1 = y + rng.uniform(-amp, amp)
            c2 = y + rng.uniform(-amp, amp)
            pts.append(f"C{x + step / 3:.0f} {c1:.0f},{x + 2 * step / 3:.0f} {c2:.0f},{x + step:.0f} {y:.0f}")
            x += step
        out.append(f'<path d="{" ".join(pts)}" fill="none" stroke="#FFFFFF" '
                   f'stroke-opacity="{0.06 + 0.05 * t:.3f}" stroke-width="{2.5 + 2 * t:.1f}"/>')
    for i in range(14):
        y = HORIZON + 8 + i * (4 + i * 0.5)
        length = (240 - i * 12) * rng.uniform(0.55, 1.1)
        cx = 2950 + rng.uniform(-45, 45)
        out.append(f'<path d="M{cx - length / 2:.0f} {y:.0f}h{length:.0f}" stroke="#FFF0D2" '
                   f'stroke-width="{4.5 - i * 0.15:.1f}" stroke-linecap="round" opacity="{0.6 * (1 - i / 14):.2f}"/>')
    return "\n".join(out)


def shore(dy: float = 0) -> str:
    return f"M-60 {3770 + dy} C 800 {3690 + dy}, 1800 {3830 + dy}, 2600 {3755 + dy} S 3300 {3690 + dy}, {W + 60} {3735 + dy}"


def background(rng: random.Random) -> str:
    return "\n".join([
        f'<rect x="-60" y="-60" width="{W + 120}" height="{HORIZON + 60}" fill="url(#sky)"/>',
        f'<rect x="-60" y="-60" width="{W + 120}" height="{HORIZON + 60}" fill="url(#sun)"/>',
        skyline(rng),
        f'<rect x="-60" y="{HORIZON}" width="{W + 120}" height="2400" fill="url(#sea)"/>',
        f'<rect x="-60" y="{HORIZON - 40}" width="{W + 120}" height="80" fill="url(#haze)"/>',
        sea_texture(rng),
        # Shore: a pale wave, then the ivory band
        f'<path d="{shore(-44)} L{W + 60} {H + 60} L-60 {H + 60}Z" fill="#FFFFFF" opacity=".10"/>',
        f'<path d="{shore()} L{W + 60} {H + 60} L-60 {H + 60}Z" fill="url(#ivory)"/>',
        f'<path d="{shore()}" fill="none" stroke="#FFFFFF" stroke-width="5" opacity=".7"/>',
    ])


# ---------- Header ----------

def header() -> str:
    cx = W / 2
    out = [
        # Wordmark with a wave under "Bridge"
        f'<path d="M780 566 C 990 648, 1390 656, 1720 548 C 1400 628, 1000 622, 780 566Z" fill="url(#logoFlow)"/>',
        f'<path d="M850 612 C 1040 680, 1380 688, 1650 610 C 1390 668, 1050 664, 850 612Z" fill="{CYAN}" opacity=".7"/>',
        text(cx, 470, f'<tspan fill="{NAVY}">Bridge</tspan><tspan fill="url(#logoFlow)">Flow</tspan>'
                      f'<tspan fill="{NAVY}"> AI</tspan>', 290, weight=700, anchor="middle", spacing=-6, raw=True),
        # Team line between two hairlines
        f'<path d="M1230 749h130M2140 749h130" stroke="{NAVY}" stroke-width="3" opacity=".45"/>',
        text(cx + 9, 770, 'TEAM CONFLUX<tspan font-size="36" dy="-22">4</tspan>', 58, weight=500, fill=NAVY,
             anchor="middle", spacing=18, opacity=".8", raw=True),
        # Headline
        text(cx, 990, "WHEN FLOWS CONVERGE,", 214, family=SERIF, weight=700, anchor="middle", spacing=4),
        text(cx, 1222, "VALUE MOVES.", 214, family=SERIF, weight=700, fill="url(#goldText)", anchor="middle",
             spacing=4),
        # Promise
        text(cx, 1365, "Connect every department’s data. Anticipate risks. Explore options.", 64, fill=INK,
             anchor="middle"),
        text(cx, 1450, "Turn decisions into action — with people in control.", 64, fill=INK, anchor="middle"),
    ]
    return "\n".join(out)


# ---------- Middle: departments -> one traceable flow -> one decision ----------

def column_label(x: float, num: str, label: str) -> str:
    return (text(x, TOP - 70, num, 54, family=SERIF, weight=700, fill=GOLD_SOFT)
            + text(x + 86, TOP - 72, label, 42, weight=600, fill="#FFFFFF", spacing=8, opacity=".92"))


DEPARTMENTS = [
    ("factory", "Production", "Capacity · Delivery", "Output · Inventory"),
    ("contract", "Procurement", "Cost · Suppliers", "Materials · Contracts"),
    ("finance", "Finance", "Margin · Cash flow", "Receivables · Budget"),
    ("people", "Marketing", "Demand · Pricing", "Customers · Growth"),
]


def departments() -> str:
    out = [column_label(DEPT_X0, "01", "EVERY DEPARTMENT")]
    gap = 70
    h = (BOT - TOP - 4 * gap) / 5
    w = DEPT_X1 - DEPT_X0
    for i in range(5):
        y = TOP + i * (h + gap)
        cy = y + h / 2
        more = i == 4
        # Stream from this card to the confluence
        qx, qy = CONFLUENCE
        path = f"M{DEPT_X1} {cy:.0f} C{DEPT_X1 + 190} {cy:.0f},{qx - 170} {qy:.0f},{qx} {qy:.0f}"
        dash = ' stroke-dasharray="4 22"' if more else ""
        out.append(f'<path d="{path}" fill="none" stroke="{CYAN}" stroke-width="30" opacity="{".18" if more else ".42"}" '
                   f'filter="url(#glow)"/>')
        out.append(f'<path d="{path}" fill="none" stroke="url(#stream)" stroke-width="{6 if more else 8}" '
                   f'stroke-linecap="round" opacity="{".6" if more else "1"}"{dash}/>')
        if more:
            out.append(f'<rect x="{DEPT_X0}" y="{y:.0f}" width="{w}" height="{h:.0f}" rx="44" fill="#FFFFFF" '
                       f'fill-opacity=".04" stroke="#FFFFFF" stroke-opacity=".5" stroke-width="3" '
                       f'stroke-dasharray="20 14"/>')
            out.append(f'<circle cx="{DEPT_X0 + 120}" cy="{cy:.0f}" r="62" fill="none" stroke="#FFFFFF" '
                       f'stroke-opacity=".45" stroke-width="3" stroke-dasharray="10 9"/>')
            out.append(icon("plus", DEPT_X0 + 120, cy, 64, "#FFFFFF", 6.5))
            out.append(text(DEPT_X0 + 220, cy + 20, "More departments", 56, weight=600, fill="#FFFFFF", opacity=".85"))
            continue
        name, title, l1, l2 = DEPARTMENTS[i]
        out.append(f'<rect x="{DEPT_X0}" y="{y:.0f}" width="{w}" height="{h:.0f}" rx="44" fill="url(#glassDark)" '
                   f'stroke="#FFFFFF" stroke-opacity=".3" stroke-width="3"/>')
        out.append(f'<circle cx="{DEPT_X0 + 120}" cy="{cy:.0f}" r="62" fill="#FFFFFF" fill-opacity=".1" '
                   f'stroke="#FFFFFF" stroke-opacity=".38" stroke-width="3"/>')
        out.append(icon(name, DEPT_X0 + 120, cy, 64, "#FFFFFF", 6.5))
        out.append(text(DEPT_X0 + 220, cy - 34, title, 64, weight=600, fill="#FFFFFF"))
        out.append(text(DEPT_X0 + 220, cy + 30, l1, 44, fill=ON_DARK))
        out.append(text(DEPT_X0 + 220, cy + 86, l2, 44, fill=ON_DARK))
        out.append(f'<circle cx="{DEPT_X1}" cy="{cy:.0f}" r="11" fill="#E9FAFF"/>')
    return "\n".join(out)


STAGES = [
    ("layers", "UNDERSTAND", "Unify every sheet", "into one table."),
    ("radar", "ANTICIPATE", "Find risks early,", "cite the cells behind them."),
    ("branch", "SIMULATE", "Compare options,", "price on evidence."),
    ("decide", "YOU DECIDE", "Approve, or reject with", "a reason the agent hears."),
]


def stage_centre(i: int) -> float:
    return TOP + i * STAGE_H + STAGE_H / 2


def flow_panel() -> str:
    qx, qy = CONFLUENCE
    spine_x = FLOW_X0 + 130
    out = [column_label(FLOW_X0, "02", "ONE TRACEABLE FLOW")]
    out.append(f'<rect x="{FLOW_X0}" y="{TOP}" width="{FLOW_X1 - FLOW_X0}" height="{BOT - TOP}" rx="48" '
               f'fill="url(#glassPanel)" stroke="#FFFFFF" stroke-opacity=".34" stroke-width="3"/>')
    # The decision row is gilded
    y4 = TOP + 3 * STAGE_H
    out.append(f'<rect x="{FLOW_X0 + 22}" y="{y4 + 22:.0f}" width="{FLOW_X1 - FLOW_X0 - 44}" height="{STAGE_H - 44:.0f}" '
               f'rx="34" fill="{GOLD_SOFT}" fill-opacity=".07" stroke="{GOLD_SOFT}" stroke-opacity=".7" stroke-width="3"/>')
    for i in (1, 2, 3):
        y = TOP + i * STAGE_H
        if i < 3:
            out.append(f'<path d="M{FLOW_X0 + 250} {y:.0f}H{FLOW_X1 - 50}" stroke="#FFFFFF" stroke-opacity=".14" '
                       f'stroke-width="3"/>')
    # Spine through the stages, joined by the converged stream
    out.append(f'<path d="M{spine_x} {stage_centre(0):.0f}V{stage_centre(3):.0f}" stroke="url(#spine)" '
               f'stroke-width="7"/>')
    out.append(f'<path d="M{qx} {qy:.0f}H{spine_x}" stroke="#E9FAFF" stroke-width="10" stroke-linecap="round"/>')
    out.append(f'<circle cx="{qx}" cy="{qy:.0f}" r="70" fill="{CYAN}" opacity=".45" filter="url(#glowWide)"/>')
    out.append(f'<circle cx="{qx}" cy="{qy:.0f}" r="24" fill="#FFFFFF"/>')
    for i, (name, title, l1, l2) in enumerate(STAGES):
        cy = stage_centre(i)
        decide = i == 3
        if decide:
            out.append(f'<circle cx="{spine_x}" cy="{cy:.0f}" r="70" fill="url(#gold)"/>')
            out.append(icon(name, spine_x, cy, 76, NAVY, 6.5))
        else:
            out.append(f'<circle cx="{spine_x}" cy="{cy:.0f}" r="70" fill="#163A62" stroke="#BFEFFF" '
                       f'stroke-opacity=".6" stroke-width="3"/>')
            out.append(icon(name, spine_x, cy, 72, "#FFFFFF", 6.5))
        tx = FLOW_X0 + 250
        out.append(text(tx, cy - 47, title, 58, weight=600, fill=GOLD_SOFT if decide else "#FFFFFF", spacing=7))
        out.append(text(tx, cy + 25, l1, 46, fill=ON_DARK))
        out.append(text(tx, cy + 85, l2, 46, fill=ON_DARK))
    return "\n".join(out)


OPTIONS = [
    ("Floor", "Break-even at today’s material cost", 0.52, SLATE),
    ("Target", "Best balance of margin and risk", 0.70, "url(#gold)"),
    ("Stretch", "If capacity and payment terms allow", 0.86, "#6FA3D2"),
]


def decision_card() -> str:
    x0, x1 = CARD_X0, CARD_X1
    w = x1 - x0
    cx = (x0 + x1) / 2
    px = x0 + 64
    decide_y = stage_centre(3)
    out = [column_label(x0, "03", "ONE DECISION, YOURS")]
    # Gold link from "You decide" to the buttons
    out.append(f'<path d="M{FLOW_X1 - 22} {decide_y:.0f}H{x0 - 14}" stroke="{GOLD_SOFT}" stroke-width="26" '
               f'opacity=".5" filter="url(#glow)"/>')
    out.append(f'<path d="M{FLOW_X1 - 22} {decide_y:.0f}H{x0 - 18}" stroke="{GOLD_SOFT}" stroke-width="8" '
               f'stroke-linecap="round"/>')
    out.append(f'<path d="M{x0 - 44} {decide_y - 22:.0f}l24 22-24 22" fill="none" stroke="{GOLD_SOFT}" '
               f'stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>')
    # Card
    out.append(f'<rect x="{x0 + 30}" y="{TOP + 60}" width="{w - 60}" height="{BOT - TOP - 20}" rx="48" '
               f'fill="#04101F" opacity=".55" filter="url(#shadow)"/>')
    out.append(f'<rect x="{x0}" y="{TOP}" width="{w}" height="{BOT - TOP}" rx="48" fill="#FFFFFF" '
               f'fill-opacity=".95" stroke="#FFFFFF" stroke-width="3"/>')
    # Heading
    out.append(icon("chart", px + 26, TOP + 116, 52, BLUE, 5))
    out.append(text(px + 76, TOP + 132, "SIMULATE OPTIONS", 40, weight=600, fill=BLUE, spacing=6))
    out.append(text(px, TOP + 244, "What should we charge?", 76, family=SERIF, weight=700))
    out.append(text(px, TOP + 312, "Customer enquiry · this month’s data", 42, fill=MUTED))
    out.append(f'<path d="M{px} {TOP + 368}H{x1 - 64}" stroke="#E2E7EE" stroke-width="3"/>')
    # Price options
    track = w - 2 * 64 - 2 * 46
    for r, (name, caption, share, colour) in enumerate(OPTIONS):
        y = TOP + 395 + r * 228
        if r == 1:
            out.append(f'<rect x="{px - 24}" y="{y}" width="{w - 128 + 48}" height="210" rx="30" fill="#FBF5E7" '
                       f'stroke="#E7D3A0" stroke-width="3"/>')
            bx1 = x1 - 64 - 22  # badge: star, then the 254-unit-wide label
            bx0 = bx1 - 358
            out.append(f'<rect x="{bx0}" y="{y + 28}" width="358" height="66" rx="33" fill="url(#gold)"/>')
            out.append(f'<path d="{star(bx0 + 45, y + 61, 19, 8)}" fill="#FFFFFF"/>')
            out.append(text(bx0 + 76, y + 74, "Recommended", 36, weight=600, fill="#FFFFFF"))
        out.append(text(px + 22, y + 80, name, 54, weight=600))
        out.append(text(px + 22, y + 134, caption, 40, fill=MUTED))
        out.append(f'<rect x="{px + 22}" y="{y + 160}" width="{track}" height="16" rx="8" fill="#E8EDF3"/>')
        out.append(f'<rect x="{px + 22}" y="{y + 160}" width="{track * share:.0f}" height="16" rx="8" fill="{colour}"/>')
    # Evidence
    ey = TOP + 1180
    out.append(icon("clip", px + 26, ey - 16, 52, NAVY, 5))
    out.append(text(px + 76, ey, "Every figure cites its source rows", 44, weight=600))
    out.append(text(px + 76, ey + 62, "Material cost · Capacity · Receivables", 40, fill=MUTED))
    out.append(f'<path d="M{px} {ey + 128}H{x1 - 64}" stroke="#E2E7EE" stroke-width="3"/>')
    # Buttons, level with "You decide"
    bw = (w - 128 - 30) / 2
    by = decide_y - 60
    out.append(f'<rect x="{px}" y="{by:.0f}" width="{bw:.0f}" height="120" rx="60" fill="{TEAL}"/>')
    out.append(icon("check", px + bw / 2 - 118, decide_y, 54, "#FFFFFF", 7))
    out.append(text(px + bw / 2 + 28, decide_y + 16, "Approve", 46, weight=600, fill="#FFFFFF", anchor="middle"))
    rx0 = px + bw + 30
    out.append(f'<rect x="{rx0:.0f}" y="{by:.0f}" width="{bw:.0f}" height="120" rx="60" fill="#FFFFFF" '
               f'stroke="{CORAL}" stroke-width="4"/>')
    out.append(icon("cross", rx0 + bw / 2 - 100, decide_y, 46, CORAL, 7))
    out.append(text(rx0 + bw / 2 + 28, decide_y + 16, "Reject", 46, weight=600, fill=CORAL, anchor="middle"))
    out.append(text(cx, decide_y + 136, "Nothing is written until a person approves.", 40, fill=MUTED,
                    anchor="middle"))
    return "\n".join(out)


# ---------- Value band ----------

VALUES = [
    ("clock", "Faster", "Every department reviewed", 'in <tspan font-weight="700" fill="#0B1F3A">53.4 s</tspan> on a real model'),
    ("alert", "Lower Risk", "Loss-making orders flagged", "the month they happen"),
    ("trace", "Better Decisions", "Every number traces to", "file · sheet · row · column"),
    ("tag", "Higher Value", "No evidence, no price:", "quotes backed by your data"),
]


def value_band() -> str:
    col = (W - 2 * M) / 4
    out = []
    for k, (name, title, l1, l2) in enumerate(VALUES):
        cx = M + col * (k + 0.5)
        if k:
            out.append(f'<path d="M{M + col * k:.0f} 3910V4280" stroke="#D8D2C4" stroke-width="3"/>')
        out.append(f'<circle cx="{cx:.0f}" cy="3975" r="82" fill="#FFFFFF" fill-opacity=".6" stroke="{GOLD}" '
                   f'stroke-opacity=".7" stroke-width="3"/>')
        out.append(icon(name, cx, 3975, 92, NAVY, 5.5))
        out.append(text(cx, 4140, title, 70, weight=600, anchor="middle"))
        out.append(text(cx, 4212, l1, 46, fill="#4A5872", anchor="middle"))
        out.append(text(cx, 4272, l2, 46, fill="#4A5872", anchor="middle", raw=True))
    return "\n".join(out)


# ---------- Footer: the strait, the credits, the QR codes ----------

def qr_paths() -> list[str]:
    found = re.findall(r'aria-label="QR code"><path class="qrline" stroke="#0b1b3a" d="([^"]+)"',
                       OLD_POSTER.read_text(encoding="utf-8"))
    if len(found) != 2:
        raise SystemExit(f"expected two QR codes in {OLD_POSTER.name}, found {len(found)}")
    return found


def footer() -> str:
    out = [
        f'<path d="M{M} 4395H{W - M}" stroke="#DDD6C7" stroke-width="3"/>',
        text(M, 4535, 'Just as the Strait of Malacca connects <tspan font-style="italic">the world</tspan> '
                      'and helped Singapore flourish,', 62, family=SERIF, weight=400, raw=True),
        text(M, 4625, 'we connect your business to <tspan font-style="italic" fill="#A9823A">better decisions'
                      '</tspan>.', 62, family=SERIF, weight=400, raw=True),
        text(M, 4742, 'Team CONFLUX<tspan font-size="28" dy="-16">4</tspan><tspan dy="16"> · Show Me Your Agents 2026'
                      ' · Running on AWS</tspan>', 46, fill=MUTED, raw=True),
        text(M, 4808, "Sample data is synthetic, modelled on a real business’s templates.", 46, fill=MUTED),
    ]
    size, gap = 340, 44
    for j, (d, label) in enumerate(zip(qr_paths(), ("Try it", "Code"))):
        x = W - M - size - (1 - j) * (size + gap)
        y = 4440
        out.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="26" fill="#FFFFFF" '
                   f'stroke="#DDD6C7" stroke-width="3"/>')
        out.append(f'<svg x="{x + 24}" y="{y + 24}" width="{size - 48}" height="{size - 48}" viewBox="0 0 33 33" '
                   f'shape-rendering="crispEdges"><path stroke="{NAVY}" d="{d}"/></svg>')
        out.append(text(x + size / 2, y + size + 66, label, 46, weight=600, anchor="middle"))
    return "\n".join(out)


# ---------- Assembly ----------

def build_svg(bleed: bool) -> str:
    rng = random.Random(1358)
    b = BLEED if bleed else 0
    vb = f"{-b} {-b} {W + 2 * b} {H + 2 * b}"
    size_mm = (594 + (6 if bleed else 0), 841 + (6 if bleed else 0))
    body = "\n".join([defs(), background(rng), header(), departments(), flow_panel(), decision_card(),
                      value_band(), footer()])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="poster" viewBox="{vb}" '
            f'width="{size_mm[0]}mm" height="{size_mm[1]}mm" data-px="{W + 2 * b}x{H + 2 * b}">\n'
            f'<title>BridgeFlow AI · When flows converge, value moves.</title>\n{body}\n</svg>\n')


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>BridgeFlow AI · A1 booth poster (Confluence)</title>
<!--
  Generated by build_flow_poster.py; edit the script, not this file.
  Print from Chrome: Save as PDF, Margins "None", Background graphics on, Scale 100.
-->
<style>
  @page {{ size: {w_mm}mm {h_mm}mm; margin: 0; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ background: #1d2533; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .stage {{ min-height: 100vh; display: flex; justify-content: center; align-items: flex-start; padding: 24px; }}
  svg.poster {{
    display: block; height: auto;
    width: min(calc(100vw - 48px), calc((100vh - 48px) * {ratio}));
    box-shadow: 0 30px 80px rgba(0, 0, 0, .45);
  }}
  /* ?export renders the poster at exactly one CSS pixel per unit, for the PNG screenshot */
  .export .stage {{ padding: 0; display: block; }}
  .export svg.poster {{ width: {w_px}px; height: {h_px}px; box-shadow: none; }}
  @media print {{
    html, body {{ background: none; }}
    .stage {{ padding: 0; display: block; }}
    svg.poster {{ width: {w_mm}mm; height: {h_mm}mm; box-shadow: none; }}
  }}
</style>
<script>if (location.search.includes('export')) document.documentElement.classList.add('export');</script>
</head>
<body>
<div class="stage">
{svg}</div>
</body>
</html>
"""


def export(html_path: Path, png_path: Path, pdf_path: Path, w_px: int, h_px: int) -> None:
    url = html_path.as_uri()
    common = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
              "--virtual-time-budget=3000"]
    subprocess.run(common + [f"--window-size={w_px},{h_px}", f"--screenshot={png_path}", url + "?export"],
                   check=True, capture_output=True)
    subprocess.run(common + ["--no-pdf-header-footer", "--print-to-pdf-no-header", f"--print-to-pdf={pdf_path}",
                             url], check=True, capture_output=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", action="store_true", help="also write PNG and PDF with headless Chrome")
    ap.add_argument("--bleed", action="store_true", help="add 3 mm bleed on every side")
    args = ap.parse_args()

    stem = "bridgeflow-a1-flow" + ("-bleed" if args.bleed else "")
    svg = build_svg(args.bleed)
    b = BLEED if args.bleed else 0
    w_px, h_px = W + 2 * b, H + 2 * b
    w_mm, h_mm = 594 + (6 if args.bleed else 0), 841 + (6 if args.bleed else 0)

    svg_path, html_path = HERE / f"{stem}.svg", HERE / f"{stem}.html"
    svg_path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + svg, encoding="utf-8")
    html_path.write_text(HTML.format(svg=svg, w_mm=w_mm, h_mm=h_mm, w_px=w_px, h_px=h_px,
                                     ratio=f"{w_px / h_px:.6f}"), encoding="utf-8")
    print(f"wrote {svg_path.name}, {html_path.name}")
    if args.export:
        png_path, pdf_path = HERE / f"{stem}.png", HERE / f"{stem}.pdf"
        export(html_path, png_path, pdf_path, w_px, h_px)
        print(f"wrote {png_path.name} ({w_px} x {h_px}), {pdf_path.name} ({w_mm} x {h_mm} mm)")


if __name__ == "__main__":
    main()
