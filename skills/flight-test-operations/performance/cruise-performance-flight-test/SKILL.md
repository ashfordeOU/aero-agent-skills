---
name: cruise-performance-flight-test
description: "Use when you must plan and reduce a cruise performance flight test: schedule level cruise points across a Mach sweep at constant altitude with stabilized fuel flow runs, correct measured fuel flow from the test weight to the reference weight with the square-root weight correction, convert corrected fuel flow and true airspeed into range performance, fit a quadratic range performance curve versus Mach, and read off the maximum range cruise Mach at the vertex and the long range cruise speed at the 99 percent point. Produces the corrected fuel flow table, the fitted curve, the maximum range cruise Mach, the long range cruise Mach, and verdicts gating the cruise fuel economy flight test assessment. Trigger: cruise performance flight test, fuel flow versus Mach, Mach sweep at altitude, maximum range cruise speed, long range cruise speed."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [cruise-performance-flight-test, fuel-flow-versus-mach, stabilized-fuel-flow-runs, mach-sweep-at-altitude, weight-corrected-fuel-flow, maximum-range-cruise-speed, long-range-cruise-speed]
  version: 0.1.0
  author: Aero Agent Skills
---

# Cruise Performance Flight Test (flight-test-operations/performance/cruise-performance-flight-test)

Use when you must plan and reduce a cruise performance flight test
that measures fuel flow versus Mach number at constant altitude to
build the flight-test range performance curve: schedule the level
cruise test points across a Mach sweep with stabilized fuel-flow runs,
correct each measured fuel flow from the test weight to the reference
weight with the square-root weight correction, convert the corrected
fuel flow and the true airspeed into the range performance of each
point, fit a quadratic curve of range performance versus Mach by
ordinary least squares, and read off the maximum range cruise Mach and
the long range cruise speed. This leaf reduces MEASURED fuel-flow runs
from a dedicated cruise test; the analytic neighbors
flight-mechanics/performance/specific-range and breguet-range compute
cruise results from models instead, and level-acceleration-test and
engine-flight-test cover the other performance flight tests.

## Domain quick reference

- ISA speed of sound: a = sqrt(gamma * R * T), gamma = 1.4, R = 287.05
  J/(kg K); T = 288.15 - 0.0065 h below 11 km and T = 216.65 K in the
  isothermal stratosphere. True airspeed: V = M * a.
- Square-root weight correction: Wf_corr = Wf_measured *
  sqrt(W_ref / W_test). This is a documented engineering approximation
  valid for small weight differences at constant Mach and altitude,
  where induced drag dominates the cruise drag balance; it removes the
  test-weight effect so all runs reduce to one reference weight.
- Range performance at a point: rp = V_tas / Wf_corr (distance per
  unit fuel mass).
- Curve fit: rp(M) = c2*M^2 + c1*M + c0 fitted by ordinary least
  squares (normal equations, 3x3 Gaussian elimination inside the
  module; no external solver).
- Maximum range cruise Mach: M_mrc = -c1 / (2*c2), the parabola vertex,
  reported only when c2 < 0 (downward-bowed data).
- Long range cruise Mach: the larger root of c2*M^2 + c1*M + c0 =
  LRC_FRACTION * rp_max with LRC_FRACTION = 0.99, the faster Mach at
  which range performance falls to 99 percent of its maximum. It must
  sit above M_mrc (ordering verdict "lrc-faster").
- Units are SI throughout: m, s, kg, kg/s, m/s.

## Workflow

1. Build the test card with plan_test_matrix: the Mach sweep at the
   cruise altitude, one stabilized run per Mach, with a linear
   test-weight ramp from the start weight to the end weight across the
   sweep (each run burns fuel).
2. Fly the level stabilized runs and record wf_measured_kg_s, w_test_kg
   and altitude_m per point at each Mach.
3. Correct every measured fuel flow to the reference weight with
   corrected_fuel_flow (weight_correction_factor gives the factor).
4. Convert each point with range_performance using the true airspeed
   from tas_from_mach (isa_speed_of_sound for the altitude).
5. Reduce the whole set with reduce_cruise_test(points, w_ref) to get
   the point table, the fitted coefficients, max_rp_mach, max_rp,
   lrc_mach, residuals, and the reduction verdict.
6. Confirm the ordering with verify_speed_ordering(max_rp_mach,
   lrc_mach): the long range cruise speed is the faster 99 percent
   point.
7. Confirm the deterministic checks with the contract test.

## Worked example

Reference W_ref = 200000 kg at 10668 m (a = 296.51 m/s), seven
stabilized runs across the Mach sweep 0.72 to 0.84 with test weights
ramping 209000 kg down to 197000 kg. The measured fuel-flow table is
built from an exact quadratic model rp(M) = 90 - 6000*(M - 0.8)^2, so
the reduction recovers it exactly.

- At M = 0.80, W_test = 201000 kg: V = 0.8 * 296.51 = 237.21 m/s, the
  model gives rp = 90, Wf_corr = 237.21 / 90 = 2.6357 kg/s, and the
  correction factor sqrt(201000 / 200000) = 1.00250, so
  Wf_measured = 2.6423 kg/s. corrected_fuel_flow(2.6423, 201000,
  200000) returns 2.6357 kg/s.
- reduce_cruise_test on the fixture returns max_rp_mach = 0.800000
  (within 1e-6), max_rp = 90.0, coefficients c2 = -6000.0, c1 =
  +9600.0, c0 = -3750.0 (within 1e-3), since 90 - 6000*(M - 0.8)^2 =
  -6000*M^2 + 9600*M - 3750. Vertex M = -9600 / (2 * -6000) = 0.8.
- Long range cruise: solve -6000*M^2 + 9600*M - 3750 = 0.99 * 90 =
  89.1; discriminant 21600, roots 0.78775 and 0.81225, so lrc_mach =
  0.81225 (exact fitted root 0.812247), the larger root.
  verify_speed_ordering(0.8, 0.81225) = "lrc-faster".
- Residuals are all below 1e-9 (noise-free parabola) and the verdict
  is "maximum-found".
- Sanity case: range performance linear in Mach gives c2 near zero and
  a "no-maximum" verdict with no reported vertex or LRC Mach.

## Verification

- Confirm isa_speed_of_sound returns 340.29 m/s at sea level and
  296.51 m/s at 10668 m (within 0.1).
- Confirm corrected_fuel_flow(2.6423, 201000, 200000) returns 2.6357
  kg/s within 1e-3 and that range_performance(237.21, 237.21/90.0)
  returns 90 within 1e-6 (the exact-model round trip).
- Confirm the reduction recovers vertex 0.8, max 90, coefficients
  -6000/9600/-3750, and the LRC root 0.81225, with residuals below
  1e-9.
- Confirm the round trip: measured flow built as Wf_corr *
  sqrt(W_test/W_ref) reduces back to exactly Wf_corr at every point.
- Confirm every non-physical input raises ValueError: negative
  altitude or Mach, non-positive weights, non-positive fuel flow,
  fewer than 3 points, duplicate Mach, Mach outside (0.3, 1.0).
- Run the contract test offline: python3
  scripts/test_cruise_performance_flight_test.py (35 tests,
  deterministic).

## Related leaves

- flight-mechanics/performance/specific-range: analytic range
  performance and fuel economy calculation, the model counterpart of
  this measured-data reduction.
- flight-mechanics/performance/breguet-range: analytic cruise range
  from the Breguet equation.
- flight-test-operations/performance/level-acceleration-test: the
  accelerated level flight test that shares the cruise condition.
- flight-test-operations/performance/engine-flight-test: installed
  thrust and fuel flow verification at altitude.
- flight-test-operations/performance/climb-performance-flight-test:
  the climb side of the performance flight test campaign.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_cruise_performance_flight_test.py

The test covers the ISA speed of sound anchors at 0 m and 10668 m, the
true airspeed conversion, the weight correction factor and its inverse
round trip, the worked-example corrected fuel flow anchor, the range
performance conversion, the full fixture reduction (vertex 0.8, max
90, coefficients -6000/9600/-3750, LRC root, residuals below 1e-9,
point-table entries, verdicts), the linear-data no-maximum sanity
case, the test-card weight ramp from plan_test_matrix, the fixture
inverse-build consistency, and ValueError rejection of non-physical
inputs.

## Compliance

- Standards referenced, not reproduced: FAR 25 and CS 25 frame the
  cruise performance context for transport category airplanes
  (performance and flight test data requirements); the relations above
  are standard flight-test engineering methodology, summary-only per
  standards-map.yaml. No verbatim regulatory text.
- compliance: STANDARDS-REF, gated: false.
