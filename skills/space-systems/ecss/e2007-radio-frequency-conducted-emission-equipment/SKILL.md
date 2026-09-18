---
name: e2007-radio-frequency-conducted-emission-equipment
description: "Use when assess the instrument set an ECSS-E-ST-20-07C clause 5.4.3.2 radio-frequency conducted-emission run depends on: confirm a measurement-receiver, a current-probe, a signal-generator, a data-recorder and an oscilloscope are each declared once, intersect their usable frequency spans, compare that intersection with the method band, name the item that bounds it, apply the probe transfer-impedance and cable loss to turn a receiver reading into a lead current, size the generator against the injection level the probe check needs, and reject an item whose calibration lapses inside the campaign. Trigger: ecss, e-st-20-07c, rf-conducted-emission-equipment, measurement-receiver-span, current-probe-transfer-impedance, injection-signal-generator, conducted-emission-data-recorder, instrument-calibration-validity."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radio-frequency-conducted-emission-equipment, rf-conducted-emission-equipment, measurement-receiver-span, current-probe-transfer-impedance, injection-signal-generator, instrument-calibration-validity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radio-Frequency Conducted Emission, Instrument Set (space-systems/ecss/e2007-radio-frequency-conducted-emission-equipment)

Use when the task is the equipment clause of ECSS-E-ST-20-07C clause
5.4.3.2 -- deciding whether the items a higher-band conducted-emission
run is to be made with (a measurement receiver, a current probe, a
signal generator, a recorder for the results and an oscilloscope) are
present, span the method band between them, and stay calibrated for as
long as the campaign runs.

## Domain quick reference

- The list is a set of roles, not a shopping list of boxes. One
  instrument cannot stand in for two roles in the same run: the
  generator drives the probe check while the receiver is reading, and
  the oscilloscope watches the time-domain behaviour the receiver
  averages away. A role declared twice is as much a defect as a role
  missing, because it means the run plan has not said which item does
  what.
- Usable span is the binding property. The band a run can actually
  cover is the intersection of the declared spans, and that
  intersection is set by one item at each edge -- almost always the
  current probe, whose useful range is narrower than the receiver's.
  Naming that item is what makes a coverage shortfall fixable.
- A receiver reading is a voltage; the quantity the limit is written
  against is a lead current. The conversion runs through the probe
  transfer impedance, in decibels above one ohm, with the loss of the
  cable between probe and receiver added back rather than ignored. A
  reading reported without that conversion is a number in the wrong
  unit, not a conservative one.
- The generator exists to raise the probe check, so its output is
  sized against the injection level that check calls for. Meeting the
  level exactly is not a fault, but it leaves nothing for cable loss
  drift and is carried as a limitation.
- Calibration validity is graded against the campaign window, not
  against today. An item whose certificate expires mid-campaign
  invalidates every reading after that date, and re-running is far
  more expensive than swapping the item first.
- The instrument set is graded on its own. Where the items sit on the
  bench belongs to the setup clause of the same method.

## Workflow

1. Validate each declared item: a recognized role, a positive lower
   span edge, an upper edge strictly above it, a non-negative
   calibration validity and a non-empty identifier.
2. Reject a duplicate role, then reject the set outright when any
   required role is absent -- the run cannot be made at all.
3. Validate the method band, then test each item's span against both
   band edges, absorbing representation error at an edge with a named
   tolerance.
4. Intersect the declared spans; refuse an empty intersection, and
   otherwise name the item setting each edge of it.
5. Grade calibration: validity shorter than the campaign window is a
   finding, validity that just reaches the end of it is accepted.
6. When an injection level is declared, compute the generator margin
   over it; a shortfall is a finding, exact equality a limitation.
7. Report readiness with its findings and limitations. The set is
   ready only when no finding stands.

## Pitfalls

- Reading the receiver span and calling the band covered. The probe
  is nearly always the narrower item, and the run is bounded by the
  intersection, not by the widest box on the bench.
- Reporting a receiver reading as if it were a lead current. Without
  the probe transfer impedance and the cable loss the number is in
  the wrong unit and cannot be compared with a current limit.
- Subtracting the cable loss instead of adding it back. The loss sits
  between the probe and the receiver, so it makes the reading lower
  than the lead current, and correcting it the wrong way doubles the
  error.
- Treating the oscilloscope as optional because the receiver already
  records levels. The two instruments answer different questions, and
  a transient that the receiver's detector smooths is exactly what
  the oscilloscope is there for.
- Checking calibration on the day of the readiness review only. A
  certificate valid this morning and expired next week still
  invalidates the second half of the campaign.

## Behavior contract (gate 3)

The instrument validation, role-completeness check, span
intersection, bounding-item selection, probe-factor conversion,
injection-margin computation and calibration grading are exercised by
the gate 3 contract test:
scripts/test_e2007_radio_frequency_conducted_emission_equipment.py
against
scripts/e2007_radio_frequency_conducted_emission_equipment_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radio_frequency_conducted_emission_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
