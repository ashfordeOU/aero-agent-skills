---
name: e3102-thermal-performance-test
description: "Evaluate a two-phase heat transport thermal performance test against ECSS-E-ST-31-02C clause 5.6.9. Use when the task is mapping a transport device over its power and temperature envelope: subtracting the parasitic leak to get the power that actually crossed the device, forming the evaporator-to-condenser drop and the transport conductance it cost, grading each point against the capability interpolated at its own operating temperature, confirming every required power and sink-temperature cell was run to steady state, judging the start-up demonstration on the time transport took to establish from a cold device, and grading the regulation demonstration on the worst deviation held around the setpoint. Trigger: ecss, e-st-31-02c, two-phase-transport-performance-test, heat-transport-power-mapping, transport-capability-utilisation, evaporator-condenser-temperature-drop, heat-transport-start-up-demonstration, transport-setpoint-regulation-band, transport-steady-state-dwell."
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
  tags: [ecss, e-st-31-02-two-phase-transport-scope, e3102-thermal-performance-test, heat-transport-power-mapping, transport-capability-utilisation, evaporator-condenser-temperature-drop, heat-transport-start-up-demonstration, transport-setpoint-regulation-band, transport-steady-state-dwell]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Thermal Performance Test (space-systems/ecss/e3102-thermal-performance-test)

Use when the task is the thermal performance test of ECSS-E-ST-31-02C
clause 5.6.9 -- mapping a heat pipe, loop or capillary-pumped transport
assembly across the power and temperature envelope it is qualified for,
and adding the two demonstrations a steady map cannot make on its own:
start-up from a cold device, and regulation around a control setpoint.

## Domain quick reference

- The number being mapped is the transported power, not the heater
  draw. Whatever leaked to the surroundings between the heater and the
  evaporator never crossed the transport path, so the parasitic loss is
  subtracted before any grading happens. A map built on applied power
  credits the device with heat it never carried.
- Each mapped point is a pair: the power carried, and the
  evaporator-to-condenser temperature drop it cost. Their quotient is
  the transport conductance, which is the figure that actually tracks
  degradation from one test to the next. A point where the two ends read
  the same temperature yields no conductance at all; the instrumentation
  simply cannot resolve it, and that is a finding, not a zero.
- Transport capability is a function of operating temperature, not a
  single number. The capability a point is graded against is
  interpolated from the declared curve at that point's own condenser
  temperature, and a point outside the declared curve span is refused
  rather than extrapolated -- continuing the last slope is how a
  beyond-capability point comes back reported as compliant.
- The map is a matrix, so coverage is part of the result. Every required
  power and sink-temperature cell has to have been run, and run to
  steady state: a point taken while the assembly was still drifting
  records a transient, and a drift rate is the cheapest available proof
  that the dwell was long enough.
- Start-up is a separate demonstration because a two-phase device that
  runs well once primed can fail to prime at all. It is graded on two
  facts: whether transport established from the declared cold initial
  condition, and how long that took against the declared limit.
- Regulation is graded on the worst deviation over the sample record,
  not the mean. An assembly that averages onto its setpoint while
  excursions leave the band has not held the band.

## Workflow

1. Take the capability curve and check it is usable: at least two
   points, strictly increasing temperature, positive capability. A curve
   that is not monotonic is rejected rather than sorted, because the
   reordering would silently invent a capability nobody declared.
2. For each mapped point, subtract the parasitic loss from the applied
   power, form the temperature drop, and refuse a point whose condenser
   reads above its evaporator -- that geometry is reversed and the point
   is not interpretable.
3. Interpolate the capability at the point's condenser temperature,
   divide the transported power by it, and categorize the point as
   within, exactly on, or beyond the capability.
4. Assess the dwell: compare the recorded drift rate against the steady
   limit and mark an unsettled point as not accepted whatever its
   utilisation says.
5. Check the coverage matrix cell by cell and list the required power
   and sink-temperature combinations no point matched.
6. Grade the start-up demonstration on establishment and elapsed time,
   and the regulation demonstration on the worst deviation from the
   setpoint.
7. Close with one verdict: the performance is demonstrated only when
   every point is accepted, the matrix is complete, and both
   demonstrations passed.

## Pitfalls

- Reporting the heater setting as the transported power. The parasitic
  leak is often a few per cent near the top of the envelope and a large
  fraction at the bottom, so the error is worst exactly where the
  low-power start of the map is being qualified.
- Grading every point against one capability figure. The capability
  moves with operating temperature, and a cold-end point graded against
  a warm-end capability can be well beyond the real limit while the
  arithmetic reports margin.
- Extrapolating the capability curve past its declared span. The curve
  is evidence over the range it was measured on; beyond that it is a
  guess with a slope attached, and the guess always flatters the device.
- Accepting a point that was still drifting. A transient reads as a
  smaller temperature drop than the settled value, so an unsettled point
  reports a better conductance than the device actually has.
- Treating the mapping as complete because every point that was run
  passed. Coverage and pass rate are different questions, and a matrix
  with untried cells has simply not been mapped there.
- Comparing a utilisation, a drift rate or a start-up time against its
  limit by bare arithmetic. Each is the result of a division, so a case
  that is exactly on the limit can land a few units in the last place on
  the wrong side of it; the comparisons absorb that representation error
  while the limits themselves stay untouched.

## Behavior contract (gate 3)

The parasitic subtraction, temperature-drop and conductance formation,
capability interpolation with its extrapolation refusal, utilisation
grading, steady-state assessment, matrix coverage, start-up and
regulation demonstrations and the overall verdict are exercised by the
gate 3 contract test:
scripts/test_e3102_thermal_performance_test.py against
scripts/e3102_thermal_performance_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3102_thermal_performance_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
