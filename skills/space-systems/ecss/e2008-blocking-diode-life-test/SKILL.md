---
name: e2008-blocking-diode-life-test
description: "Verify that a blocking diode life test under ECSS-E-ST-20-08C clause 12.6.8 establishes stability over the mission rather than over the part of it the bench reached: confirm the run is both hot enough and loaded hard enough to accelerate, convert its hours into mission-equivalent hours through the Arrhenius factor those conditions buy, measure the signed drift of every watched parameter against its limit, and project the same drift rate to end of mission so a parameter that passes the run but not the mission is caught. Use when planning or reviewing a long duration blocking diode life test before qualification closes. Trigger: ecss, e-st-20-08c-clause-12-6-8, blocking-diode-life-test-extreme-conditions, blocking-diode-life-test-mission-coverage, blocking-diode-life-test-parameter-drift-limit, blocking-diode-life-test-end-of-life-projection, blocking-diode-life-test-acceleration-factor."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-blocking-diode-life-test, blocking-diode-life-test-extreme-conditions, blocking-diode-life-test-mission-coverage, blocking-diode-life-test-parameter-drift-limit, blocking-diode-life-test-end-of-life-projection, blocking-diode-life-test-acceleration-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Blocking Diode Life Test (space-systems/ecss/e2008-blocking-diode-life-test)

Use when the task is to plan or defend the long duration life test run on
blocking diodes under ECSS-E-ST-20-08C clause 12.6.8 -- at what
conditions, for how many hours that convert into mission hours, watched
through which parameters, and what the drift says about end of mission.

## Domain quick reference

- The clause asks for stability over time, and time here means mission
  time, not bench time. Bench hours become mission hours only through the
  acceleration the conditions buy.
- Conditions have to be extreme on two axes at once: a case temperature
  at or above the declared floor, and a loading at or above a declared
  share of the device rating. A long run at benign conditions buys
  equivalent hours slowly and can run for months without reaching the
  mission.
- Coverage is a declared floor, not the whole mission. Few programmes can
  run a life test to full mission duration; the floor fixes how much of
  it the test has to reach before the remainder is allowed to be
  extrapolated.
- Stability is two checks, not one. What the parameter did during the run
  is the first. What the same drift rate projects to at end of mission is
  the second, and a parameter can pass the first and fail the second.
  That second finding is the whole reason a life test is run early.
- Drift is a signed fraction of the starting value and is judged on its
  magnitude. A forward voltage that fell is as much a change as one that
  rose, and a parameter walking in either direction is not stable.
- Each watched parameter carries its own limit, and the limits are not
  interchangeable. Reverse leakage is allowed to move much further than
  forward voltage before it means anything.
- A parameter with no declared limit cannot be judged, so an unrecognised
  or unlimited parameter is a data defect rather than a passing reading.

## Workflow

1. Validate the life test policy first: hours floor, extreme-condition
   floors, mission duration, coverage floor and the per-parameter drift
   limits. An unrecognised parameter in the limit set is refused rather
   than ignored.
2. Take the conditions before anything else: the stress ratio against the
   rating, and the case temperature against its floor. Both have to hold
   or the run is long rather than accelerated.
3. Size the Arrhenius acceleration the case temperature buys against the
   use temperature, and convert the bench hours into mission-equivalent
   hours.
4. Compare the bench hours against the hours floor and the equivalent
   hours against the coverage floor. These are separate failures: a run
   can be long and still cover little, or short and strongly accelerated.
5. Take the signed drift of every watched parameter, group the
   measurements, and refuse a parameter measured twice or with no limit
   declared.
6. Judge each drift twice -- as measured, and projected to end of mission
   at the same rate -- and report the second set separately, because a
   parameter named only there passed the run.
7. Close on one verdict -- life test not performed, conditions not
   extreme, coverage short, parameter unstable, projected drift exceeded,
   or stability demonstrated -- reporting every inadequacy found, not
   only the first. A value landing exactly on a floor or a limit is
   accepted; the comparison tolerance absorbs representation error and
   the limit does not move.

## Pitfalls

- Reading bench hours as mission hours. A thousand hours at benign
  conditions is a thousand hours, and the clause is written about the
  mission the diode has to survive.
- Calling a long run an accelerated one. Duration and acceleration are
  independent, and only the second converts hours into mission coverage.
- Stopping at the measured drift. A parameter comfortably inside its
  limit after the run can be outside it at end of mission at the same
  rate, and that is the finding the test exists to produce.
- Taking drift as an absolute change. The limit is a fraction of where
  the parameter started, so the same millivolt means different things on
  different devices.
- Ignoring a parameter that fell. Magnitude is what is judged; a
  capacitance walking down is as much instability as one walking up.
- Sharing one drift limit across the parameter set. Reverse leakage and
  forward voltage do not move on the same scale and cannot be held to
  the same number.
- Stopping at the first finding. A run can be benign, short and unstable
  at once, and a report naming one of the three understates the repair.

## Behavior contract (gate 3)

The policy validation, the stress ratio and extreme-condition check, the
Arrhenius acceleration factor, the mission-equivalent hours and coverage
ratio, the signed per-parameter drift, the measured and projected
instability sets, and the life test verdict are exercised by the gate 3
contract test: scripts/test_e2008_blocking_diode_life_test.py against
scripts/e2008_blocking_diode_life_test_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_blocking_diode_life_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
