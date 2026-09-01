---
name: AeroSkills Design System
north_star: "Aerospace blueprint: warm vellum (light) or classic blueprint-blue (dark) drafting paper where every mark is graphite or bone-white linework, one mint survey-marker accent, and engineering-drawing conventions (title block, dimension lines, station marks) carried into a skills-library brand."
theme: dual
colors:
  light:
    - hex: "#f3f1ec"
      name: Warm Vellum
      role: "Canvas — warm drafting paper, never pure white"
      group: neutral
    - hex: "#faf9f5"
      name: Paper Surface
      role: "Card surfaces, drawing frame, title block"
      group: neutral
    - hex: "#171717"
      name: Ink Black
      role: "Primary text, airfoil linework, chips — slightly warm graphite"
      group: neutral
    - hex: "#5c5c5c"
      name: Pencil
      role: "Secondary text, telemetry, dimension labels"
      group: neutral
    - hex: "#a3a3a3"
      name: Faint Graphite
      role: "Grid lines, station marks, muted labels, chip borders"
      group: neutral
    - hex: "#9fe870"
      name: Survey Mint
      role: "THE single chromatic accent — camber line, datum markers, tags. Never large fills"
      group: accent
  dark:
    - hex: "#0d1b33"
      name: Blueprint Blue
      role: "Canvas — classic blueprint paper, deep indigo-navy"
      group: neutral
    - hex: "#0a1730"
      name: Deep Paper
      role: "Card surfaces, drawing frame, title block"
      group: neutral
    - hex: "#dfe8f5"
      name: Bone White
      role: "Primary text, linework, chips — the blueprint line color"
      group: neutral
    - hex: "#5f7ba8"
      name: Blueprint Muted
      role: "Secondary text, telemetry, dimension labels"
      group: neutral
    - hex: "#3a5a8f"
      name: Blueprint Border
      role: "Chip borders, muted structural lines"
      group: neutral
    - hex: "#9fe870"
      name: Survey Mint
      role: "THE single chromatic accent — camber line, datum markers. Never large fills"
      group: accent
fonts:
  display: "Barlow Condensed (substitute: DIN Condensed, Arial Narrow) — uppercase, 700, wide tracking for 'Aero'"
  serif: "Instrument Serif (substitute: Georgia italic) — one editorial accent word ('Skills') — the refero Subframe signature"
  mono: "JetBrains Mono (substitute: IBM Plex Mono, Menlo) — ALL labels, telemetry, chips, title block"
dos:
  - "Use the engineering blueprint as the visual language: drafting grid, hairline frames, title block, dimension lines, station marks"
  - "Carry a REAL engineering artifact as the hero (NACA 2412 airfoil computed from the actual camber/thickness equations, 1.8x vertical exaggeration per drafting convention)"
  - "Warm vellum canvas (light) or classic blueprint blue (dark) — never pure black or pure white"
  - "One mint accent (#9fe870) used surgically: camber line, datum markers, tags — the survey-marker role"
  - "Set every label in uppercase mono with wide tracking — instrument-panel readout"
  - "Ghost-outline chips in ink/bone — never filled"
  - "Editorial type move: huge condensed 'Aero' + italic serif 'Skills' (refero Subframe signature)"
  - "Title block bottom-right with real drafting fields: scale, sheet, class"
donts:
  - "Never use gradients — the AI rainbow-sweep look is banned (founder 2026-09-01)"
  - "Never add shadows, glows, or elevation"
  - "Never introduce a second chromatic accent — mint is alone"
  - "Never use pure #000000 or #ffffff as canvas"
  - "Never fill buttons or chips — ghosts only"
  - "Never center body text"
  - "Never reuse the void-black+white-text minimalism that founder rejected as 'too basic'"
source: "refero.design — Subframe (graphite blueprint on warm vellum), INVERSA (topographic field terminal, survey-marker accent), SpaceX (instrument-panel type), Dayos (mint tags) — founder-selected 2026-09-01; design-taste-frontend skill (anti-slop)"
applies_to:
  - docs/logo-mark.png / logo-full.png (FOUNDER-SUPPLIED raster mark, 2026-09-01 — THE logo. Exempt from this design law and from the generator; never redesign or alter. logo-mark is the text-free emblem crop used in the README hero; logo-full keeps the baked-in wordmark for app-icon/social use)
  - docs/banner.svg / banner-dark.svg (GENERATED — scripts/gen_visuals.py, v5.1)
  - docs/how-it-works.svg / -dark (GENERATED — scripts/gen_visuals.py)
  - docs/domain-map.svg (light vellum, legacy)
  - docs/logo.svg / logo-dark.svg (GENERATED — scripts/gen_visuals.py)
  - docs/domain-radar.svg / -dark (GENERATED — scripts/gen_visuals.py)
  - docs/domain-polar.svg / -dark (GENERATED — scripts/gen_visuals.py)
  - docs/stats.svg / -dark (GENERATED — scripts/gen_visuals.py)
  - any future AeroSkills visual artifact
generated_note: >
  Every chart, the logo, and every number quoted in README.md is emitted by
  scripts/gen_visuals.py from the tree at HEAD (make visuals). Never edit
  those SVGs or the README gen-blocks by hand — change the generator and
  rerun. CI enforces freshness via make visuals-check.
