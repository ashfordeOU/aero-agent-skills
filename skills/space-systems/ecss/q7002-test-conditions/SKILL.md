---
name: q7002-test-conditions
description: "Validate the condition set written on an outgassing run sheet. Use when a screening run is being booked under ECSS-Q-ST-70-02C and the declared point has to be reconciled with the method: grade specimen temperature, collector temperature and soak duration against their own bands, treat chamber pressure as a ceiling that low vacuum satisfies, require a named rationale and approval reference for each parameter that departs rather than one blanket note, and add pump-down, stabilisation, soak and cool-down to see whether the booked chamber time can hold the run. Trigger: ecss, q-st-70-02c, outgassing-test-conditions, outgassing-specimen-temperature-setpoint, outgassing-collector-temperature-setpoint, outgassing-soak-duration, outgassing-chamber-pressure-ceiling, outgassing-condition-departure-justification."
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
  tags: [ecss, q-st-70-02-outgassing-scope, q7002-test-conditions, outgassing-specimen-temperature-setpoint, outgassing-collector-temperature-setpoint, outgassing-soak-duration, outgassing-chamber-pressure-ceiling, outgassing-condition-departure-justification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening -- Test Conditions (space-systems/ecss/q7002-test-conditions)

Use when the task is the condition-set step of a thermal-vacuum outgassing
screening under ECSS-Q-ST-70-02C: a run sheet declares a specimen
temperature, a collector temperature, a chamber pressure and a soak duration,
and the question is whether that is the screening point, a justified
alternative, or a departure nobody wrote down.

## Domain quick reference

- The screening point is a combination, not four independent numbers. Results
  are comparable between laboratories because every one of them was taken at
  the same combination, so moving any single member of it moves what the
  result means.
- Specimen temperature, collector temperature and soak duration are held by
  different control loops and each carries its own band. Grading them
  together hides which loop is the one that drifted.
- Chamber pressure behaves differently from the three set points: it is a
  ceiling. Any pressure at or below the limit satisfies the condition, and
  only exceeding it is a departure, so a deep vacuum is never a finding.
- A departure is allowed when the application requires one, but the
  justification belongs to the parameter that moved. A note covering "the
  test conditions" leaves no record of which parameter was agreed, and the
  approval reference is what makes the agreement findable later.
- Pump-down and stabilisation happen before the soak clock starts, and
  cool-down after it stops. The time booked on the chamber has to hold all
  four, or the soak is what gets shortened when the schedule tightens.

## Workflow

1. Read the four declared values, refusing a non-numeric or non-finite entry
   and a soak duration that is not positive.
2. Take the signed deviation of each set point from its reference and report
   all three, so a run at the point still carries evidence that it was.
3. Raise a departure for any set point outside its own band, naming the
   parameter, the declared value and the deviation.
4. Compare the declared pressure with the ceiling and raise a departure only
   when it is above, absorbing an exact equality at the limit as
   representation error.
5. For every departed parameter, require its own justification entry carrying
   a non-blank rationale and approval reference, and report a departure with
   no entry separately from one with an incomplete entry.
6. When a chamber window is booked, sum pump-down, stabilisation, soak and
   cool-down, compare it with the booking, and report the headroom.

## Pitfalls

- Treating the pressure like the temperatures. A pressure an order below the
  ceiling is exactly right; flagging it as "off nominal" trains the operator
  to ignore the pressure finding that matters.
- Accepting one blanket justification for several moved parameters. Each one
  was agreed for its own reason, or it was not agreed at all.
- Reading a departure as a failure. A justified alternative condition is a
  valid run; what is not valid is an alternative nobody recorded.
- Booking the soak duration as the chamber time. Pump-down and stabilisation
  come out of the same window, and the soak is what ends up cut.
- Widening a band to make an edge case pass. An exact equality at the limit is
  a representation question handled inside the comparison, not a reason to
  move the limit.

## Behavior contract (gate 3)

The signed set-point deviations, band comparisons, pressure ceiling,
per-parameter justification requirement and the chamber-window arithmetic are
exercised by the gate 3 contract test:
scripts/test_q7002_test_conditions.py against
scripts/q7002_test_conditions_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7002_test_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
