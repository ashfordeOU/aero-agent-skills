---
name: material-selection
description: "Use when you must select a structural material for an aerospace component: compare candidate materials across the aluminum, titanium, steel, and composite families, compute Ashby-style selection indices (E/rho for tension stiffness, E^(1/2)/rho for beam bending, E^(1/3)/rho for panel bending, sigma/rho for strength-limited tension), and rank candidates by stiffness-to-weight and strength-to-weight. Covers design drivers: temperature limits, corrosion and galvanic coupling, cost and availability, fatigue, and damage tolerance. Produces a ranked candidate list and the index-based justification for the selection, with representative property values flagged for verification against MMPDS. Trigger: material selection, selection indices, stiffness-to-weight, strength-to-weight, specific stiffness, specific strength, aluminum, titanium, steel, composites."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: materials
  tags: [material-selection, selection-indices, stiffness-to-weight, strength-to-weight, specific-stiffness, specific-strength, aluminum-alloys, titanium-alloys, steels, composites, corrosion-resistance, temperature-limits, design-drivers, airframe-materials]
  version: 0.1.0
  author: AeroSkills
---

# Material Selection (structures/materials/material-selection)

Use when the task is structural material selection for an aerospace
component: material families, selection indices, stiffness-to-weight
and strength-to-weight ranking, temperature limits, corrosion, cost
and availability.

## Domain quick reference

- Material families in aerospace structures: aluminum 2xxx and 7xxx
  alloys, titanium alloys (6Al-4V the common grade), low-alloy
  steels (4340 class), and carbon-epoxy laminates.
- Selection indices (Ashby, Materials Selection in Mechanical
  Design) rank materials per unit weight for a fixed stiffness or
  strength target:
  - tension stiffness per weight: E / rho
  - beam bending stiffness per weight: E^(1/2) / rho
  - panel bending stiffness per weight: E^(1/3) / rho
  - tension strength per weight: sigma / rho
  - beam bending strength per weight: sigma^(2/3) / rho
  - panel bending strength per weight: sigma^(1/2) / rho
  with E the modulus, sigma the yield strength (tension allowable
  for a laminate), and rho the density.
- The exponent changes the winner: on tension stiffness per weight
  (E/rho) aluminum, titanium, and steel are close; on beam bending
  stiffness per weight (E^(1/2)/rho) aluminum beats steel by a wide
  margin; on strength per weight titanium beats aluminum.
- Representative band values (verify against MMPDS, AMS, or CMH-17
  before design use; MMPDS design-value tables are never reproduced
  here):
  - 2024-T3: rho 2.78 g/cm3, E 71.7 GPa, Fty 345 MPa, Tmax 150 C
  - 7075-T6: rho 2.80 g/cm3, E 71.7 GPa, Fty 503 MPa, Tmax 130 C
  - Ti-6Al-4V: rho 4.43 g/cm3, E 113.8 GPa, Fty 880 MPa, Tmax 315 C
  - 4340 steel: rho 7.85 g/cm3, E 200 GPa, Fty 1240 MPa, Tmax 370 C
  - carbon-epoxy laminate: rho 1.60 g/cm3, E 140 GPa, tension
    allowable 800 MPa, Tmax 120 C
- Design drivers beyond the index: temperature limits (aluminum
  loses strength above roughly 150 C, epoxy composites above
  roughly 120 C, titanium retains strength to roughly 315 C),
  corrosion and galvanic coupling (carbon fiber drives galvanic
  corrosion of adjacent aluminum), stress-corrosion cracking of
  7xxx alloys in the short-transverse direction, fatigue behavior,
  damage tolerance, lightning protection for non-conductive
  composites, cost, and availability or lead time.
- Cost reality: 4340 steel is cheap, aluminum is the baseline,
  titanium runs roughly 5-10 times aluminum per kg, carbon-epoxy
  raw material runs higher still. Indices ignore cost; cost screens
  after the ranking.

## Workflow

1. Define the load case and the failure mode. Tension stiffness
   selects on E/rho, beam bending on E^(1/2)/rho, panel bending on
   E^(1/3)/rho, strength-limited parts on sigma/rho (or the
   strength exponent for bending).
2. Gather property data for the candidates and verify the values
   against MMPDS or CMH-17.
3. Compute indices with selection_index for each candidate.
4. Rank with rank_materials.
5. Screen on temperature, corrosion, galvanic coupling, cost, and
   availability.
6. Confirm the deterministic checks with the contract test
   scripts/test_material_selection.py.

## Pitfalls

- Ranking on the wrong index: a bending-critical part must use
  E^(1/2)/rho, not E/rho; the ranking changes.
- Mixing units across candidates (E in GPa against rho in kg/m3).
  Keep rho in g/cm3, E in GPa, sigma in MPa.
- Using ultimate strength for one candidate and yield for another.
- Treating a unidirectional lamina modulus as isotropic plate
  stiffness.
- Ignoring the temperature limit: aluminum and epoxy parts derate
  well below engine or high-speed surface temperatures.
- Ignoring galvanic corrosion at carbon-epoxy to aluminum joints.
- Copying design-value tables from MMPDS; verify property values
  at the source and reproduce only representative bands.
- Using an index ranking as an allowable; indices screen, they do
  not certify.

## Behavior contract (gate 3)

The selection index, ranking, temperature, corrosion, cost, and
family logic is exercised by the gate 3 contract test:
scripts/test_material_selection.py against
scripts/material_selection_logic.py (stdlib unittest, offline).
Run:
python3 skills/structures/materials/material-selection/scripts/test_material_selection.py

## Compliance

- Standards referenced, not reproduced: MMPDS is proprietary (SAE,
  successor to public-domain MIL-HDBK-5); name + paraphrase + link
  only per standards-map.yaml; never reproduce design-value tables.
- Selection index methodology is common engineering knowledge
  (Ashby), summary-only.
- compliance: STANDARDS-REF, gated: false.
