---
name: q7004-thermal-cycling-conditions
description: "Define the cycling conditions an ECSS thermal test runs to: limits, transition rate, dwell and number of cycles. Use when the ECSS-Q-ST-70-04C condition clauses have to become a runnable profile and a chamber booking: check the span against a floor, take the transition rate as the slowest of the requested, chamber, item and policy limits and name which one bound it, build each dwell from the exponential decay of the item's lag plus the soak the test calls for, take the cycle count from the objective, then multiply out the cycle and campaign durations. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-cycling-profile-definition, cycling-transition-rate-limit, cycling-dwell-stabilization-time, thermal-cycle-count-selection, cycling-campaign-duration."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-thermal-cycling-conditions, thermal-cycling-profile-definition, cycling-transition-rate-limit, cycling-dwell-stabilization-time, thermal-cycle-count-selection, cycling-campaign-duration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Thermal Cycling Conditions (space-systems/ecss/q7004-thermal-cycling-conditions)

Use when the task is the cycling conditions of ECSS-Q-ST-70-04C — turning
two temperature limits into a profile that a chamber can actually run: the
rate between the extremes, the dwell held at each of them, how many times the
cycle repeats, and what all that adds up to in chamber hours.

## Domain quick reference

- Four numbers make a cycling profile and they are not independent. The
  limits fix the span, the span and the rate fix the transition time, the
  item's thermal response and the soak fix the dwell, and the objective fixes
  the repeat count. Change one and the chamber booking moves.
- The transition rate is the slowest of four candidates: what the test asked
  for, what the chamber can drive, what the item is allowed to see, and the
  policy ceiling. Reporting the rate without naming which one bound it hides
  whether a faster profile is available for the asking or forbidden.
- Dwell is not a round number. The item lags the chamber and that lag decays
  with the item's thermal time constant, so reaching a declared tolerance
  band from an initial offset takes the time constant times the logarithm of
  the offset over the tolerance. The dwell is that stabilization time plus
  the soak the test calls for, floored by the declared minimum.
- Which of those two set the dwell matters. A dwell set by the policy floor
  is a requirement; a dwell set by stabilization plus soak is a property of
  the item, and shortening it takes soak away from the item rather than slack
  away from the schedule.
- An item already inside the tolerance band needs no stabilization at all,
  and the arithmetic has to return zero rather than a negative time.
- The cycle count follows the objective, not the calendar. A screening run
  repeats few times and demonstrates nothing; a qualification run repeats the
  full count. The campaign duration is that count times the cycle duration,
  which is the number the facility actually books against.

## Workflow

1. Declare the objective and the two test limits. Reject a span below the
   policy floor rather than running a profile with nothing to exercise.
2. Resolve the transition rate against all four candidates and keep the name
   of the binding one with the number.
3. Compute the transition time as the span over the rate, in consistent
   units; a rate in kelvin per minute against a time in seconds is the most
   common arithmetic slip here.
4. Build each dwell separately for the hot and the cold extreme, because the
   soaks can differ, and record for each whether stabilization or the floor
   set it.
5. Assemble the cycle as two transitions plus the two dwells, take the cycle
   count from the objective, and multiply out the campaign duration.
6. Close with the findings the profile raises and with the dwell-clock duty:
   the dwell starts when the controlling sensor enters the tolerance band.

## Pitfalls

- Starting the dwell clock at the set point change. The item is still
  travelling then, so the recorded dwell includes the stabilization twice
  over on paper and not at all in the hardware.
- Quoting the requested rate as the test rate. A chamber that cannot drive it
  silently stretches every transition, and the campaign overruns by the
  difference multiplied by twice the cycle count.
- Treating the item allowable rate as a target. It is a ceiling set to
  protect the hardware; running at it leaves no margin for a chamber that
  overshoots on the way into the dwell.
- Using one dwell for both extremes out of habit. The stabilization is
  symmetric only if the item's response is, and the soaks are usually set by
  different mechanisms at the hot and cold ends.
- Shortening the dwell to fit the schedule when stabilization dominates it.
  What gets removed is time at temperature, so the cycles still run but the
  item no longer reaches the condition the test was written for.
- Comparing the computed dwell against the floor by bare arithmetic. A dwell
  built from a logarithm can land a few units in the last place either side
  of the floor; the comparison absorbs that representation error while the
  floor itself stays untouched.

## Behavior contract (gate 3)

The span check, rate resolution with its binding constraint, transition time,
stabilization and dwell construction, cycle arithmetic, cycle count and
campaign duration are exercised by the gate 3 contract test:
scripts/test_q7004_thermal_cycling_conditions.py against
scripts/q7004_thermal_cycling_conditions_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7004_thermal_cycling_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
