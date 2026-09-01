---
name: AeroSkills Design System
north_star: "The repo wears the logo's universe: deep space navy, a paper plane's clean white geometry, and the logo's four hues — cyan orbit, violet sky, magenta cloud, orange exhaust — used as flat, disciplined accents over engineering-drawing conventions (mono uppercase labels, hairline frames, title blocks)."
theme: dual
logo:
  file: docs/logo-mark.png (+ docs/logo-full.png with baked wordmark)
  rule: "FOUNDER-SUPPLIED raster (2026-09-01) — THE logo. Never redesign, regenerate, or alter the artwork. logo-mark is the text-free emblem crop with rounded corners (r=96/640) used in the README hero; logo-full keeps the wordmark for app-icon/social use. Source: founder's aeroskills.png."
colors:
  dark:
    - hex: "#0a0d1e"
      name: Tile Navy
      role: "Canvas — sampled from the logo tile"
    - hex: "#111632"
      name: Deep Surface
      role: "Card surfaces, chips, title blocks"
    - hex: "#edf0fc"
      name: Star White
      role: "Primary text, linework, ghost outlines"
    - hex: "#8a93c4"
      name: Muted Slate
      role: "Secondary text, captions, dimension labels"
    - hex: "#2c3564"
      name: Faint Line
      role: "Grid lines, tracks, hairlines"
    - hex: "#38bdf8"
      name: Orbit Cyan
      role: "PRIMARY accent — main data series, terminal nodes"
    - hex: "#a78bfa"
      name: Sky Violet
      role: "Accent 2 — family cycle, group frames"
    - hex: "#f472b6"
      name: Cloud Magenta
      role: "Accent 3 — family cycle, group frames"
    - hex: "#fb923c"
      name: Exhaust Orange
      role: "Accent 4 — family cycle, stop-gates, warnings"
  light:
    - hex: "#f6f7fc"
      name: Cool Paper
      role: "Canvas"
    - hex: "#ffffff"
      name: Surface
      role: "Card surfaces, chips, title blocks"
    - hex: "#151a33"
      name: Space Ink
      role: "Primary text, linework"
    - hex: "#5a6289"
      name: Muted Slate
      role: "Secondary text"
    - hex: "#c6cce4"
      name: Faint Line
      role: "Grid lines, tracks"
    - hex: "#0891b2"
      name: Orbit Cyan (deep)
      role: "PRIMARY accent"
    - hex: "#7c3aed"
      name: Sky Violet (deep)
      role: "Accent 2"
    - hex: "#db2777"
      name: Cloud Magenta (deep)
      role: "Accent 3"
    - hex: "#ea580c"
      name: Exhaust Orange (deep)
      role: "Accent 4"
fonts:
  display: "Barlow Condensed (substitute: DIN Condensed, Arial Narrow) — uppercase, 700, chart titles and big numbers"
  mono: "JetBrains Mono (substitute: IBM Plex Mono, Menlo) — ALL labels, captions, chips, title blocks"
dos:
  - "Derive every accent from the logo's four hues; cycle cyan→violet→magenta→orange for per-family color"
  - "Flat fills only in charts — the logo may glow, the data may not"
  - "Keep engineering-drawing conventions: mono uppercase labels, hairline frames, corner station marks, title blocks with UNIT/SCALE/SHEET"
  - "Translucent data fills stay ≤0.16 over navy so hues never muddy"
  - "README stats are colorful TEXT (math \\color) and small flat badges — not framed image strips"
donts:
  - "Never alter the founder logo (crop bounds included) — it is the one non-generated visual"
  - "Never use gradients or shadows in generated charts"
  - "Never introduce a hue outside the logo palette (green stays only in pass/fail badge semantics)"
  - "Never quote roadmap/target figures in public-facing surfaces — current numbers only"
  - "Never hand-edit generated SVGs, DOMAINS.md, or README gen-blocks — change scripts/gen_visuals.py and run make visuals"
source: "Founder logo aeroskills.png (2026-09-01) + founder screenshot feedback rounds 1-3; supersedes the mint/vellum blueprint law (v3-v5.1)"
applies_to:
  - docs/logo-mark.png / logo-full.png (FOUNDER-SUPPLIED — exempt, canonical)
  - docs/domain-radar.svg / -dark (GENERATED — scripts/gen_visuals.py)
  - docs/domain-polar.svg / -dark (GENERATED)
  - docs/structure.svg / -dark (GENERATED — sunburst)
  - docs/how-it-works.svg / -dark (GENERATED — runtime flow)
  - docs/gates.svg / -dark (GENERATED — verification battery)
  - docs/skill-anatomy.svg / -dark (GENERATED — skill exploded view)
  - README.md gen-blocks + docs/DOMAINS.md (GENERATED)
generated_note: >
  Every chart and every number quoted in README.md is emitted by
  scripts/gen_visuals.py from the tree at HEAD (make visuals). CI enforces
  freshness via make visuals-check. Retired 2026-09-01: mint/vellum banner,
  SVG roundel logo, instrument strip, domain-map.svg.
