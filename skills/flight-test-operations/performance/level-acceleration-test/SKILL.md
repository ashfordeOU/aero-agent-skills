---
name: level-acceleration-test
description: "Use when you must reduce an accelerated level flight run from a fixed-wing aircraft flight test: convert the calibrated airspeed samples to true airspeed with the ISA density at the test altitude, smooth the airspeed trace with a moving average, compute the acceleration from the smoothed trace with central differences, and evaluate the specific excess power by the total energy method, P_s = dh/dt + V a / g. Estimates the excess thrust at the test weight from P_s and, when the drag polar is provided, the thrust available and the thrust required, then corrects the specific excess power to the reference weight and the standard density. Produces the smoothed trace, acceleration, specific excess power, excess thrust, and sustained acceleration verdict gating the acceleration capability assessment. Trigger: level acceleration, accelerated level flight, specific excess power, total energy method, excess thrust flight test, Ps, thrust available, acceleration capability."
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
  tags: [level-acceleration-test, accelerated-level-flight, specific-excess-power, total-energy-method, excess-thrust-flight-test, level-acceleration-run, thrust-available, acceleration-capability, constant-altitude-run]
  version: 0.1.0
  author: Aero Agent Skills
---

# Level Acceleration Flight Test (flight-test-operations/performance/level-acceleration-test)

Use when the task is acceleration capability flight testing at constant
altitude: the total energy (TPS) reduction of an accelerated level
flight run into the specific excess power P_s, the excess thrust (the
drag gap), the acceleration, and the sustained acceleration speeds of
the test band. The input is the recorded airspeed versus time trace of
the run at the test weight and altitude; the output is the reduced
P_s and excess thrust data an operator compares with the level flight
requirements, plus the thrust available estimate when the drag polar is
provided. Calibration, time alignment, and raw channel filtering of the
recorder belong to flight-test-data-reduction, not to this leaf.

## Domain quick reference

- Units: forces and weight in N, speeds in m/s, density in kg/m^3,
  time in s, g = 9.80665 m/s^2. P_s is specific power, power per unit
  weight, in m/s.
- Test technique: a level acceleration run at full throttle and
  constant altitude through the speed band, with time, calibrated
  airspeed, pressure altitude, outside air temperature, and weight
  recorded per sample; straight flight, fixed configuration.
- ISA atmosphere: isa_conditions(altitude_m) returns the temperature
  (K), pressure (Pa), and density (kg/m^3): T = 288.15 - 0.0065 h in
  the troposphere to 11000 m (216.65 K isothermal above), pressure
  from the hydrostatic balance, rho = P / (R T). Worked: at 8000 m,
  T = 236.15 K, P = 35599.8 Pa, rho = 0.52517 kg/m^3 (density ratio
  0.4287); at sea level 1.225 kg/m^3.
- Equivalent to true airspeed: true_airspeed_from_eas,
  V_tas = V_eas * sqrt(rho0 / rho), equal dynamic pressure at the test
  density, the standard subsonic conversion. Worked: 110 m/s EAS at
  8000 m gives 168.0 m/s true airspeed.
- Smoothing: smooth_trace applies a centered moving average over an
  odd window, clipped at the trace ends; even windows raise. A linear
  ramp is preserved exactly wherever the full window fits. Worked:
  window 5 on the 150 to 170 m/s ramp keeps sample 10 at 160.0 m/s.
- Acceleration: acceleration_from_trace differentiates the smoothed
  trace, a = dV/dt by central differences, one-sided at the two ends;
  times must be strictly increasing. Worked: the 150 to 170 m/s ramp
  over 20 s gives 1.0 m/s^2 on the assessment region.
- Total energy method: specific_excess_power,
  P_s = dh/dt + V * a / g, the energy height rate. Level flight has
  dh/dt = 0 so P_s = V * a / g; the dh/dt term covers slightly
  non-level runs. Worked: 160 m/s at 1 m/s^2 gives 16.315 m/s.
- Excess thrust: excess_thrust_from_ps, delta_T = W * P_s / V, the
  drag gap, thrust available minus drag. For a level run this equals
  (W / g) * a, Newton's second law along the path. Worked: 250000 N at
  160 m/s gives 25492.9 N, independent of speed.
- Drag polar: lift_coefficient CL = W / (0.5 * rho * V^2 * S),
  drag_coefficient CD = cd0 + k * CL^2, and drag_from_polar
  D = 0.5 * rho * V^2 * S * CD, the thrust required for steady level
  flight at that speed. Worked at 160 m/s, S 122.6 m^2: CL 0.3034, CD
  0.02386, D 19667.8 N.
- Thrust available: thrust_available_estimate, T = delta_T + D from
  the measured drag gap and the polar drag. The aircraft sustains the
  acceleration at a given speed when T > D, that is when the measured
  excess thrust is positive. Worked: 45160.8 N at 160 m/s.
- Reference corrections (documented simplified): weight_corrected_ps,
  P_s_ref = P_s * W_test / W_ref at constant excess thrust, first
  order while the induced drag change over the weight difference is
  small; density_corrected_ps, P_s_std = P_s *
  (rho_test / rho_std)^(lapse_exp - 0.5) at constant indicated
  airspeed with the jet thrust lapse exponent, default 0.7, the same
  model the climb leaf applies. Worked: 250000 N to 240000 N gives
  16.995 m/s; rho ratio 0.9 gives 15.975 m/s; combined 16.641 m/s.
- Assessment region: the reported means average the samples where the
  smoothing window and the central difference stencil are both full,
  indices (window + 1) / 2 to n - (window + 1) / 2; near-edge samples
  carry clipped windows and reduced smoothing.
- Model caveat: the polar omits the compressibility drag rise, so the
  drag and thrust available estimates run optimistic at high Mach; the
  excess thrust from the measured acceleration does not depend on the
  polar and needs no model.

## Workflow

1. Fly the level acceleration: trim at the entry speed, full throttle,
   constant altitude, no configuration change through the band; record
   time, calibrated airspeed, pressure altitude, OAT, and weight.
2. Convert the airspeed samples to true airspeed with
   true_airspeed_from_eas, using isa_conditions at the test altitude,
   or the measured day density when recorded (module
   scripts/level_acceleration_test_logic.py).
3. Smooth the true airspeed trace with smooth_trace over an odd window
   (5 is the default for 1 Hz recording; widen it for noisier traces).
4. Differentiate with acceleration_from_trace to the acceleration of
   the smoothed trace; the recorded times must be strictly increasing.
5. Evaluate the specific excess power per point with
   specific_excess_power, dh/dt = 0 for the level run or the recorded
   climb rate for a slightly non-level run.
6. Estimate the excess thrust per point with excess_thrust_from_ps at
   the test weight; the drag gap needs no polar.
7. When the wing area, cd0, and k are available, add the polar drag
   with drag_from_polar and close to the thrust available with
   thrust_available_estimate; the speeds where the excess thrust is
   positive are the sustained acceleration speeds of the band.
8. Correct the measured specific excess power to the reference
   condition with weight_corrected_ps and density_corrected_ps, or
   ps_at_reference_conditions for the combined correction.
9. For the one-pass reduction call level_acceleration_summary with the
   times, the true airspeed trace, the test weight, the altitude or
   density, and optionally the polar and the reference conditions; it
   returns the smoothed trace, the acceleration, P_s, the excess
   thrust, the per-sample and band sustained verdicts, and the mean
   values over the assessment region.
10. Report the P_s curve, the excess thrust, the sustained
    acceleration speeds, and the thrust available estimate for the
    acceleration capability assessment.

## Worked example

Level acceleration run at 8000 m on the standard day (rho 0.52517
kg/m^3): true airspeed from 150 to 170 m/s over 20 s, recorded at 1 s
intervals (21 samples), W = 250000 N, S = 122.6 m^2, CD0 = 0.02,
K = 0.042. Smoothing window 5.

- Acceleration: the ramp slope is 1.0 m/s^2; the smoothed interior
  keeps it exact and the mean over the assessment region (samples 3 to
  17) is 1.000 m/s^2.
- Specific excess power at 160 m/s: P_s = 160 * 1.0 / 9.80665 =
  16.315 m/s; the underlying motion carries P_s = V / g from 15.296
  m/s at the 150 m/s entry to 17.335 m/s at the 170 m/s exit.
- Excess thrust: delta_T = 250000 * 16.315 / 160 = 25492.9 N, equal to
  W * a / g, constant across the run; positive everywhere, so the
  whole band is sustained acceleration.
- Drag polar at 160 m/s: CL = 0.3034, CD = 0.02386,
  D = 19667.8 N, the thrust required; thrust available
  T = 25492.9 + 19667.8 = 45160.8 N. The mean drag over the smoothed
  band is 19686.8 N and the mean thrust available 45179.8 N.
- Constant speed check: the same airplane at 160 m/s constant over
  20 s gives a = 0, P_s = 0, and delta_T = 0 exactly; the verdict is
  not accelerating, and the thrust available collapses to the drag,
  19667.8 N.
- Weight correction to the 240000 N reference weight:
  P_s = 16.315 * 250000 / 240000 = 16.995 m/s at the 160 m/s point;
  the excess thrust is unchanged by the constant excess thrust
  assumption.

## Verification

- ISA anchors: sea level (288.15 K, 101325 Pa, 1.225 kg/m^3), 8000 m
  (236.15 K, 35599.8 Pa, 0.52517 kg/m^3), tropopause 216.65 K with
  density ratio 0.2971, isothermal above.
- EAS to TAS identity at the sea level density and 168.0 m/s for
  110 m/s EAS at 8000 m, within 1 percent.
- Smoothing preserves a linear ramp on the interior exactly and leaves
  a constant trace unchanged; odd windows only.
- Acceleration of a linear ramp equals the slope; a constant trace
  gives exactly zero; the quadratic trace reproduces 2 t by central
  differences.
- Worked anchors reproduced within 1 percent: P_s 16.315 m/s, excess
  thrust 25492.9 N equal to W * a / g, drag 19667.8 N, thrust
  available 45160.8 N at 160 m/s; the constant speed sub-case is
  exactly zero.
- The one-pass summary equals the per-point scalar chain over the
  assessment region, and the mean thrust available equals the mean
  drag plus the mean excess thrust (round-trip identity).
- Corrections are identities at the reference weight and density and
  reproduce the worked anchors within 1 percent.
- ValueError on non-positive speeds, weights, and densities, even
  windows, non-increasing times, mismatched lengths, partial polar
  arguments, and a trace too short for the window (all asserted in the
  contract test).

## Related leaves

- flight-test-operations/performance/climb-performance-flight-test:
  the steady climb measures P_s as dh/dt; the level acceleration
  measures the same specific excess power as (V / g) * a, and the two
  runs share the weight and density correction models.
- flight-test-operations/performance/engine-flight-test: converts the
  measured drag gap plus the polar drag into the installed thrust and
  verifies the engine performance; this leaf measures the gap itself.
- flight-test-operations/performance/takeoff-distance-determination:
  integrates the same a = (T - D) * g / W relation over the ground
  roll, the accelerating case on the runway.
- flight-test-operations/planning/flight-test-data-reduction:
  calibration correction, time alignment, and raw trace filtering
  precede this reduction.
- flight-test-operations/planning/telemetry-data-acquisition: sizes
  the airspeed, altitude, and time channels the recorded trace comes
  from.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 skills/flight-test-operations/performance/level-acceleration-test/scripts/test_level_acceleration_test.py

The test covers the worked example within 1 percent, the constant
speed zero sub-case, the ISA and EAS to TAS anchors, smoothing and
central difference identities, the polar chain, the reference
corrections, the one-pass summary against the per-point scalar calls,
and ValueError rejection of non-physical inputs, even windows, and
malformed traces.

## Pitfalls

- Routing analytical excess power questions here: computing P_s from
  thrust, drag, speed, and weight, energy height trades, and zoom
  climb belong to flight-mechanics/performance/energy-height; this
  leaf is the flight test side, reducing the recorded acceleration
  trace of a flown run.
- Routing engine questions here: engine systems checks, fuel flow,
  EGT margins, and installed thrust determination belong to
  engine-flight-test; the level acceleration provides the drag gap,
  not the engine limits.
- Routing channel reduction questions here: calibration correction,
  time alignment, and recorder filtering belong to
  flight-test-data-reduction; this leaf starts from the converted,
  aligned trace.
- Confusing the drag gap with the installed thrust: the excess thrust
  is T - D, so converting it to the installed thrust requires the
  drag, see engine-flight-test.
- Differentiating the raw trace: differentiate the smoothed trace, or
  the scatter in the recorded airspeed dominates the acceleration.
- Trusting the near-edge samples: clipped smoothing windows distort
  the first and last (window - 1) / 2 samples; judge the band on the
  assessment region.
- Using an even smoothing window: the centered stencil needs a
  midpoint and raises.
- Forgetting the weight and density corrections before comparing
  runs: the measured P_s at the test weight and day does not give the
  reference acceleration capability directly.
- Treating the polar drag estimate as the measured result: the
  parabolic polar without compressibility runs optimistic at high
  Mach; the measured excess thrust stands alone.
- A zero or negative excess thrust is a finding, not an error: the
  speed is beyond the sustained acceleration capability, and the
  verdict reports it.

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; accelerated level
  flight testing with the total energy method is common methodology in
  the FAR 25.101 general performance context, summary-only per
  standards-map.yaml. No standard text is quoted.
- compliance: STANDARDS-REF, gated: false.
