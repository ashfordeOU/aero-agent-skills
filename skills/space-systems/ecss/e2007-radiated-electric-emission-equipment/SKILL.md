---
name: e2007-radiated-electric-emission-equipment
description: "Evaluate the instrument set an ECSS-E-ST-20-07C clause 5.4.6.2 radiated electric-emission run depends on: confirm a measurement receiver, a data recorder and the polarized receive antennas are each declared, tile the antenna spans across the method band in vertical and horizontal polarization separately, name every uncovered segment and the antenna holding each edge, turn a receiver reading into a field strength through the antenna factor and cable loss, and reject an item whose calibration lapses inside the campaign. Use when a radiated-emission bench is assembled or its readiness reviewed. Trigger: ecss, e-st-20-07c, radiated-electric-emission-equipment, radiated-emission-measurement-receiver, polarized-receive-antenna-set, antenna-factor-field-conversion, antenna-band-tiling-gap, radiated-instrument-calibration-window."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-electric-emission-equipment, radiated-electric-emission-equipment, radiated-emission-measurement-receiver, polarized-receive-antenna-set, antenna-factor-field-conversion, antenna-band-tiling-gap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Electric Emission, Instrument Set (space-systems/ecss/e2007-radiated-electric-emission-equipment)

Use when the task is the equipment clause of ECSS-E-ST-20-07C clause
5.4.6.2 -- deciding whether the items a radiated electric-field
emission run is to be made with (a measurement receiver, a recorder
for what it reads, and the polarized antennas that couple the field
into it) are present, reach across the method band between them in
both polarizations, and stay calibrated for as long as the campaign
runs.

## Domain quick reference

- The receiver and the recorder are single roles. Declaring either of
  them twice is as much a defect as leaving it out, because it means
  the run plan has not said which item does the job.
- The antennas are the exception, and the whole shape of this clause
  turns on it. No single antenna spans several decades, so the
  antennas are a SET that has to TILE the band. A conducted method
  intersects the spans of its instruments; here the spans are unioned,
  and what matters is whether the union leaves a hole.
- A hole is named by its edges, not by a pass/fail flag. "No antenna
  between 300 MHz and 500 MHz" tells the bench which item to borrow;
  "coverage incomplete" does not.
- Tiling is graded once per polarization. An antenna is mounted in a
  plane, and a set that reaches the top of the band only with an item
  never used horizontally has covered one plane and left the other
  open. Grading the antennas as one pool hides exactly that.
- A receiver reading is a voltage at the receiver input; the quantity
  the limit is written against is a field strength in decibels above
  one microvolt per metre. The conversion runs through the antenna
  factor, with the loss of the cable between antenna and receiver
  added back rather than ignored -- the loss made the reading lower
  than the field was, so subtracting it doubles the error.
- Calibration validity is graded against the campaign window, not
  against today. A certificate that expires mid-campaign invalidates
  every reading after that date, and re-running costs far more than
  swapping the item first.
- The instrument set is graded on its own. Where the items sit and how
  the unit faces them belong to the setup clause of the same method.

## Workflow

1. Validate each declared item: a non-empty identifier, a recognized
   role, a positive lower span edge, an upper edge strictly above it,
   and a non-negative calibration validity.
2. Validate an antenna further: it declares the polarizations it is
   used in, without repeating one, and it carries an antenna factor.
3. Reject a repeated identifier and a repeated single role, then
   refuse the set outright when the receiver, the recorder or the
   antennas are absent -- the run cannot be made at all.
4. Validate the method band, then test the receiver against it and
   record any part of the band it cannot reach.
5. For each polarization, take the antennas used in that plane, walk
   their sorted spans across the band, and record every uncovered
   segment; name the antenna holding each edge of what is covered.
6. Grade calibration against the campaign window: validity shorter
   than the window is a finding, validity that just reaches its last
   day is accepted and carried as a limitation.
7. Report readiness with its findings and limitations. The set is
   ready only when no finding stands.

## Pitfalls

- Intersecting the antenna spans the way a conducted method
  intersects instrument spans. The antennas are meant to hand over to
  each other; intersecting them collapses the set to nothing.
- Grading the antennas as one pool. Coverage is a per-plane property,
  and an item used only vertically cannot close a horizontal hole.
- Reporting a receiver reading as if it were a field strength. Without
  the antenna factor the number is in the wrong unit and cannot be
  compared with a radiated limit.
- Subtracting the cable loss instead of adding it back. The loss sits
  between the antenna and the receiver, so it makes the reading lower
  than the field, and correcting it the wrong way doubles the error.
- Treating the recorder as bookkeeping. Without a recorded trace there
  is nothing to re-examine when an exceedance is questioned, and the
  run has to be repeated.
- Checking calibration on the day of the readiness review only. A
  certificate valid this morning and expired next week still
  invalidates the second half of the campaign.

## Behavior contract (gate 3)

The instrument validation, role-completeness check, per-polarization
band tiling, edge-antenna naming, antenna-factor conversion and
calibration grading are exercised by the gate 3 contract test:
scripts/test_e2007_radiated_electric_emission_equipment.py
against
scripts/e2007_radiated_electric_emission_equipment_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radiated_electric_emission_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
