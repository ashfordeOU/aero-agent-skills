---
name: e3102-pressure-cycle-test
description: "Define the pressure cycling fatigue test of a two-phase heat transport item under ECSS-E-ST-31-02C clause 5.6.6. Use when the task is turning a service cycle count and a life scatter factor into whole test cycles, checking that the applied pressure range envelops the service range at both ends instead of only at the peak, bounding the cycle and ramp rates so the run stays a mechanical duty cycle rather than a heating run, holding the declared temperature band, and closing acceptance on the post-cycling leak rate. Trigger: ecss, e-st-31-02c, pressure-cycle-life-scatter-factor, pressure-cycle-range-envelope, pressure-cycle-ramp-rate-limit, pressure-cycle-temperature-band, post-cycling-leak-acceptance."
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
  tags: [ecss, e-st-31-02-two-phase-heat-transport-scope, e3102-pressure-cycle-test, pressure-cycle-life-scatter-factor, pressure-cycle-range-envelope, pressure-cycle-ramp-rate-limit, pressure-cycle-temperature-band, post-cycling-leak-acceptance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Pressure Cycle Test (space-systems/ecss/e3102-pressure-cycle-test)

Use when the task is the pressure cycling test of ECSS-E-ST-31-02C
clause 5.6.6 -- how many cycles, between which two pressures, how fast,
at what temperature, and what the article has to look like afterwards.

## Domain quick reference

- The cycle count is the service count times a life scatter factor, and
  the service count is not just the launch. Ground pressurisations
  during integration, flight transients, and the thermally driven
  pressure excursions a two-phase loop sees every orbit all accumulate
  fatigue in the same envelope. The product is rounded up: a fraction of
  a cycle is not a cycle, and rounding down is a life shortfall.
- A scatter factor below unity would test less than the service life and
  is refused rather than applied.
- The applied range has to envelop the service range at both ends. A
  test that reaches the service peak but starts from a raised floor
  applies a smaller amplitude than the article sees, and fatigue damage
  goes with amplitude, so the run understates the damage while reading
  as a pass on peak pressure alone.
- Rate is bounded twice. The pressure ramp rate is bounded because a
  step is not a cycle, and the mean cycle rate is bounded because a fast
  run heats the working fluid and turns a mechanical duty cycle into a
  thermal one, which is a different test with different damage.
- Temperature matters because both the fluid saturation state and the
  material properties move with it; a cycling run outside the declared
  band is not the qualification condition.
- Acceptance has two independent parts. Leakage observed during cycling
  means the article did not complete the life, and that is true no
  matter how clean the final measurement reads; the post-cycling leak
  rate is then graded against its allowable on its own.

## Workflow

1. Validate the service cycle count as a whole number and the scatter
   factor as at least unity.
2. Form the required cycle count as the product rounded up to whole
   cycles, absorbing float representation error so an exact product does
   not gain a spurious cycle.
3. Grade the applied count against the requirement and report the
   shortfall, not just a verdict.
4. Validate both pressure ranges and grade the applied one for coverage
   at the low end and the high end separately, reporting the amplitude
   ratio so an under-amplitude run is visible.
5. Grade the mean cycle rate from count and duration, and the ramp rate,
   each against its own ceiling.
6. Grade the cycling temperature against the declared band, edges
   included.
7. Take the during-cycling leak observation as a boolean and grade the
   post-cycling rate against its allowable; fail on either.
8. Roll the six checks into one verdict and name every failed check.

## Pitfalls

- Counting only flight cycles. Ground pressurisations and orbital
  thermal excursions are the majority of the count for a two-phase loop,
  and omitting them shrinks the test by a factor before the scatter
  factor is even applied.
- Rounding the required count down or to nearest. The count is a floor
  on life demonstration, so it rounds up.
- Cycling from a raised floor because the facility cannot vent fully.
  Peak pressure alone is not the duty cycle; amplitude is what drives
  fatigue, and the shortfall is invisible in a peak-only report.
- Running the cycles as fast as the rig allows to save schedule. Beyond
  the rate ceiling the fluid heats and the test stops being the
  mechanical one that was specified.
- Reporting a clean final leak measurement after a leak was seen
  mid-run. A leak during cycling ends the life demonstration; a later
  tight reading does not restore it.
- Relaxing an allowable so an exactly-at-limit case reads as a pass.
  Equality at a limit is a representation question, handled by the
  tolerance inside the comparison.

## Behavior contract (gate 3)

The scatter-factor validation, required-count rounding, applied-count
grading, two-ended range envelope check with amplitude ratio, cycle-rate
and ramp-rate ceilings, temperature band check, post-cycling leak
grading and the rolled-up verdict are exercised by the gate 3 contract
test: scripts/test_e3102_pressure_cycle_test.py against
scripts/e3102_pressure_cycle_test_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3102_pressure_cycle_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
