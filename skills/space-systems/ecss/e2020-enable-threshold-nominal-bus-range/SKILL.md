---
name: e2020-enable-threshold-nominal-bus-range
description: "Evaluate an adjustable turn on threshold that is set as a percentage of the nominal main bus voltage, per clause 5.4.4.1.1 of ECSS-E-ST-20-20C. Use when a unit declares an enable setting ladder and the range it spans has to be shown against the percentages the project asks for. Refer every setting back into volts through the nominal main bus, walk the ladder from its lowest step to its highest, and test the coverage of the required band, the volts one step buys, and whether each setting lands inside the bus window the enable point can actually be crossed in. Report the reference the specification used. Trigger: ecss, e-st-20-20c-clause-5-4-4-1-1, enable-threshold-nominal-bus-percentage, turn-on-threshold-adjustment-ladder, nominal-main-bus-voltage-referral, enable-threshold-range-coverage, enable-setting-step-resolution."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e-st-20-20c-clause-5-4-4-1-1, e2020-enable-threshold-nominal-bus-range, enable-threshold-nominal-bus-percentage, turn-on-threshold-adjustment-ladder, nominal-main-bus-voltage-referral, enable-threshold-range-coverage, enable-setting-step-resolution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Enable Threshold Range on the Nominal Bus (space-systems/ecss/e2020-enable-threshold-nominal-bus-range)

Use when the task is clause 5.4.4.1.1 of ECSS-E-ST-20-20C: the turn on
threshold of a protection function is adjustable, and the adjustment is
expressed as a percentage of the nominal main bus voltage. This leaf takes the
declared setting ladder and shows the range it really covers, the volts each
step commands, and which of its settings the bus can actually reach.

## Domain quick reference

- A percentage is only a number until its reference is named. The same 70
  percent setting is 19.6 V against a 28 V nominal bus and 70 V against a
  100 V one, so the reference travels with the figure and a specification that
  quotes the percentage alone has not stated the threshold.
- This clause names the nominal main bus as the reference. A unit that refers
  its ladder to the maximum bus value instead is answering a different clause,
  and the two references do not give the same volts, so the mismatch is a
  finding rather than a presentation detail.
- The range has two ends and both of them are requirements. A ladder that
  reaches high enough but cannot be set low enough fails exactly as hard as
  one that cannot be set high enough; coverage is reported per end so the
  design knows which way to move.
- Resolution is the other half of the range. Volts per step is the step
  percentage referred to the nominal bus, and a ladder can span the required
  band while its step is too coarse to place the threshold where the analysis
  wants it.
- A setting that exists on the ladder is not automatically a setting the unit
  can use. The enable point has to sit above the floor the equipment operates
  from and below the lowest steady state bus voltage, otherwise the bus never
  climbs through it and the load never comes on.
- Adjustment is a ground activity. The usable window is decided once, against
  the bus behaviour the mission actually shows, and the count of usable
  settings is the practical resolution the operator is left with.

## Workflow

1. Validate the nominal main bus, the ladder description and the required
   percentage band; a step of zero or a negative setting count is an input
   error, not an empty ladder.
2. Normalise the stated reference and record whether it is the nominal main
   bus this clause asks for, the maximum bus value, or unstated.
3. Build the ladder by offsetting each step from the lowest setting rather
   than by accumulating additions, so the highest setting is exact.
4. Refer every setting into volts through the nominal main bus and derive the
   volts one adjustment step buys.
5. Test coverage at both ends of the required band, absorbing an exact landing
   on either bound with a named tolerance.
6. Keep the settings whose volts lie inside the window between the equipment
   operating floor and the lowest steady state bus voltage, and report how
   many survive.
7. Return the span, the resolution, the usable settings and a verdict, with a
   finding for every end that is short, a step that is too coarse and a
   reference that is not the nominal main bus.

## Pitfalls

- Reading a percentage without its reference. The number is meaningless on its
  own, and assuming the nominal bus when the specification meant the maximum
  bus shifts every setting by the ratio between them.
- Checking the top of the range only. The low end is where the enable point
  has to sit for a deeply discharged bus to recover, and it is the end most
  often left uncovered.
- Accumulating the ladder by repeated addition. The accumulated error lands
  the top step just off its declared value, and a coverage test at the bound
  then fails on arithmetic rather than on design.
- Counting every ladder setting as usable. Settings below the equipment
  operating floor, and settings above the lowest steady state bus voltage,
  are positions the operator cannot use.
- Reporting resolution as a percentage alone. The analysis that placed the
  threshold works in volts, and the step in volts is what decides whether the
  wanted point can be set at all.
- Widening the required band to fit the ladder that exists. The band comes
  from the bus and load behaviour; a ladder that cannot cover it is the item
  that has to change.

## Behavior contract (gate 3)

The reference normalisation, ladder construction, percentage to volts
referral, span and step resolution, required band coverage at both ends,
usable window filtering and verdict are exercised by the gate 3 contract test:
scripts/test_e2020_enable_threshold_nominal_bus_range.py against
scripts/e2020_enable_threshold_nominal_bus_range_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_enable_threshold_nominal_bus_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
