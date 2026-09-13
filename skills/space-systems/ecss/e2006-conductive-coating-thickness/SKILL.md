---
name: e2006-conductive-coating-thickness
description: "Use when verify that a conductive-coating on an externally exposed spacecraft surface still carries its electrostatic bleed path at end-of-life under ECSS-E-ST-20-06C clause 6.3.3.5: accumulate the depth each erosion mechanism removes across the mission lifetime, atomic-oxygen recession, ion-sputtering, particulate-abrasion and handling-wear, scale the sum by the erosion-uncertainty factor, subtract it from the as-deposited thickness, and check the surviving layer against both the coating continuity-floor and the end-of-life sheet-resistance ceiling, then report the as-deposited thickness the erosion budget actually demands. Trigger: ecss, e-st-20-electrical-scope, conductive-coating, coating-thickness-budget, atomic-oxygen-erosion, ion-sputtering, sheet-resistance, end-of-life-thickness, continuity-floor."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-conductive-coating-thickness, conductive-coating, coating-thickness-budget, atomic-oxygen-erosion, ion-sputtering, sheet-resistance, end-of-life-thickness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrostatic Design — Conductive-Coating Thickness (space-systems/ecss/e2006-conductive-coating-thickness)

Use when the task is the clause 6.3.3.5 obligation of ECSS-E-ST-20-06C: a
conductive coating that gives an external surface its charge-bleed path is
laid down thick enough to still conduct after everything the mission erodes
away, so the check is made at end-of-life, never at the coating shop.

## Domain quick reference

- A coating family carries two numbers: the bulk resistivity of the deposited
  layer, which turns a thickness into a sheet resistance, and the continuity
  floor, the thickness below which the film stops being a continuous
  conductive path regardless of what the resistivity arithmetic says. The
  module register holds both for indium-tin-oxide, vapour-deposited-aluminium,
  gold-flash, germanium-on-polyimide and conductive-black-paint.
- Erosion arrives by several mechanisms and they add. Atomic-oxygen recession
  is fluence times erosion yield; ion-sputtering is flux times sputter yield
  times exposure duration times atomic volume; particulate-abrasion and
  handling-wear are supplied as a linear rate per year. The summed depth is
  then scaled by an erosion-uncertainty factor covering model and environment
  spread, which may be raised but never taken below unity.
- Sheet resistance is bulk resistivity divided by thickness, so it climbs as
  the layer thins. Two independent floors therefore apply to the surviving
  layer: the continuity floor of the coating family, and the thickness that
  still meets the end-of-life sheet-resistance ceiling for an external bleed
  surface. The stricter of the two governs.
- The required as-deposited thickness is that governing end-of-life floor plus
  the whole budgeted recession. Reporting it turns a failed check into a
  design number rather than a verdict.
- A coating eroded through to zero has no sheet resistance at all; it is
  reported as unbounded and fails both checks, rather than dividing by zero.

## Workflow

1. Resolve the coating family in the register to get its bulk resistivity and
   continuity floor. Reject an unknown family instead of assuming a default.
2. Evaluate every erosion mechanism declared for the surface over the mission
   lifetime, rejecting an unknown mechanism type, a negative fluence or rate,
   a non-positive erosion yield and a non-positive atomic volume.
3. Sum the mechanism depths and multiply by the erosion-uncertainty factor to
   get the budgeted recession; keep the per-mechanism breakdown so the driving
   mechanism stays visible.
4. Subtract the budgeted recession from the as-deposited thickness to get the
   surviving end-of-life layer, floored at zero.
5. Compare the surviving layer with the continuity floor, and its sheet
   resistance with the end-of-life ceiling. Treat a layer sitting exactly on a
   floor as compliant: the surviving thickness is a subtraction and can land a
   few units in the last place under an exactly-satisfied floor.
6. Compute the required as-deposited thickness, the governing end-of-life
   floor plus the budgeted recession, and raise a finding when the actual
   as-deposited value falls short. The coating is compliant only when the
   finding list is empty.

## Pitfalls

- Verifying the coating at beginning-of-life. A sheet-resistance measurement
  taken on the as-deposited layer is the one number the clause does not ask
  for; the layer that has to conduct is the one left at end-of-life.
- Checking sheet resistance alone and ignoring the continuity floor. The
  resistivity arithmetic keeps returning a finite, comfortable sheet
  resistance for layers far too thin to be continuous, so a coating can read
  as passing while the film has broken into islands.
- Dropping a mechanism because its individual depth looks small. The floors
  are compared against the sum, and a handling-wear rate that looks like
  rounding on its own can be what pushes a marginal layer through the floor.
- Setting the erosion-uncertainty factor to unity because the environment
  model is the project baseline. The factor covers the spread of the yield and
  the fluence, not a disagreement about which model to use, and taking it
  below unity is rejected outright.
- Widening the continuity floor or the sheet-resistance ceiling to close a
  boundary case. A layer exactly on the floor is compliant already; the
  tolerance belongs on the comparison, as a named nanometre-scale tolerance,
  never on the limit.

## Behavior contract (gate 3)

The coating-register, per-mechanism recession, end-of-life-thickness,
sheet-resistance and required-as-deposited logic is exercised by the gate 3
contract test: scripts/test_e2006_conductive_coating_thickness.py against
scripts/e2006_conductive_coating_thickness_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_conductive_coating_thickness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
