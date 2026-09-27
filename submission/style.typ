// Shared layout for the BridgeFlow AI submission documents.

#let accent = rgb("#1f3a5f")
#let ink = rgb("#1b1f24")
#let muted = rgb("#5b6470")
#let rule-color = rgb("#d6dae0")
#let panel = rgb("#f4f6f8")

#let sans = ("Helvetica Neue", "Helvetica", "Arial")
#let serif = ("Charter", "Libertinus Serif")

#let meta = (
  team: "CA3WTLPW",
  event: "Show Me Your Agents Hackathon · NUS-ISS",
  date: "September 2026",
  live: "https://47.130.178.176.sslip.io",
  portal: "https://portal.47.130.178.176.sslip.io",
  repo: "https://github.com/EricWang1358/BridgeFlow-AI",
)

// Highlighted fact: light panel, thin accent rule on the left.
#let fact(body) = block(
  width: 100%,
  fill: panel,
  inset: (x: 11pt, y: 9pt),
  stroke: (left: 2pt + accent),
)[#body]

#let meta-row(label, value) = (
  text(font: sans, size: 8pt, fill: muted, weight: "medium", tracking: 0.04em)[#upper(label)],
  value,
)

#let title-block(kind, subtitle, companion) = block(width: 100%, below: 1.6em)[
  #text(font: sans, size: 8.5pt, fill: accent, weight: "bold", tracking: 0.12em)[#upper(kind)]
  #v(6pt, weak: true)
  #text(font: sans, size: 24pt, weight: "bold", fill: ink)[BridgeFlow AI]
  #v(7pt, weak: true)
  #text(size: 12pt, fill: muted)[#subtitle]
  #v(12pt, weak: true)
  #line(length: 100%, stroke: 0.9pt + accent)
  #v(8pt, weak: true)
  #set text(size: 9.3pt)
  #grid(
    columns: (2.9cm, 1fr),
    row-gutter: 6.5pt,
    align: (left + horizon, left + horizon),
    ..meta-row("Team code", strong(meta.team)),
    ..meta-row("Event", [#meta.event · #meta.date]),
    ..meta-row("Live demo", link(meta.live)),
    ..meta-row("Sign-in portal", link(meta.portal)),
    ..meta-row("Repository", [#link(meta.repo)[github.com/EricWang1358/BridgeFlow-AI] #text(fill: muted)[(private; access on request)]]),
    ..meta-row("Companion", companion),
  )
  #v(8pt, weak: true)
  #line(length: 100%, stroke: 0.4pt + rule-color)
]

#let doc(kind: "", subtitle: "", companion: [], body) = {
  set document(title: "BridgeFlow AI — " + kind, author: "Team " + meta.team)
  set page(
    paper: "a4",
    margin: (x: 2.2cm, top: 2.5cm, bottom: 2.2cm),
    header: context {
      if counter(page).get().first() > 1 {
        set text(font: sans, size: 7.8pt, fill: muted)
        grid(columns: (1fr, auto), [BridgeFlow AI · #kind], [Team #meta.team])
        v(-5pt)
        line(length: 100%, stroke: 0.4pt + rule-color)
      }
    },
    footer: context {
      set text(font: sans, size: 7.8pt, fill: muted)
      align(center, counter(page).display("1 / 1", both: true))
    },
  )

  set text(font: serif, size: 10.3pt, lang: "en", fill: ink)
  set par(justify: true, leading: 0.66em, spacing: 1em)
  set list(indent: 0.3em, body-indent: 0.6em, marker: text(fill: accent)[•])
  set enum(indent: 0.3em, body-indent: 0.6em)
  set heading(numbering: "1.1")
  set strong(delta: 250)

  show heading: set text(font: sans, fill: accent)
  show heading.where(level: 1): it => block(above: 1.7em, below: 0.85em, text(size: 13pt, weight: "bold", it))
  show heading.where(level: 2): it => block(above: 1.3em, below: 0.65em, text(size: 10.8pt, weight: "bold", fill: ink, it))

  show link: set text(fill: accent)
  show raw: set text(font: ("Menlo", "DejaVu Sans Mono"), size: 0.84em)
  show raw.where(block: true): it => block(width: 100%, fill: panel, inset: 10pt, it)

  set table(
    inset: (x: 6pt, y: 5pt),
    stroke: (x, y) => (
      top: if y == 0 { 0.8pt + ink } else if y == 1 { 0.6pt + ink } else { 0.4pt + rule-color },
    ),
    fill: (x, y) => if y == 0 { panel },
  )
  show table: it => block(width: 100%, stroke: (bottom: 0.8pt + ink), it)
  show table: set text(size: 9.2pt)
  show table: set par(justify: false, leading: 0.55em)
  show table.cell.where(y: 0): set text(font: sans, size: 8.6pt)

  title-block(kind, subtitle, companion)
  body
}
