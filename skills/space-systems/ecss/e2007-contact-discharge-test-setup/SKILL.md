---
name: e2007-contact-discharge-test-setup
description: "Derive the bench a direct contact discharge run stands on from the standard unit configuration, under ECSS-E-ST-20-07C clause 5.4.14.3. Use when a contact discharge arrangement is built or reviewed: confirm the generator carries the contact tip and not the air tip, apply each declared delta to the baseline bands, refuse a delta that closes one, grade discharge resistance, storage capacitance, return cable length and separation, support thickness, bond resistance and tip approach angle, derive the nominal peak current, the network decay constant, the stored energy and the delivered charge, group every declared point as contact capable or air only, and return the governing parameter with the setup verdict. Trigger: ecss, e-st-20-07c, contact-discharge-test-setup, esd-generator-contact-tip, contact-discharge-network-peak-current, esd-return-cable-dressing, contact-discharge-point-surface-finish, esd-unit-insulating-support."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-contact-discharge-test-setup, esd-generator-contact-tip, contact-discharge-network-peak-current, esd-return-cable-dressing, contact-discharge-point-surface-finish, esd-unit-insulating-support]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Contact Discharge Test Setup (space-systems/ecss/e2007-contact-discharge-test-setup)

Use when the task is the setup clause of ECSS-E-ST-20-07C clause
5.4.14.3 -- arranging the bench that exposes a unit to a discharge put
onto the unit itself through a tip held against it, rather than into a
plane beside it. The clause does not build a bench from nothing: it
starts from the standard equipment configuration already used for the
other runs and modifies it only where direct application demands
something different.

## Domain quick reference

- The generator has two personalities and only one of them is this
  clause. A contact run wants the pointed tip that makes a galvanic
  connection before the switch fires; the rounded tip belongs to the air
  run. A bench declared for contact application while the rounded tip is
  fitted is delivering a different event at every point, and nothing in
  the recorded level says so.
- A discharge point is a surface, not a coordinate. The tip can only
  make contact where the finish is conductive and the surface resistance
  is low; an anodized or painted face grades as an air point however
  firmly the tip is pressed against it, because the arc still forms
  across a film. Listing such a face for contact application is a setup
  finding, not a small procedural difference.
- The severity is set by the network, not by the tip. The charge voltage
  divided by the discharge resistor fixes the first-peak current, the
  resistor and the storage capacitor fix the decay, and the capacitor
  and the voltage fix the energy and the charge the event moves. Two
  generators set to the same kilovolts deliver different events when
  their networks differ.
- The return path is part of the circuit. The return cable has to span
  the geometric path from the generator to the ground reference without
  being stretched, and the cable left over has to be dressed away from
  the unit rather than coiled next to it, where it couples the return
  current straight back into the harness under test.
- The insulating support and the declared bond are what make the return
  path knowable. Rest the unit directly on the ground reference and the
  return goes through whatever the contact happens to be, which is not
  the path anybody measured.
- The tip is held perpendicular. An oblique approach changes the contact
  geometry and the inductance of the last few centimetres, which is
  exactly the part of the loop the sub-nanosecond edge sees.
- Every departure from the standard configuration is a declared delta
  with a reason. A delta may move a band; it may never close one, so a
  delta leaving a parameter with no admissible value is an input error
  rather than a very tight bench.

## Workflow

1. Validate the realized bench: a recognized generator mode and tip
   type, positive network, geometry and charge values, an approach angle
   inside half a turn, a non-negative bond resistance, at least one
   declared discharge point with a recognized finish, and a deviation
   list naming only graded parameters.
2. Resolve the bands: start from the baseline configuration and apply
   each declared delta, refusing an unknown parameter, an unknown delta
   key and any delta that collapses a band.
3. Grade discharge resistance, storage capacitance, return cable length,
   cable-to-unit separation, support thickness, bond resistance and tip
   approach angle against their resolved bands as conforming, a declared
   deviation, or nonconforming.
4. Group every declared point as contact capable, air only, or not a
   discharge point, from its finish, its surface resistance and whether
   it is reachable at all with the unit as configured.
5. Derive the nominal peak current, the network decay constant, the
   stored energy and the delivered charge from the network and the
   charge voltage.
6. Compare the return cable length with the return path it has to span
   and report the slack.
7. Rank the graded parameters by their fractional distance from the
   nearer band edge and name the governing one.
8. Aggregate: the wrong tip for the mode, a point listed for contact
   that grades otherwise, no contact-capable point at all, a cable
   shorter than its path and an undeclared excursion are findings; a
   declared excursion, air-only points, unreachable points and a large
   cable slack are limitations carried with the run.

## Pitfalls

- Reading the tip as an accessory. It is what decides whether the event
  is the one the clause names, and swapping it changes the result
  without changing a single recorded number.
- Choosing discharge points off a drawing. The finish decides, and the
  finish is on the hardware rather than in the model.
- Setting the level in kilovolts and calling the severity fixed. The
  resistor and the capacitor are what turn those kilovolts into a
  current and an energy.
- Ordering a longer return cable to reach comfortably. The slack has to
  go somewhere, and coiled beside the unit is the worst place for it.
- Letting the unit sit straight on the ground reference plane. The
  insulating support is what forces the return through the declared
  bond.
- Pressing the tip on at whatever angle reaches. The perpendicular
  approach is part of the arrangement, not a convenience.
- Accepting a declared deviation as if it were conformance. It keeps the
  run usable, but it travels with the results as a limitation and has to
  reach whoever reads them.

## Behavior contract (gate 3)

The bench validation, delta resolution, band grading, discharge-point
grouping, network peak-current, decay, energy and charge derivation,
return-cable slack, governing-parameter ranking and the aggregate
verdict are exercised by the gate 3 contract test:
scripts/test_e2007_contact_discharge_test_setup.py against
scripts/e2007_contact_discharge_test_setup_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_contact_discharge_test_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
