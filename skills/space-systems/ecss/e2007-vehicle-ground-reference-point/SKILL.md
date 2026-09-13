---
name: e2007-vehicle-ground-reference-point
description: "Use when validate the structural vehicle-ground-reference-point that ECSS-E-ST-20-07C clause 4.2.11.2 makes the baseline for every bonding-resistance measurement: confirm exactly one reference is designated, that it sits on primary-structure behind a conductive surface-finish and stays reachable with the harness installed, then check each bonding-measurement that cites it - the four-terminal-kelvin method where the allowance is in the low-milliohm range, a lead-offset substantiated by the conductor geometry, and a lead-corrected reading inside the allowance for its bond-category. Trigger: vehicle-ground-reference-point, bonding-resistance-measurement, structural-reference-baseline, four-terminal-kelvin, bond-category-allowance, conductive-surface-finish, lead-offset-correction, primary-structure-attachment."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-vehicle-ground-reference-point, vehicle-ground-reference-point, bonding-resistance-measurement, structural-reference-baseline, four-terminal-kelvin, bond-category-allowance, conductive-surface-finish]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility -- Vehicle Ground Reference Point (space-systems/ecss/e2007-vehicle-ground-reference-point)

Use when the task is the bonding baseline of ECSS-E-ST-20-07C clause
4.2.11.2 -- designating one structural point as the vehicle ground
reference, qualifying it as a measurement baseline, and checking that
every bonding-resistance measurement on the vehicle is referred to it
by a method that can actually resolve the allowance being claimed.

## Domain quick reference

- The clause exists because a bonding-resistance number is meaningless
  without a stated second terminal. Two measurements taken to two
  different structural points are not comparable, and a bond that
  passes against a nearby bracket can fail against the real reference.
  Exactly one point is designated for the whole vehicle.
- The reference point qualifies only when three properties hold at
  once: it is on primary-structure (a secondary bracket or an equipment
  panel moves with its own joint resistance), its surface-finish is
  conductive (bare-machined, chemical-conversion-coated or
  electroplated -- a hard-anodized or painted finish inserts the
  finish's own resistance into every reading), and it stays reachable
  in the configuration in which bonding is measured.
- Bond categories carry different allowances, in milliohm:
  lightning-return-bond 1.0, structure-bond-primary 2.5,
  structure-bond-secondary 10.0, shield-termination-bond 25.0. The
  category is a property of the bond's function, not of the instrument.
- Method resolution is a real constraint. A two-terminal-ohmmeter
  reading carries its own lead resistance, which is tens of milliohm
  and swamps anything below roughly 100 milliohm; a low-milliohm
  allowance therefore demands the four-terminal-kelvin method, where
  the current and sense pairs are separate.
- A declared lead-offset is substantiated from conductor geometry:
  for copper at room temperature the resistance of a lead is about
  17.24 milliohm per metre per square-millimetre of section. A declared
  offset far from that figure means the offset was guessed, and it is
  subtracted from every reading in the campaign.

## Workflow

1. Resolve the designated reference: exactly one record is flagged.
   Zero means no baseline exists and no measurement in the campaign can
   be interpreted; more than one means two baselines are in use. Both
   are input defects.
2. Qualify the reference point: primary-structure attachment,
   conductive surface-finish, reachable in the measurement
   configuration. Each failed property is its own finding, because the
   repairs differ -- move the point, strip and treat the finish, or
   re-plan the access.
3. Compute the substantiated lead-offset from the lead length and
   section, and compare it with the declared offset. Flag a declared
   offset that departs from the computed figure by more than the
   substantiation band, because that offset is subtracted from every
   reading.
4. Correct each raw reading by its lead-offset. A correction that
   drives the reading negative means the offset is larger than the
   measurement, which is an input defect, not a very good bond.
5. Check the method against the allowance: a bond-category allowance in
   the low-milliohm range measured with a two-terminal-ohmmeter is a
   finding regardless of the number that came out.
6. Check the terminal: a measurement that cites any point other than
   the designated reference is a finding; do not silently re-base it.
7. Compare the corrected reading with the category allowance and
   aggregate. Report the worst corrected reading and the mean across
   the campaign, and mark the baseline compliant only when the
   reference findings and every measurement finding are empty.

## Pitfalls

- Accepting a reading because the number is small. The number is only
  interpretable once the second terminal is the designated reference
  and the method can resolve the allowance being claimed.
- Treating a painted or hard-anodized reference face as adequate
  because the reading still passed. The finish resistance is in series
  with every measurement in the campaign; a passing reading through it
  means the bond is better than it looks and a failing one may be the
  face, not the bond.
- Subtracting an unsubstantiated lead-offset. The offset is applied to
  every reading, so a guessed value is a campaign-wide bias, not a
  per-measurement rounding.
- Reading a negative corrected value as an excellent bond. It means the
  offset exceeds the raw reading, which is arithmetically impossible
  for a real conductor.
- Widening a category allowance because a lead-corrected reading lands
  a hair above it. The correction is a subtraction of two decimal
  values and can overshoot in the last place -- absorb that in the
  comparison tolerance, never by relaxing the allowance.

## Behavior contract (gate 3)

The reference-resolution, reference-qualification, lead-offset,
method-resolution, terminal-citation and allowance-comparison logic is
exercised by the gate 3 contract test:
`scripts/test_e2007_vehicle_ground_reference_point.py` against
`scripts/e2007_vehicle_ground_reference_point_logic.py` (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_vehicle_ground_reference_point.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
