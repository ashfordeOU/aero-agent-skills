---
name: e2008-harness-resistance-measurement
description: "Use when a harness resistance measurement has to be set up, sentenced or repeated. Derive the resistance of one solar array harness run at the interface connector from a series loop read across redundant conductors joined at the far end, under ECSS-E-ST-20-08C clause 5.5.3.3.9: refuse a pair whose legs differ in material, gauge, routed length or section, since only matched legs may be halved; subtract the declared far-end joint, halve the remainder and refer it to the reference temperature; compare it against what the declared geometry predicts; and convert it through the flight configuration into the voltage lost at maximum array current. Trigger: ecss, e-st-20-electrical-scope, harness-resistance-measurement, redundant-wiring-series-loop, interface-connector-voltage-drop, four-wire-harness-measurement, solar-array-harness-screening."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-harness-resistance-measurement, harness-resistance-measurement, redundant-wiring-series-loop, interface-connector-voltage-drop, four-wire-harness-measurement, solar-array-harness-screening, harness-conductor-temperature-referral]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Harness Resistance Measurement (space-systems/ecss/e2008-harness-resistance-measurement)

Use when the task is the harness resistance measurement of
ECSS-E-ST-20-08C clause 5.5.3.3.9 -- getting the resistance of a harness
run at the interface connector when only one end of that run is
available to an instrument, by tying two redundant conductors together
at the far end and reading the loop they form.

## Domain quick reference

- The wanted number is one run, array to interface connector. Both of
  its ends are rarely reachable at once, since the far end is already
  terminated into the array. Joining two redundant conductors of the
  same circuit at the far end turns the pair into an out-and-back loop
  whose two ends both land at the connector, which is where the
  measurement is taken.
- The loop reading is not the answer. It carries both conductors in
  series, plus the far-end tie, at whatever temperature the harness
  happens to be. Three things come off it before it means anything.
- The far-end tie belongs to the test article, not to the harness, so
  its declared resistance is subtracted. A tie that accounts for the
  whole reading means the loop never closed through the conductors.
- Halving what is left shares the resistance equally between the two
  legs, which is a statement about the harness only when the legs are
  the same wire. Material, gauge, routed length and section are compared
  leg to leg, and an undeclared attribute is rejected rather than
  assumed equal. A mismatched pair yields a number that belongs to
  neither leg, so it is reported as not evaluated.
- Copper resistance rises with temperature, so the leg is referred to
  the declared reference temperature before it meets a band. A run read
  in a warm cleanroom reads high and is not thereby defective.
- The band is set by what the declared conductor geometry predicts.
  Above it means a resisting joint, a cold crimp or an undersized
  conductor. Below it means the loop did not take the routed path -- a
  tie at the wrong point, or a leg bypassed -- which is a finding, not a
  bonus.
- The series loop is a test configuration, not a flight one. What the
  array current actually sees depends on whether the redundant legs are
  paralleled in flight or only one is active, and the interface voltage
  drop follows from that, not from the loop.
- A two-wire reading cannot separate the harness from the instrument
  leads. At these resistances the leads are a large part of the reading,
  so where four-wire measurement is required a two-wire record is
  reported as not evaluated.

## Workflow

1. Capture both legs of the redundant pair with material, gauge, routed
   length and section declared, and the loop reading with its
   measurement temperature, its far-end joint resistance and its
   measurement method.
2. Compare the legs. A mismatch stops the reduction for that run and
   names the attribute, because the halving step is what the mismatch
   invalidates.
3. Check the method. A two-wire reading against a four-wire requirement
   is re-taken, not corrected.
4. Subtract the declared far-end joint from the loop reading and halve
   the remainder to reach one leg at the measurement temperature.
5. Refer that leg to the reference temperature with the conductor
   coefficient, then compare it against the resistance the declared
   geometry predicts and group it: within band, above band, below band.
6. Put the leg into its flight configuration, convert it to the voltage
   lost at maximum array current, and sentence the campaign. Report each
   shortfall separately so the retest is scoped to the one that failed.

## Pitfalls

- Halving a loop whose legs are not the same wire. The result sits
  between the two and describes neither, and nothing downstream can tell
  that it is a blend.
- Leaving the far-end tie in the number. On a run of a few tens of
  milliohms a bolted or crimped tie is not a rounding error, and it
  inflates every leg reported from that loop.
- Comparing a reading taken at ambient against a band derived at the
  reference temperature. A twenty-kelvin offset is several percent of
  the resistance, which is a large share of the tolerance.
- Reporting the loop resistance, or the leg resistance, as what the
  array current sees. Paralleled redundant legs halve the run again, so
  quoting the leg overstates the interface drop while quoting the loop
  overstates it twice over.
- Comparing a referred leg against a band edge by bare arithmetic. The
  leg is a quotient of products and the edge is a product of a declared
  fraction, so a run meant to sit on the edge can land a few units in
  the last place outside it; the comparison absorbs that representation
  error while the band stays untouched.

## Behavior contract (gate 3)

The redundant-pair check, the geometry prediction, the joint removal and
halving, the temperature referral, the band grouping, the flight
configuration, the interface voltage drop and the campaign verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_harness_resistance_measurement.py against
scripts/e2008_harness_resistance_measurement_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_harness_resistance_measurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
