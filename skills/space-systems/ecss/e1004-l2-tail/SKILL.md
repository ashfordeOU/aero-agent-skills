---
name: e1004-l2-tail
description: "Use when defining the radiation environment for a Sun-Earth L2 or deep-magnetotail mission under ECSS-E-ST-10-04C clause 9.2.7: define which unshielded galactic-cosmic-ray and solar-energetic-particle components apply once the trapped-belt boundary is left behind, flag orbit segments that cross the magnetotail plasma sheet or lobes so a supplemental charging environment is added, and verify the resulting environment definition is complete before it feeds the radiation environment specification (RES). Trigger: L2, Lagrange point, deep magnetotail, magnetotail plasma sheet, magnetotail lobe, deep-space radiation environment, unshielded GCR, unshielded SEP, e-st-10-04, ecss."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10-04c, l2, magnetotail, radiation-environment, gcr, sep]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS L2 / Deep Magnetotail Radiation Environment (space-systems/ecss/e1004-l2-tail)

Use when the task is defining the radiation environment for a mission
at the Sun-Earth L2 point or in the deep magnetotail under
ECSS-E-ST-10-04C clause 9.2.7: identifying which environment
components apply once the trapped radiation belts are left behind, and
flagging any orbit segments that need a supplemental magnetotail
charging environment.

## Domain quick reference

- L2 and the deep magnetotail sit far beyond the outer trapped
  radiation belt, so the long-term trapped-electron/proton belt
  models (AE/AP-family, IGE-2006, MEOv2, MOBE-DIC — owned by the
  sibling leaves e1004-trapped-leo, e1004-geo-ige, e1004-meo-meov2,
  e1004-trapped-proton-wc) do not apply there.
- Without the geomagnetic field to provide cutoff shielding (the
  Størmer-cutoff mechanism used for LEO in e1004-stormer), the full
  unshielded galactic-cosmic-ray spectrum (e1004-gcr) and the full
  unshielded solar-energetic-particle environment — proton fluence
  (e1004-sep-fluence), peak flux (e1004-sep-peakflux), and heavy-ion
  spectrum — apply directly at L2 and in the deep magnetotail.
- A halo or Lissajous orbit around L2 can still carry the spacecraft
  through the magnetotail's plasma sheet and lobes for parts of each
  orbit. Those crossings add a transient, lower-energy plasma-sheet
  energetic-electron population relevant to surface charging; this
  population is kept separate from the deep-space GCR/SEP dose
  baseline, not merged into it.
- The Annex I particle-radiation background material (carried by the
  reference-data leaf e1004-ref-particles) documents this outer-
  magnetosphere/L2 behaviour; this leaf turns that guidance into the
  per-segment component list that feeds the RES (e1004-rad-env-spec).

## Workflow

1. For each segment of the mission timeline, record its distance from
   Earth (in Earth radii) and whether it crosses the magnetotail
   plasma sheet or a magnetotail lobe.
2. Confirm each segment sits outside the trapped-belt boundary; a
   segment still inside the belts is out of this leaf's scope and
   belongs to the trapped-radiation leaves instead.
3. Classify each outside-the-belt segment as plain L2/deep-space,
   magnetotail lobe, or magnetotail plasma sheet (plasma sheet takes
   precedence when both crossings are flagged together).
4. Assign the unshielded GCR + SEP proton/heavy-ion component set to
   every segment; add the plasma-sheet energetic-electron charging
   component only to plasma-sheet segments.
5. Confirm geomagnetic shielding is not applied anywhere in this
   region — every segment's environment is the full unshielded
   spectrum, unlike the LEO Størmer-cutoff treatment.
6. Verify the environment definition is complete: every segment carries
   its full required component set and no segment claims geomagnetic
   shielding before handing the definition to the RES.

## Pitfalls

- Applying a trapped-belt model (AE/AP, IGE-2006, MEOv2, MOBE-DIC) to
  an L2 or deep-magnetotail segment where it does not apply.
- Applying a geomagnetic-cutoff (Størmer) shielding reduction to the
  GCR or SEP spectrum at L2 or in the deep magnetotail, where no such
  shielding exists.
- Folding the transient magnetotail plasma-sheet charging population
  into the deep-space GCR/SEP dose baseline instead of tracking it as
  a separate, segment-specific supplement.
- Missing a plasma-sheet or lobe crossing in the orbit timeline and
  under-specifying the environment for that segment.

## Behavior contract (gate 3)

The segment classification, required-component, shielding, and
definition-completeness logic is exercised by the gate 3 contract
test: scripts/test_e1004_l2_tail.py against
scripts/e1004_l2_tail_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_l2_tail.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
