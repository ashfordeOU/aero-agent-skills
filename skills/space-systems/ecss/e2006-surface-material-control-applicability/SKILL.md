---
name: e2006-surface-material-control-applicability
description: "Use when determine whether the surface-material electrical-control rules of ECSS-E-ST-20-06C clause 6.1.1 apply to a spacecraft external item: categorize every item as plasma-exposed, partially-shielded or internal from its shield-coverage-fraction and ambient-plasma view, rank the orbit-regime severity of the ambient-plasma environment, screen the surface-resistivity and dielectric-thickness values that separate a controlled-conductive surface from a floating-dielectric surface, size the charge-bleed-path resistance from the exposed surface to structure-ground, and return a per-item applicability verdict plus the open findings that block a surface-material-control compliance statement. Trigger: ecss-e-st-20-06c, clause-6-1-1, plasma-exposed-surface, surface-material-electrical-control, charge-bleed-path, surface-resistivity-screening, floating-dielectric-surface, structure-ground-bonding, orbit-regime-severity."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-surface-material-control-applicability, ecss-e-st-20-06c, plasma-exposed-surface, surface-material-electrical-control, charge-bleed-path, floating-dielectric-surface, structure-ground-bonding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Surface-Material Control Applicability (space-systems/ecss/e2006-surface-material-control-applicability)

Use when the task is deciding where the surface-material
electrical-control rules of ECSS-E-ST-20-06C clause 6.1.1 bite -- which
external items sit in the ambient-plasma environment, what
electrical behaviour their outer material must therefore exhibit, and
which items fall outside the rule entirely.

## Domain quick reference

- Clause 6.1.1 exists because an outer material that cannot move
  collected charge away accumulates it. A plasma-exposed surface
  collects electrons and ions from the ambient environment; if the
  material is a good insulator, the collected charge stays where it
  landed and the surface floats to a potential set by the local
  current balance rather than by the spacecraft structure. Neighbouring
  surfaces then sit at different potentials, and the resulting
  differential-potential is what eventually drives an
  electrostatic-discharge. The rule therefore targets the *electrical
  behaviour* of the exposed material, not its thermo-optical or
  mechanical properties.
- Applicability is a two-part question. First, exposure: an item is
  plasma-exposed when it is external, has a view to the ambient
  environment, and is not fully covered by a shield; it is
  partially-shielded when a shield covers part of it; it is internal
  when it is inside the structure, has no ambient view, or is fully
  covered. Only the first two categories are in scope for a
  surface-material-control requirement.
- Second, environment severity: the same material is benign in a dense
  cold plasma and hostile in a hot tenuous one. Rank the mission's
  regime -- geostationary-orbit and highly-elliptical-orbit are the
  severe cases, medium-earth-orbit and polar-low-earth-orbit are
  intermediate (auroral-electron precipitation reaches the polar
  case), interplanetary-cruise is moderate, and
  equatorial-low-earth-orbit is the mild case where the dense
  ionospheric plasma clamps the surface. Severity sets whether the
  requirement applies at full or reduced level, never whether it
  vanishes.
- The screening quantities are the surface-resistivity of the outer
  layer and the resistance of the charge-bleed-path from that layer to
  structure-ground. A surface counts as controlled-conductive when
  both sit at or below their screening ceilings; a surface above
  either ceiling is a floating-dielectric surface and carries a
  finding. The bleed-path resistance follows from the layer's
  volume-resistivity, its thickness and its grounded contact area.

## Workflow

1. Validate each item record: it needs a name, an outer-material name,
   an external flag, a shield-coverage-fraction in the zero-to-one
   range and an ambient-plasma view flag. Reject a malformed record
   before it enters the assessment rather than defaulting it.
2. Categorize exposure from those fields into plasma-exposed,
   partially-shielded or internal. An internal item is out of scope for
   clause 6.1.1 and is reported as not-applicable, not as compliant.
3. Rank the mission orbit-regime severity. Reject an unrecognized
   regime; do not silently fall back to the severe case, because that
   hides a missing environment definition behind a conservative-looking
   verdict.
4. Set the requirement level: full for a plasma-exposed item in a
   severe or intermediate regime, reduced for a plasma-exposed item in
   a mild regime and for any partially-shielded item, none for an
   internal item.
5. For every in-scope item, compute the charge-bleed-path resistance
   from volume-resistivity, layer thickness and grounded contact area,
   then screen it and the surface-resistivity against their ceilings.
   Treat an exact-ceiling value as compliant by comparing with a
   relative tolerance, never by widening the ceiling itself.
6. Record a finding for each failure mode separately: surface-resistivity
   above its ceiling, bleed-path resistance above its ceiling, a missing
   structure-ground bond, and an absent screening value. Aggregate over
   the inventory; the inventory is applicability-complete only when
   every in-scope item carries a verdict with no open findings.

## Pitfalls

- Reading "not-applicable" as "compliant". An internal item is simply
  outside clause 6.1.1; an in-scope item with no screening data on
  record is an open finding, and the two must never collapse into the
  same verdict.
- Judging the outer layer by its thermo-optical role. A
  thermal-control coating, an optical-solar-reflector and a paint are
  all in scope if they are plasma-exposed; the rule reads their
  electrical behaviour, not their function.
- Treating a grounded metallic backing as proof of control. Charge
  lands on the outer face, so the path that matters runs through the
  outer layer's thickness to that backing; a highly-resistive layer
  over a perfectly-grounded substrate is still a floating-dielectric
  surface.
- Defaulting an unknown orbit-regime to the severe case. That produces
  a verdict that looks conservative while concealing the fact that the
  charging-environment specification was never captured.

## Behavior contract (gate 3)

The exposure-categorization, orbit-regime-severity,
bleed-path-resistance and screening logic is exercised by the gate 3
contract test: scripts/test_e2006_surface_material_control_applicability.py
against scripts/e2006_surface_material_control_applicability_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_surface_material_control_applicability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
