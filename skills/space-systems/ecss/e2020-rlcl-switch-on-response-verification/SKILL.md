---
name: e2020-rlcl-switch-on-response-verification
description: "Verify the switch-on response of a retriggerable latching current limiter against a stepped input. Use when an ECSS-E-ST-20-20C clause 5.4.4.4.1 test steps the bus from below the enable point up to nominal and has to prove what the output did: check the start point, the landing point, the settled dwell and the sharpness of the edge, time the delay from the interpolated input crossing to the output reaching its declared fraction of the regulated level, grade every run against both ends of the response window, then take the spread across the campaign. Refuses an inverted window, a nominal below the enable point and traces on different time bases. Trigger: ecss, e-st-20-20c, rlcl-switch-on-response, rlcl-turn-on-delay, bus-voltage-step-stimulus, response-window-verification, switch-on-repeatability-spread, retriggerable-limiter-enable-point."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-rlcl-switch-on-response-verification, rlcl-switch-on-response, rlcl-turn-on-delay, bus-voltage-step-stimulus, response-window-verification, switch-on-repeatability-spread]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — RLCL Switch-On Response Verification (space-systems/ecss/e2020-rlcl-switch-on-response-verification)

Use when the task is the switch-on verification of ECSS-E-ST-20-20C
clause 5.4.4.4.1 — driving the input of a retriggerable latching current
limiter from below its enable point up to the nominal bus in one step
and showing that the output answers inside the response the unit
declares.

## Domain quick reference

- The stimulus is a step and not a ramp. A ramp leaves the unit sitting
  near its enable point for a while, which is a different test: it
  measures where the comparator trips, not how fast the unit answers a
  bus that has come back.
- The start point sits below the enable point with margin, and it sits
  there long enough for the unit to be genuinely off. A step that begins
  a volt under the enable point, or that begins immediately after a
  previous run, measures a re-arm rather than a turn-on.
- The landing point is nominal, not merely somewhere above the enable
  point. The response is specified at the bus the unit will run on, and
  a step that stops short measures the unit at a voltage no operational
  case contains.
- The edge has to be sharp against the response being measured. When the
  source takes an appreciable fraction of the response window to reach
  nominal, the source and not the unit sets the number that comes out,
  so a blunt edge is reported as an unusable measurement rather than a
  slow unit.
- The delay is the gap between two instants: the input passing the
  enable point on the way up, and the output reaching its declared
  fraction of the regulated level. Both are interpolated crossings — the
  delay is usually a few sample intervals long, so a sample-counted
  instant carries an error of the same order as the quantity.
- The response window has two ends. Too slow is the obvious failure.
  Too fast is also a failure: a unit that answers sooner than its own
  declared confirmation time is not blanking the excursions it promised
  to blank, and that shows up as a spurious turn-on in flight rather
  than on the bench.
- One run proves nothing repeatable. The campaign is graded as a set —
  enough runs, and a spread across them inside the declared tolerance —
  because two runs either side of the window can average to a
  comfortable number.
- The margins, fractions, run count and tolerances are declared project
  policy rather than physical constants; the defaults in the logic
  module are a starting point a project substitutes its own values into.

## Workflow

1. Validate the policy and the unit spec: an enable point below nominal,
   a regulated output level, and a response window that is the right way
   up. An inverted window admits nothing and is a data error.
2. Validate each step profile against that spec — start point below the
   enable point with margin, landing point on nominal within tolerance,
   settled dwell at the start point, and the edge time against the
   fraction of the response window the policy allows.
3. Reduce each run to a delay. Where traces are given, interpolate the
   input crossing of the enable point and the output crossing of the
   reached level, and refuse a pair of traces whose output rises before
   its input as a shared-time-base defect rather than a fast unit.
4. Record a run whose output never reaches the level as a no-turn-on
   with the reason attached, instead of letting it fall out of the set
   and flatter the statistics.
5. Grade each run against both ends of the window, then against the
   guard band inside each end, so a run that only just fits is reported
   as thin rather than as a pass.
6. Take the count, mean, extremes and relative spread over the runs that
   produced a delay, and compare the spread with the repeatability
   tolerance.
7. Report the campaign at the worst thing present: an unusable
   measurement or too few runs before a breach of the window, a breach
   before a repeatability problem, and a thin margin last.

## Pitfalls

- Starting the step just below the enable point. It shortens the run and
  measures the comparator rather than the response, and it is the most
  common way a unit passes a switch-on test it should not have passed.
- Stepping to any voltage above the enable point instead of to nominal.
  The response is declared at nominal, and a short step reports a delay
  the flight configuration never produces.
- Accepting a soft source. A step whose edge occupies a tenth of the
  response window has folded the source into the answer; the result is
  not a slow unit but an invalid measurement, and the two get different
  fixes.
- Treating an early answer as a good answer. A delay under the floor
  says the unit is not honouring its own confirmation time, which is a
  finding against the blanking behaviour and not a margin.
- Reporting the mean of a scattered campaign. Runs either side of the
  window average to a number inside it, so the spread is graded
  alongside the mean and not instead of it.
- Counting samples for either instant. The delay is a handful of sample
  intervals, so quantisation is first-order here; both crossings are
  interpolated.
- Comparing a delay with a window edge by bare arithmetic. A run meant
  to land exactly on an edge or exactly on a guard band can fall a few
  units in the last place the wrong side of it; the comparison absorbs
  that representation error while the window stays as specified.

## Behavior contract (gate 3)

The policy validation, spec validation, step-profile validation, trace
validation, interpolated crossings, delay measurement, run grading,
spread statistics and the full campaign judgement are exercised by the
gate 3 contract test:
scripts/test_e2020_rlcl_switch_on_response_verification.py against
scripts/e2020_rlcl_switch_on_response_verification_logic.py (stdlib
unittest, offline).
Run:
python3 scripts/test_e2020_rlcl_switch_on_response_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
