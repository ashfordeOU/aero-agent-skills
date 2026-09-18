---
name: e2020-enable-threshold-maximum-bus-range
description: "Assess an adjustable turn on threshold that is expressed against the maximum direct current bus voltage, per clause 5.4.4.2.1 of ECSS-E-ST-20-20C. Use when an enable setting is quoted as a fraction and the reference behind that fraction decides the volts it really commands. Refer each settable fraction into volts through the maximum bus value, restate a fraction quoted against the nominal bus onto the maximum reference, report the volts a reader loses by taking the wrong one, and test the resulting ladder against the window between the equipment turn on floor and the lowest steady state bus. Flag a fraction with no stated reference. Trigger: ecss, e-st-20-20c-clause-5-4-4-2-1, enable-threshold-maximum-bus-referral, turn-on-threshold-maximum-dc-bus-voltage, enable-threshold-reference-conversion, enable-setting-ladder-maximum-bus, turn-on-threshold-window-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e-st-20-20c-clause-5-4-4-2-1, e2020-enable-threshold-maximum-bus-range, enable-threshold-maximum-bus-referral, turn-on-threshold-maximum-dc-bus-voltage, enable-threshold-reference-conversion, enable-setting-ladder-maximum-bus, turn-on-threshold-window-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Enable Threshold Range on the Maximum Bus (space-systems/ecss/e2020-enable-threshold-maximum-bus-range)

Use when the task is clause 5.4.4.2.1 of ECSS-E-ST-20-20C: the adjustable turn
on threshold of a protection function is expressed against the maximum direct
current bus voltage. This leaf takes the declared ladder of fractions, the
reference the specification actually used, and the bus window the enable point
has to be crossed in, and reports the volts each setting commands.

## Domain quick reference

- The maximum bus value and the nominal bus value are different numbers, and a
  fraction means different volts against each. On a bus whose nominal is 28 V
  and whose maximum is 32 V, the same 70 percent is 19.6 V against nominal and
  22.4 V against maximum — a 2.8 V error, larger than most of the margins the
  threshold is placed with.
- Restating between the two references is a single ratio: a fraction of the
  nominal bus becomes a fraction of the maximum bus scaled by nominal over
  maximum. The volts do not move; only the number quoting them does, which is
  why the restated figure and the original have to agree in volts.
- A fraction with no reference is not a conservative reading, it is an
  ambiguous one. Assuming the clause reference to carry on is a working
  assumption to be reported, not a defect that has been resolved.
- The maximum bus value is a ceiling, not a target. A setting above 100 percent
  of it asks the enable point to sit where the bus never goes, so the load
  never comes on however the protection behaves.
- Usable settings are decided in volts, against the bus. The enable point has
  to sit at or above the floor the equipment can turn on from and at or below
  the lowest steady state bus voltage, otherwise the bus never climbs through
  it. The count of survivors is the adjustment the operator really has.
- The span the ladder covers in volts is the property the design owes, not the
  count of positions on it. A wide ladder with settings clustered at one end
  can cover fewer usable volts than a short one placed well.

## Workflow

1. Validate the maximum bus value, the nominal bus value and the ladder; a
   maximum below the nominal is an input error, and an empty ladder is not an
   adjustable threshold.
2. Normalise the stated reference into the maximum bus value, the nominal bus
   value, or unstated, and record which was found.
3. Refer every setting into volts: directly through the maximum bus value when
   it is already quoted that way, through the nominal bus otherwise.
4. Restate each setting as a fraction of the maximum bus so the ladder reads in
   the reference this clause asks for, and report the volts the wrong reference
   would have shifted each setting by.
5. Derive the span the ladder covers in volts and compare it with any span the
   project requires, treating an exact landing on the bound as met.
6. Keep the settings lying between the equipment turn on floor and the lowest
   steady state bus voltage, and count them.
7. Return the restated ladder, the span, the usable settings and a verdict,
   with a finding for an unstated reference, a setting above the maximum bus,
   a span shortfall and an empty usable set.

## Pitfalls

- Carrying a nominal-referenced fraction into a maximum-referenced field
  unchanged. The number survives the copy and the volts move, which is the
  most common way this threshold ends up set where nobody intended.
- Restating the fraction and not checking the volts. The restatement is only
  correct while both readings command the same volts, and that equality is the
  test that catches a swapped ratio.
- Treating an unstated reference as the clause reference and saying nothing.
  The reader downstream cannot tell an assumption from a statement.
- Accepting a setting above the maximum bus value because the ladder allows
  it. The bus never reaches it, so the enable point is unreachable no matter
  how the protection is wired.
- Judging the ladder by how many positions it has. The usable span in volts is
  what the threshold is placed inside; positions outside the bus window are
  not adjustment.
- Relaxing the required span to fit a ladder that lands exactly on it. The
  equality is a representation question, absorbed by the tolerance in the
  comparison rather than by moving the requirement.

## Behavior contract (gate 3)

The reference normalisation, referral of each setting into volts, restatement
onto the maximum bus reference, reference shift in volts, span derivation,
required-span comparison, usable window filtering and verdict are exercised by
the gate 3 contract test:
scripts/test_e2020_enable_threshold_maximum_bus_range.py against
scripts/e2020_enable_threshold_maximum_bus_range_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_enable_threshold_maximum_bus_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
