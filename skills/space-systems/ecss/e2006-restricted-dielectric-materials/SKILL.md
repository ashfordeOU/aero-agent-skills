---
name: e2006-restricted-dielectric-materials
description: "Use when determine whether a restricted insulating material may be carried on a spacecraft external surface under ECSS-E-ST-20-06C clause 6.3.3.6: match every externally exposed item against the restricted-dielectric register and against the bulk-resistivity and surface-resistivity thresholds that make an unregistered material restricted in its own right, exempt only a negligible exposed area, then permit the item solely on a three-dimensional charging-simulation waiver that models the item geometry, bounds the worst-case environment including eclipse-entry, and predicts a differential-potential at or below the discharge-onset threshold. Trigger: ecss, e-st-20-electrical-scope, restricted-dielectric, external-dielectric-exposure, three-dimensional-charging-simulation, differential-potential, discharge-onset, bulk-resistivity, dielectric-waiver."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-restricted-dielectric-materials, restricted-dielectric, external-dielectric-exposure, three-dimensional-charging-simulation, differential-potential, discharge-onset, bulk-resistivity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrostatic Design — Restricted Dielectric Materials (space-systems/ecss/e2006-restricted-dielectric-materials)

Use when the task is the clause 6.3.3.6 obligation of ECSS-E-ST-20-06C: a set
of highly insulating materials is kept off spacecraft external surfaces, and
the only route back on is a three-dimensional charging simulation showing the
installed item, in its own geometry, stays below the discharge-onset
threshold.

## Domain quick reference

- Restriction has two independent doors. A material family named in the
  restricted-dielectric register is restricted on sight; an unregistered
  material becomes restricted once its measured bulk resistivity or surface
  resistivity crosses the threshold, because the clause is about how the
  surface behaves electrostatically, not about the name on the datasheet.
  The module register holds uncoated-polyimide-film,
  uncoated-fused-silica-cover, polytetrafluoroethylene-sheet,
  uncoated-glass-fibre-laminate and unconditioned-silicone-adhesive.
- Two states escape the clause without a waiver: an internal item, which sees
  no ambient flux on an external face, and an item whose exposed area is
  negligible, a square centimetre in the module default, which cannot collect
  enough charge to matter.
- The waiver is specifically three-dimensional. A one- or two-dimensional
  reduction cannot represent the edges, the shadowing and the adjacent
  conductive returns that set the real surface potential of an installed
  dielectric, so a reduced-dimension run is rejected outright rather than
  accepted with a caveat.
- A waiver is only as good as its scope: it has to name the item in its
  modelled geometry, declare an environment case that bounds the worst case,
  and cover the eclipse-entry transient, which is where a sunlit dielectric
  loses its photoemission return and charges fastest.
- The pass criterion is the differential potential between the dielectric
  surface and structure, taken as a magnitude so a negative surface potential
  against a biased structure is handled, compared against the discharge-onset
  threshold a project may tighten but not relax by default.

## Workflow

1. Normalize every item on the external inventory: name, material, exposure,
   exposed area, and the measured resistivities where they exist, inheriting
   register values when they do not. Reject an unknown exposure value, a
   negative area, and an internal item that still declares an exposed area.
2. Decide restriction: skip internal items and negligible exposed areas, then
   collect every reason the item is restricted, register membership and each
   resistivity threshold crossed. An item with no reason needs no waiver.
3. Validate the waiver record on its own terms before judging it: known
   dimensionality, a list of modelled item names, an environment case, the
   explicit worst-case and eclipse-entry flags, and finite potentials. Reject
   an unknown dimensionality instead of downgrading it.
4. Compute the differential potential as the magnitude of the surface-to-
   structure difference and compare it with the discharge-onset threshold.
   Treat a prediction sitting exactly on the threshold as compliant: the
   value is a difference of two potentials and can land a few units in the
   last place above a threshold it physically meets.
5. Raise a finding per shortfall: no waiver, a reduced-dimension run, the item
   missing from the modelled geometry, an environment that does not bound the
   worst case, no eclipse-entry coverage, and a potential past onset.
6. Aggregate across the inventory. The external surface is compliant only
   when no item is barred; report the barred item names alongside the
   findings so the open work is visible per item.

## Pitfalls

- Reading a material as acceptable because it is not in the register. The
  register is a list of known offenders, not the definition of a restricted
  dielectric; an unregistered film above the resistivity thresholds is
  restricted on its measured properties alone.
- Accepting a two-dimensional or axisymmetric run because it was cheaper and
  covered the same environment. The dimension that was dropped is the one
  carrying the edge and shadowing behaviour that drives the installed
  potential, so the environment fidelity does not compensate.
- Closing the waiver on a sunlit steady state. The eclipse-entry transient is
  the credible worst case for an external dielectric; a waiver silent on it
  has not shown the item is safe, whatever its illuminated prediction says.
- Comparing potentials as signed values. A surface at minus one thousand
  volts against a structure at minus eight hundred volts differs by two
  hundred, not by eighteen hundred, and a signed comparison flips the verdict
  on any biased structure.
- Relaxing the discharge-onset threshold to clear a prediction that sits
  exactly on it. The prediction already complies; the tolerance belongs on
  the comparison, as a named volt-scale tolerance, never on the threshold.

## Behavior contract (gate 3)

The restriction-register, resistivity-threshold, waiver-validation,
differential-potential and inventory-aggregation logic is exercised by the
gate 3 contract test:
scripts/test_e2006_restricted_dielectric_materials.py against
scripts/e2006_restricted_dielectric_materials_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_restricted_dielectric_materials.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
