---
name: e2007-low-frequency-conducted-emission-equipment
description: "Assess the instrument set a low-frequency conducted-emission run is built from under ECSS-E-ST-20-07C clause 5.4.2.2: confirm a measurement receiver, a current probe and a calibration signal source are all present and in date, intersect their frequency coverage with the required measurement band, report every uncovered sub-band, name the instrument that limits the chain, check the probe transfer-impedance and current rating against the harness it must clamp, and derive the source drive level the system check will need. Use when assembling or auditing a low-frequency conducted-emission bench before the setup is built. Trigger: ecss, e-st-20-07c, lf-conducted-emission-equipment, emi-measurement-receiver, current-probe-transfer-impedance, conducted-emission-calibration-source, conducted-emission-band-coverage, instrument-calibration-currency."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-low-frequency-conducted-emission-equipment, lf-conducted-emission-equipment, emi-measurement-receiver, current-probe-transfer-impedance, conducted-emission-calibration-source, conducted-emission-band-coverage, instrument-calibration-currency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Low-Frequency Conducted-Emission Equipment (space-systems/ecss/e2007-low-frequency-conducted-emission-equipment)

Use when the task is the instrumentation list of ECSS-E-ST-20-07C clause
5.4.2.2 -- deciding whether the measurement receiver, the current probe
and the calibration signal source on hand can actually carry a
low-frequency conducted-emission run across the whole required band, and
naming what is missing when they cannot.

## Domain quick reference

- The clause names three roles, not three boxes. One instrument may fill
  only one role in a given run; a set carrying two receivers and no probe
  is not a set, and a set whose source is missing cannot be system
  checked at all. Readiness is decided per role, and an absent role is a
  finding rather than a detail to be worked around on the day.
- Coverage is an intersection, never a union. The measurable band is the
  overlap of the receiver, the probe and the source coverages with the
  required band. A receiver reaching far above the band buys nothing once
  the probe stops early; the chain is exactly as wide as its narrowest
  member.
- Report the gap as a frequency interval, not as a percentage. A set that
  covers ninety-five percent of a decade-wide band can still be blind
  across the sub-band the unit's switching fundamental sits in, and only
  the interval says so.
- The current probe is characterised by its transfer impedance, the ratio
  between the voltage it presents to the receiver and the current flowing
  in the harness. Too low a transfer impedance sinks the wanted signal
  into the receiver noise floor at the low end of the band, where the
  emission limits are tightest.
- The probe also has a current rating. Clamping a probe on a harness
  carrying more current than the core can take saturates the core, and
  the recorded level is then a property of the saturated probe.
- The signal source exists to inject a known current during the system
  check. The level it must reach follows from the wanted check current
  and the probe transfer impedance through the port impedance; a source
  that cannot reach it makes the system check unperformable.
- Calibration currency is part of the equipment list. A lapsed
  calibration is a finding; one about to lapse before the campaign ends
  is a limitation to be carried, not silently ignored.

## Workflow

1. Normalize every instrument record to one of the three recognized
   roles and reject an unrecognized role or a role appearing twice.
2. Validate each record: positive, ordered frequency edges, a calibration
   figure, plus transfer impedance and current rating on the probe and an
   output ceiling on the source.
3. List the absent roles. Without all three, stop at incomplete rather
   than grading a coverage that cannot be measured.
4. Intersect the three coverages with the required measurement band,
   express the result in decades, and reduce the leftovers to explicit
   uncovered sub-bands.
5. Attribute the loss: the instrument removing the most decades from the
   required band is the limiting one, with ties resolved in the clause's
   own role order so the answer is stable.
6. Compare the probe transfer impedance against the sensitivity floor and
   its rating against the harness current, then derive the source drive
   level the system check needs and compare it with the source ceiling.
7. Aggregate the findings and the limitations. The set is ready only when
   no finding stands.

## Pitfalls

- Adding the coverages together instead of intersecting them, so a wide
  receiver hides a probe that stops two decades short.
- Treating a missing role as recoverable and grading the coverage of the
  two instruments that did turn up.
- Quoting coverage as a percentage of the band. The uncovered interval is
  what a reviewer needs; the percentage hides where the blindness sits.
- Picking a probe on its current rating alone and discovering at the low
  end that its transfer impedance leaves no signal above the noise floor.
- Assuming any laboratory source can drive the system check. The level
  needed scales with the wanted check current and the transfer impedance,
  and a low-output generator falls short of it.
- Carrying an instrument whose calibration lapses mid-campaign without
  recording it, then having the whole data set questioned afterwards.

## Behavior contract (gate 3)

The role normalization, instrument validation, band-intersection
coverage, limiting-instrument attribution, drive-level derivation and
readiness aggregation logic is exercised by the gate 3 contract test:
scripts/test_e2007_low_frequency_conducted_emission_equipment.py against
scripts/e2007_low_frequency_conducted_emission_equipment_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_low_frequency_conducted_emission_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
