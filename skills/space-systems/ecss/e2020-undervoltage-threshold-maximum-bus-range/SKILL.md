---
name: e2020-undervoltage-threshold-maximum-bus-range
description: "Verify that a ground adjustable undervoltage trip point is expressed against the maximum direct current bus voltage, per clause 5.4.3.2.1 of ECSS-E-ST-20-20C. Use when a unit declares its undervoltage threshold as a fraction of a bus voltage and the reference, the adjustment ladder and the resulting window all have to be shown. Refer every settable fraction back into volts through the maximum bus voltage, walk the ladder from its lowest setting to its highest, and test each point against the window between the equipment operating floor and the lowest steady state bus voltage. Report the reference the specification actually used, the usable settings, and the volts one adjustment step buys. Trigger: ecss, e-st-20-20c-clause-5-4-3-2-1, undervoltage-threshold-maximum-bus-range, ground-adjustable-undervoltage-setting, undervoltage-threshold-reference-voltage, undervoltage-setting-ladder-resolution, maximum-bus-voltage-referral, undervoltage-trip-window-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e-st-20-20c-clause-5-4-3-2-1, e2020-undervoltage-threshold-maximum-bus-range, ground-adjustable-undervoltage-setting, undervoltage-threshold-reference-voltage, undervoltage-setting-ladder-resolution, maximum-bus-voltage-referral, undervoltage-trip-window-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Undervoltage Threshold Against Maximum Bus Voltage (space-systems/ecss/e2020-undervoltage-threshold-maximum-bus-range)

Use when the task is clause 5.4.3.2.1 of ECSS-E-ST-20-20C: the undervoltage
trip point of a unit is adjustable on the ground and is carried against the
maximum direct current bus voltage. This leaf reads one threshold
specification and one bus description and decides whether the reference is
the right one, whether the ladder is genuinely adjustable, and whether the
volts each setting produces land where a trip point can usefully sit.

## Domain quick reference

- A percentage is not a voltage until the reference behind it is named. The
  same printed sixty-five percent is 22.1 V against a thirty-four volt
  maximum, 18.2 V against a twenty-six volt minimum and 18.2 V against a
  twenty-eight volt nominal only by coincidence. The clause names one
  reference, and a specification carrying another is reporting a number that
  does not mean what the reader will take it to mean.
- The maximum bus voltage is the conservative reference on purpose. Referring
  the setting to the top of the bus band means the same fraction gives the
  same trip voltage whatever the bus happens to be doing, and it makes the
  worst case the number the designer wrote down rather than one derived later.
- Ground adjustable means a ladder, not a number. The range has a lowest
  setting, a highest setting and a step, and the thing to grade is every point
  on that ladder — a range whose top two settings sit inside the steady state
  band ships a unit an operator can set into nuisance tripping.
- The admissible window has two walls and they come from different places. The
  ceiling is the lowest steady state bus voltage, because a trip point inside
  the normal band fires on a healthy bus. The floor is the equipment's own
  operating voltage, because a trip point below it lets the load misbehave
  before the protection ever acts.
- Sensing uncertainty closes the window from both ends. A comparator that
  realises the setting to within half a volt makes a trip point half a volt
  under the steady minimum no safer than one sitting on it, so the usable
  window is the nominal one shrunk by the uncertainty at each wall.
- Adjustment resolution is part of the requirement, not a detail. A ladder
  whose step moves the trip point further than the sensing uncertainty cannot
  be set to the accuracy the rest of the chain supports, and the adjustment
  then is the dominant error.

## Workflow

1. Validate the bus: a positive maximum, a steady state minimum no higher than
   it, an equipment floor no higher than that minimum, and a non-negative
   sensing uncertainty.
2. Validate the setting range: fractions inside zero to one, a positive step
   no wider than the whole span, and a maximum at or above the minimum.
3. Read the reference token and resolve the volts one unit of fraction stands
   for. Raise on a reference nobody can resolve; record a finding for a
   resolvable reference that is not the maximum bus voltage.
4. Enumerate the ladder in whole steps from the lowest setting upward and
   refer every point into volts.
5. Build the admissible window: equipment floor plus sensing uncertainty as
   the lower wall, steady state minimum less sensing uncertainty as the upper.
6. Test every settable point against the window and categorize each miss as
   below the operating floor or inside the steady state band.
7. Compute the volts one adjustment step moves the trip point and compare it
   with the sensing uncertainty.
8. Return the verdict with the reference, the usable settings, the ladder
   extremes, the step in volts and the findings behind each of them.

## Pitfalls

- Grading the volts and never grading the reference. A specification written
  against nominal can produce a perfectly admissible trip voltage today and a
  different one the moment the bus definition moves; the reference is the
  finding even when every setting lands well.
- Checking only the setting the unit shipped at. The clause is about an
  adjustable trip point, so every point an operator can reach has to be
  admissible, not just the one currently dialled in.
- Taking the nominal bus voltage as the ceiling of the window. The wall is the
  lowest steady state voltage the bus is allowed to reach; a trip point below
  nominal but above that minimum still fires on a healthy bus.
- Forgetting the equipment's own floor. A very low trip point looks safe
  against nuisance tripping and is exactly the setting that lets the load run
  itself into a state the protection was there to prevent.
- Leaving sensing uncertainty out of the window. It is the difference between
  a setting that is inside the band and one that is inside the band as
  realised by the hardware, and it eats into both walls at once.
- Reporting a ladder as adjustable when the range holds a single point. A
  minimum equal to the maximum is a fixed threshold with an adjustment story
  attached, and it fails the clause on its face.

## Behavior contract (gate 3)

The bus and setting range validation, reference resolution, ladder
enumeration, referral into volts, window construction with sensing
uncertainty, per-setting admissibility, adjustment resolution check and the
verdict are exercised by the gate 3 contract test:
scripts/test_e2020_undervoltage_threshold_maximum_bus_range.py against
scripts/e2020_undervoltage_threshold_maximum_bus_range_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_undervoltage_threshold_maximum_bus_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
