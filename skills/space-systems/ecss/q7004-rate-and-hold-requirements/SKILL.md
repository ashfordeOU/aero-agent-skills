---
name: q7004-rate-and-hold-requirements
description: "Verify that a thermal test run obeyed its ECSS rate limits and earned the hold it claims. Use when an ECSS-Q-ST-70-04C temperature record has to be graded rather than planned: differentiate the logged series into per-interval rates in kelvin per minute, judge each against the hardware ceiling and against the requested rate's tolerance band over the declared transition only, locate the first instant from which the item stays inside the set-point band with its drift under the limit for the whole confirmation window, then measure the hold credited from there against the hold the procedure demanded. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-rate-and-hold-requirements, thermal-transition-rate-conformance, thermal-stabilization-criterion, thermal-dwell-credit, thermal-drift-limit-check."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-rate-and-hold-requirements, thermal-rate-and-hold-requirements, thermal-transition-rate-conformance, thermal-stabilization-criterion, thermal-dwell-credit, thermal-drift-limit-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Rate and Hold Requirements (space-systems/ecss/q7004-rate-and-hold-requirements)

Use when the task is grading what the chamber actually did against the rate
and hold clauses of ECSS-Q-ST-70-04C — reading a logged temperature series and
answering two questions: did the transitions stay inside their rate limits, and
was the item stabilized long enough for the dwell to count.

## Domain quick reference

- The rate requirement has two different shapes and both are live. A ceiling
  protects the hardware and is never to be crossed in either direction; a
  tolerance band around the requested rate says the run reproduced the profile
  it was written to. A run can satisfy the ceiling and still miss the band.
- The band applies to the transition, not to the dwell. Grading the dwell
  intervals against a transition rate reports an excursion on every sample
  where the item was correctly holding still, which is the most common way
  this check is made useless.
- Stabilization is not a temperature reading, it is a sustained condition. The
  item counts as stabilized from the first instant it stays inside the
  tolerance band around the set point for the whole confirmation window, with
  its drift over that window under the declared limit.
- Drift and band are separate criteria. An item can sit inside a wide band
  while still climbing steadily towards the edge, and that is not a
  stabilized item; the drift limit is what catches it.
- The credited hold starts at stabilization, not at the set-point change, and
  ends the moment the band is left. A run that dips out and comes back has two
  holds, and only the one that satisfies the requirement may be claimed.
- A confirmation window that no sample covers is a sampling failure, not a
  pass. The record has to contain evidence across the whole window before the
  window can be said to have been held.

## Workflow

1. Validate the logged series: strictly increasing timestamps, real
   temperatures, at least two samples to have a rate at all.
2. Differentiate it interval by interval into kelvin per minute, keeping the
   sign so a cooling excursion is distinguishable from a heating one.
3. Judge every interval against the ceiling on magnitude and record by how
   much each excursion crossed it.
4. Judge the intervals inside the declared transition window against the
   requested rate's tolerance band, and refuse a window that contains no
   complete interval rather than silently grading nothing.
5. Walk the series for the stabilization point: band satisfied continuously
   across the confirmation window, with the window's mean drift inside the
   drift limit and at least one sample covering the window.
6. Measure the unbroken hold from that point, compare with the requirement
   inside a named tolerance, and report every finding the run raised.

## Pitfalls

- Grading the dwell samples against the transition rate band. Every quiet
  interval then reads as a gross underspeed, and the real transition
  excursion is lost in the noise.
- Taking the first in-band sample as stabilization. The item may be passing
  through; only a sample that holds the band across the whole window with the
  drift under its limit marks the start of a creditable hold.
- Crediting the hold from the set-point change. The transition time is then
  counted as dwell, and the item spends less time at temperature than the
  report claims.
- Using a band test alone and ignoring drift. A steady climb inside a wide
  band satisfies every instantaneous check and still means the item has not
  settled.
- Treating a data gap across the confirmation window as continuity. With no
  sample inside the window there is no evidence the band was held, so the
  candidate point is refused rather than accepted by default.
- Comparing a computed rate, drift or hold against its limit with a bare
  strict inequality. These are all floats built from divisions, so a value
  physically sitting on the limit is compared within a named tolerance while
  the limit itself stays exactly as the procedure wrote it.

## Behavior contract (gate 3)

The series validation, per-interval rate differentiation, ceiling and
requested-band excursion detection over the declared transition, window drift,
stabilization search and credited hold measurement are exercised by the gate 3
contract test: scripts/test_q7004_rate_and_hold_requirements.py against
scripts/q7004_rate_and_hold_requirements_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7004_rate_and_hold_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
