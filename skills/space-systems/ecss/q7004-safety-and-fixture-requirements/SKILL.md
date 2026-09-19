---
name: q7004-safety-and-fixture-requirements
description: "Define the safety and fixturing provisions an ECSS thermal test needs before the chamber runs. Use when the ECSS-Q-ST-70-04C safety and mounting clauses have to become numbers: check the fixture-to-item expansion mismatch across the test span against an allowable strain, take the fixture load margin against the mounted mass and a safety factor, derive the over-temperature interlock set point from the test limit plus chamber overshoot and prove it still clears the item damage limit, then compute the wait before an operator may touch the hardware. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-test-fixture-requirements, fixture-item-expansion-mismatch, fixture-load-margin, chamber-over-temperature-interlock, test-personnel-access-cooldown."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-safety-and-fixture-requirements, thermal-test-fixture-requirements, fixture-item-expansion-mismatch, fixture-load-margin, chamber-over-temperature-interlock, test-personnel-access-cooldown]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Safety and Fixture Requirements (space-systems/ecss/q7004-safety-and-fixture-requirements)

Use when the task is the safety and fixturing side of ECSS-Q-ST-70-04C —
how the item is held while it is driven across the test span, and what has
to be true of the chamber, the interlocks and the access rules before
anybody presses start or opens the door afterwards.

## Domain quick reference

- A fixture is a load path and a thermal path at the same time. Across a
  hundred kelvin or more the fixture and the item change length at
  different rates, and in a joint stiff enough to carry launch loads that
  difference has nowhere to go but into the item as strain. The mismatch
  strain is the difference of the two expansion coefficients times the
  span, and it is compared against an allowable, not assumed small.
- The fix for a failed mismatch is a sliding or flexured interface, not a
  bigger bolt. Stiffening the joint raises the strain it transmits; it does
  not reduce the length difference that caused it.
- The fixture's structural margin is taken against the load it actually
  carries, which is the mounted mass times the design load factor times a
  safety factor. A margin quoted against the static weight alone is not a
  margin; it is a weighing.
- An over-temperature interlock does not sit on the test limit. The chamber
  overshoots its set point, so the interlock sits at the limit plus that
  overshoot plus a guard band, and the whole stack still has to clear the
  temperature at which the item is damaged with a declared clearance. If it
  does not, the test limit comes down or the chamber is changed; the
  interlock is not moved up to fit.
- The item is not the chamber. Its offset from ambient decays with its own
  thermal time constant, so an operator access rule keyed to the chamber
  reading is a burn or a cold-contact injury waiting to happen. The wait is
  the time constant times the logarithm of the present offset over the
  touch-safe offset, and it is zero for an item already in the band.
- Hazard groups are read off the conditions, not from habit: a cryogenic
  cold end, a hot surface, a vacuum run with its venting and outgassing,
  the lifting group a heavy assembly falls into, and the stored strain a
  failed mismatch leaves in the joint.

## Workflow

1. Validate the two test limits and the fixturing policy. An inverted or
   equal pair of limits is an input error, not a degenerate run.
2. Form the mismatch strain across the span and take its margin against
   the allowable. Record the margin, not just a pass or fail.
3. Build the design load from the mounted mass, the load factor and the
   safety factor, and take the fixture margin against its rated capacity.
4. Stack the interlock set point from the hot limit, the chamber overshoot
   and the guard band, and check the clearance to the item damage limit
   against the declared minimum.
5. Compute the access wait separately for the hot and the cold end, each
   against its own touch-safe temperature, since ambient sits between them
   and the two decays are not symmetric.
6. Categorize the run into its hazard groups and attach the duties each
   group brings, then close with the findings that block the run.

## Pitfalls

- Bolting a light-alloy fixture rigidly to a composite item and calling the
  interface conservative. It is conservative for load and severe for
  strain; the two requirements pull opposite ways and only the arithmetic
  says which one binds.
- Quoting a fixture margin against the static weight. The launch or
  handling load factor is what the fixture was rated for, and leaving the
  safety factor out of the applied load moves the margin by the factor.
- Setting the over-temperature interlock at the test limit. Every run then
  trips on normal overshoot, the interlock gets raised to stop the nuisance
  trips, and the protection it was installed for is gone.
- Reading the chamber thermocouple as the item temperature for access. The
  chamber arrives first and the item arrives one time constant at a time.
- Comparing a computed clearance or margin against its floor by bare
  arithmetic. A value built from a logarithm or a division can land a few
  units in the last place either side of the floor; the comparison absorbs
  that representation error while the floor itself stays untouched.
- Treating the hot and cold access waits as one number. Ambient sits
  between the two extremes, so the offsets differ and so do the waits.

## Behavior contract (gate 3)

The policy validation, mismatch strain and its margin, fixture load and
margin, interlock set point and clearance, touch-safe access waits and the
hazard grouping are exercised by the gate 3 contract test:
scripts/test_q7004_safety_and_fixture_requirements.py against
scripts/q7004_safety_and_fixture_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7004_safety_and_fixture_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
