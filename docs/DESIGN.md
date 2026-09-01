---
name: AeroSkills Design System
north_star: "Mission control viewport: void-black instrument panel where star-white tracked type reads like telemetry and every control is a hairline ghost outline."
theme: dark
colors:
  - hex: "#000000"
    name: Void Black
    role: "Canvas for every section — no other background surface"
    group: neutral
  - hex: "#f0f0fa"
    name: Star White
    role: "All text, headings, icons, borders — the sole foreground; cool tint reads as instrument light, not paper"
    group: neutral
  - hex: "#545457"
    name: Dim Steel
    role: "Secondary labels, muted telemetry, disabled states"
    group: neutral
  - hex: "#1a1a1e"
    name: Hairline
    role: "Structural frames, section dividers — barely visible against black"
    group: neutral
  - hex: "#3c3d3e"
    name: Ghost Border
    role: "Chip/button outlines, lower-emphasis than star white"
    group: neutral
  - hex: "#cececf"
    name: Chalk
    role: "Secondary text inside chips, table cells"
    group: neutral
fonts:
  display: "Barlow Condensed (substitute: DIN Condensed, Arial Narrow) — uppercase, 700, wide tracking"
  mono: "JetBrains Mono (substitute: IBM Plex Mono, Menlo) — all labels, telemetry, chips"
dos:
  - "Use void black #000000 as the canvas — never a colored or gradient background"
  - "Set every label in uppercase with wide letter-spacing (3-5px at 11-13px) — instrument-panel readout"
  - "Build chips/buttons as 1px ghost outlines in #f0f0fa (primary) or #3c3d3e (secondary) — never filled"
  - "Use hairline frames (#1a1a1e, 1px) for panel edges and card boundaries"
  - "Keep telemetry lines in mono 10-13px — coordinates, counts, versions"
  - "Left-align everything — mission-log reading flow"
donts:
  - "Never use gradients — the AI rainbow-sweep look is banned (founder 2026-09-01)"
  - "Never add shadows, glows, or elevation — depth comes from type scale and hairlines"
  - "Never introduce chromatic accents or colored card fills — monochrome by design"
  - "Never fill buttons — ghosts only"
  - "Never center body text"
  - "Never use editorial/humanist warmth fonts — industrial geometric + mono only"
source: "refero.design — SpaceX (mission control), INVERSA (topographic field terminal), Dayos (editorial brutalist) — founder-selected 2026-09-01"
applies_to:
  - docs/banner.svg
  - docs/banner-dark.svg
  - docs/domain-map.svg
  - any future AeroSkills visual artifact
