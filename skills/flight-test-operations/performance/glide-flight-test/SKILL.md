---
name: glide-flight-test
description: "Use when you must run a glide flight test at idle thrust to measure the sink rate and the lift to drag ratio of an airplane: derive the sink rate from the altitude loss and the segment time, compute the lift to drag ratio from the true airspeed and the sink rate, correct the results for the weight change, the air density, and the residual idle thrust, and locate the best glide speed. Produces the measured and corrected sink rate in m/s, the lift to drag ratio, and the best glide speed that gate the glide test assessment. Trigger: glide test, sink rate, idle thrust, lift to drag, best glide speed, flight test."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [glide-testing, sink-rate, lift-to-drag, idle-thrust, flight-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# Glide Flight Test (flight-test-operations/performance/glide-flight-test)

Use when the task is glide flight testing for a flight test program:
sink rate and lift to drag measurement at idle thrust, weight and
density corrections, and best glide speed checks.

## Domain quick reference

- Units: speeds in m/s, altitude in m, time in s, sink rate in m/s,
  densities in kg/m^3, weights in consistent units (ratio only).
- sink_rate: v_sink = altitude_loss / time, the mean sink rate over a
  timed straight glide segment.
- descent_angle: gamma = atan(1 / (L/D)) in degrees, the steady glide
  path angle.
- ld_from_sink_rate: L/D ~= V_tas / v_sink, the small-angle
  horizontal-speed form, exact as the path angle approaches zero.
- sink_rate_from_airspeed: v_sink = V_tas * sin(gamma), gamma in
  degrees, converted inside the function.
- weight_corrected_sink_rate: v_sink_ref = v_sink_test *
  sqrt(W_ref / W_test); sink rate scales with the square root of the
  weight ratio at constant L/D.
- density_corrected_airspeed: V_ref = V_tas * sqrt(rho_test / rho_ref);
  at constant lift coefficient, true airspeed scales with the inverse
  square root of the air density.
- idle_thrust_corrected_ld: L/D_true = 1 / (1 / (L/D)_m - T/W),
  removing the residual idle thrust from the measured ratio.
- best_glide_speed: v_best = v_ref * sqrt((L/D)_max / (L/D)_ref).
- glide_ratio_from_distance: E = horizontal / altitude_loss, the
  horizontal distance covered per unit altitude lost.
- Idle power setting: engines at flight idle, gear and flaps in the
  test configuration, trimmed, hands-and-feet-off stabilized condition.

## Workflow

1. Stabilize the airplane at the test configuration with the engines
   at idle thrust; record altitude versus time over a straight,
   constant-heading glide segment.
2. Compute the sink rate with sink_rate from the altitude loss and
   the segment time.
3. Convert the measured calibrated airspeed to true airspeed for the
   test density altitude before any ratio is formed.
4. Compute the lift to drag ratio with ld_from_sink_rate from the
   true airspeed and the sink rate.
5. Apply the corrections: weight_corrected_sink_rate,
   density_corrected_airspeed, and idle_thrust_corrected_ld.
6. Locate the best glide speed with best_glide_speed from a reference
   speed and the maximum lift to drag ratio.
7. Report the measured and corrected sink rate, the lift to drag
   ratio, and the best glide speed for the glide test assessment.

## Pitfalls

- Using the calibrated airspeed instead of the true airspeed: sink
  rate and L/D need V_tas at the test density altitude, not the
  instrument reading.
- Treating the idle thrust as exactly zero: residual idle thrust lifts
  the measured L/D; idle_thrust_corrected_ld removes it when the
  thrust to weight ratio is known.
- Mixing the sink rate with the airspeed: L/D is V_tas / v_sink, not
  V_tas / altitude_loss and not V_tas / time.
- Scaling the sink rate linearly with weight: the correction is the
  square root of the weight ratio, not the ratio itself.
- Forgetting the density correction on the airspeed: V_ref =
  V_tas * sqrt(rho_test / rho_ref) at constant lift coefficient.
- Reading the small-angle form as exact at steep angles: V_tas /
  v_sink is the horizontal-speed form; use descent_angle for the
  exact atan form.
- A zero or negative sink rate has no glide: the segment is not
  descending, so L/D from the sink rate is undefined and must raise.
- Gliding in a turn or with configuration changes: the measurement is
  only valid in the straight, trimmed, hands-and-feet-off condition.

## Behavior contract (gate 3)

The sink rate, lift to drag, and correction logic is exercised by the
gate 3 contract test: scripts/test_glide_flight_test.py against
scripts/glide_flight_test_logic.py (stdlib unittest, offline). Run:
`python3 scripts/test_glide_flight_test.py`

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; glide test sink
  rate and lift to drag measurement is common flight-test methodology
  in the FAR 25.101 / 25.141 general performance context, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
