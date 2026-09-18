---
name: e2007-indirect-discharge-test-setup
description: "Derive the bench an indirect discharge exposure runs on from the standard equipment configuration, under ECSS-E-ST-20-07C clause 5.4.12.3. Use when a coupling plane arrangement is built or reviewed: apply each declared delta to the baseline geometry, refuse an unknown delta or one that collapses a band, grade coupling plane distance, overhang, bleeder resistance, cable separation, insulating support and bond resistance against their bands, size the plane span from the unit footprint, derive the bleeder chain time constant, the bleed time the interval has to allow and the charge still on the plane at the next event, and return the governing parameter with the setup verdict. Trigger: ecss, e-st-20-07c, indirect-discharge-test-setup, esd-coupling-plane-geometry, indirect-discharge-bleeder-chain, coupling-plane-to-unit-distance, indirect-discharge-residual-plane-charge, esd-ground-reference-plane-bonding."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-indirect-discharge-test-setup, esd-coupling-plane-geometry, indirect-discharge-bleeder-chain, coupling-plane-to-unit-distance, indirect-discharge-residual-plane-charge, esd-ground-reference-plane-bonding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Indirect Discharge Test Setup (space-systems/ecss/e2007-indirect-discharge-test-setup)

Use when the task is the setup clause of ECSS-E-ST-20-07C clause
5.4.12.3 -- arranging the bench that exposes a unit to a discharge
delivered into a coupling plane beside it rather than into the unit
itself. The clause does not build a bench from nothing: it starts from
the standard equipment configuration already used for the other runs
and modifies it only where coupling through a plane demands something
different.

## Domain quick reference

- The bench is a derived arrangement, not an independent one. Every
  departure from the standard configuration is a declared delta with a
  reason; an undeclared departure is a setup finding even when the
  number it produces looks reasonable. A delta may move a band, never
  close it, so a delta leaving a parameter with no admissible value is
  an input error rather than a very tight bench.
- The exposure the unit sees is a geometry, not a setting. The distance
  from the plane to the unit face sets the coupled field for a given
  charge voltage, and moving the plane a few centimetres changes the
  severity far more than the operator expects.
- The plane has to be larger than the unit. It covers the footprint
  plus overhang on both sides, or the edges of the unit sit outside the
  coupled region and the parts that are hardest to expose are exactly
  the parts that were missed.
- The bleeder chain, not the operator, sets the repetition. The plane is
  a capacitor against the ground reference, and it comes down through
  the bleeder resistors on an exponential. The interval between events
  has to span several of those time constants, or the next event starts
  on a plane that never returned to the reference.
- Residual charge remains even when the bleed rule is satisfied. A few
  time constants leave a small but non-zero fraction of the charge
  voltage on the plane, and that belongs in the record rather than being
  rounded to nothing.
- The insulating support and the bond to the ground reference plane are
  part of the circuit. The support holds the unit off the reference so
  the return path is the bond that was declared, and a bond resistance
  outside its band moves the return path somewhere nobody measured.
- A vertical plane couples into one face. The faces it does not see are
  exposed by moving the plane and running again, so a single position is
  a partial exposure and the report has to say which faces it covered.

## Workflow

1. Validate the realized bench: a recognized plane type, positive
   geometry, capacitance, charge voltage and interval, a non-negative
   bond resistance, a whole number of bleeder resistors, and a deviation
   list naming only graded parameters.
2. Resolve the bands: start from the baseline configuration and apply
   each declared delta, refusing an unknown parameter, an unknown delta
   key and any delta that collapses a band.
3. Grade each geometry parameter against its resolved band as
   conforming, a declared deviation, or nonconforming.
4. Size the plane span from the unit footprint and the overhang, and
   compare it with the plane that is actually there.
5. Derive the bleeder chain time constant from the series resistance and
   the plane capacitance, the bleed time the interval has to allow, and
   the fraction and voltage still on the plane at the next event.
6. Rank the graded parameters by their fractional distance from the
   nearer band edge and name the governing one.
7. Aggregate: an undeclared excursion, an undersized plane and too short
   an interval are findings; a declared excursion, residual plane charge
   and a single vertical plane position are limitations carried with the
   run.

## Pitfalls

- Treating the indirect bench as a fresh arrangement. It inherits the
  standard configuration, and a parameter nobody thought to declare is
  still being changed silently.
- Sizing the plane on the unit footprint alone. The overhang is what
  keeps the unit edges inside the coupled region, and it is needed on
  both sides.
- Setting the repetition rate from the generator's own recovery. The
  plane bleeds far more slowly than the generator recharges, and the
  slower of the two is what sets the interval.
- Reading the bleed rule as leaving nothing behind. It leaves a small
  fraction, and on a high charge voltage that is still tens of volts on
  the plane when the next event fires.
- Letting the unit rest directly on the ground reference plane. The
  insulating support is what forces the return through the declared
  bond, and without it the return path is whatever the contact happens
  to be.
- Accepting a declared deviation as if it were conformance. It keeps the
  run usable, but it travels with the results as a limitation and has to
  reach whoever reads them.
- Reporting a single vertical plane position as the full exposure.

## Behavior contract (gate 3)

The bench validation, delta resolution, band grading, plane-span sizing,
bleeder time constant, bleed-time and residual-charge derivation,
governing-parameter ranking and the aggregate verdict are exercised by
the gate 3 contract test:
scripts/test_e2007_indirect_discharge_test_setup.py against
scripts/e2007_indirect_discharge_test_setup_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_indirect_discharge_test_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
