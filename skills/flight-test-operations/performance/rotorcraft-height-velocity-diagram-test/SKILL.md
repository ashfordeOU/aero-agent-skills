---
name: rotorcraft-height-velocity-diagram-test
description: "Use when you must reduce a rotorcraft height-velocity (dead-man-curve) demonstration flight test from the hover and low-speed engine-failure runs: measure the recognition delay, the height loss and time to establish autorotation and complete the flare or landing from the baro/radar altitude traces, apply the reaction time allowance, interpolate the dead-man-curve boundary height where height loss plus recovery altitude equals the starting height at each speed, build the avoid-region map over the height and speed grid, and compare it against the predicted height-velocity diagram for the clearance verdict. Produces the recognition delay, the establishment and recovery times, the height-loss split with the flare and recovery altitudes, the boundary heights with and without the reaction allowance, and the per-speed clearance margins and verdicts that gate the demonstration. Trigger: rotorcraft-height-velocity-diagram-test, dead-man-curve boundary, hover engine-failure height-loss."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-test-operations
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [rotorcraft-height-velocity-diagram-test, dead-man-curve-boundary, hover-engine-failure-height-loss, height-velocity-boundary-interpolation, avoid-region-map]
  version: 0.1.0
  author: Aero Agent Skills
---

# Rotorcraft Height-Velocity Diagram Test (flight-test-operations/performance/rotorcraft-height-velocity-diagram-test)

Use when you must reduce the FAR 29 rotorcraft height-velocity
(dead-man-curve) demonstration flight test from the hover and low-speed
engine-failure runs (requirement named and framed only). Each
demonstration starts at 20 to 200 ft AGL at 0 to 40 KTAS, the engine
fails at hover or low speed, and the rotorcraft must be recognized,
autorotation established, and a flare and landing completed before the
touchdown sink exceeds the safe limit. This leaf reads measured marks and
baro/radar altitude traces only: the recognition delay, the time to
establish autorotation, the height lost before the flare and the recovery
altitude the flare consumes, the touchdown verdict per demonstration, the
reduced height-velocity boundary per speed, the measured avoid-region map
over the (height, speed) grid and the per-speed clearance verdict against
the predicted height-velocity diagram. The steady autorotative sink rates
and the predicted boundary table are quoted inputs from the
flight-mechanics autorotative-descent analytic leaf, never re-derived.
It pairs with flight-test-operations/performance/
rotorcraft-autorotation-flight-test, which owns the steady-descent
demonstration side (least-squares sink-rate regression over the steady
window, rotor-RPM checks, recovery to re-established level flight); a
passing high-start demonstration of this leaf keeps any brief steady
segment as flown and stops its reduction at the flare-initiation mark.

## Domain quick reference

- Recognition delay: tau_r = t_reaction - t_failure, the trace time of
  the first control input minus the trace time of the engine-failure
  event mark. The worked record shows 0.5 to 1.0 s across 0 to 40 KTAS.
- Recognition-phase height loss with allowance: h_rec + v_sink_end *
  allowance, the measured height lost over the recognition window plus
  the additional sink during the declared 1.0 s reaction time allowance.
  Module constants: SAFE_TOUCHDOWN_FPM = 600.0 ft/min (10 ft/s) and
  REACTION_ALLOWANCE_S = 1.0 s.
- Establishment time: t_estab = t_flare - t_reaction, from the first
  control input to the flare-initiation mark. The flare duration is the
  contact time minus the flare mark.
- Height-loss split: h0 = h_lost_to_flare + h_recovery, the height lost
  from the starting height to the flare-initiation mark plus the flare
  recovery altitude above the touchdown altitude (0 ft for a touchdown);
  the split identity holds on every marginal passing demonstration.
- Touchdown verdict: PASS when the measured touchdown sink rate is at or
  below the declared 600 ft/min limit, inclusive at the limit.
- Boundary reduction at one speed: the linear crossing of the
  touchdown-sink-versus-starting-height line through the bracketing pair
  (highest FAILING starting height, lowest PASSING starting height) at
  the sink limit: h_b = h_fail + (h_pass - h_fail) * (limit - s_fail) /
  (s_pass - s_fail). With the reaction allowance the published boundary
  rises by v_sink_end * allowance, 6.0 ft in the worked record.
- Avoid-region map: one cell per (height AGL, speed KTAS) grid point,
  AVOID strictly below the reduced boundary at that speed (inside the
  dead-man-curve region), SAFE at or above it.
- Clearance: margin = predicted - measured, PASS when the measured avoid
  region does not extend above the predicted height-velocity diagram
  (margin >= 0, inclusive).
- Units are ft AGL, KTAS, seconds and ft/min throughout; the reduction is
  deterministic stdlib arithmetic on measured marks and traces, never a
  stochastic model.

## Workflow

1. Fix the demonstration record: the speed KTAS, the starting height in
   ft AGL, and the baro/radar altitude-loss-versus-time trace from the
   engine-failure event mark to the touchdown with the first control
   input mark and the flare-initiation mark.
2. Measure the engine-failure recognition delay with
   recognition_delay(t_reaction_s, t_failure_s): the first-control-input
   trace time minus the engine-failure mark time.
3. Measure the establishment and flare times: the time to establish
   autorotation and set up the flare with
   time_to_establish_autorotation(t_flare_s, t_reaction_s), and the flare
   duration as the touchdown time minus the flare mark.
4. Split the measured height loss with
   height_lost_to_flare(h_start_ft, h_flare_ft) (the recognition and
   establishment losses together, read off the trace) and
   flare_recovery_altitude(h_flare_ft, h_contact_ft): on a marginal pass
   the split sums to the starting height.
5. Give the touchdown verdict of the demonstration with
   touchdown_verdict(touchdown_sink_fpm): PASS at or under 600.0 ft/min,
   inclusive.
6. Apply the declared reaction time allowance to the recognition-phase
   height loss with recognition_loss_with_allowance(h_rec_measured_ft,
   sink_end_recognition_fps): the measured loss plus the sink during the
   1.0 s allowance, the read used for the published boundary.
7. Interpolate the height-velocity boundary height at each speed with
   interpolate_boundary_height(fail_h0_ft, pass_h0_ft, fail_sink_fpm,
   pass_sink_fpm): the linear crossing through the highest FAILING and
   lowest PASSING demonstration pair at the sink limit, then apply step 6
   for the boundary with the reaction allowance.
8. Build the measured avoid-region map over the (height, speed) grid with
   build_avoid_map(heights_ft, speeds_kt, boundary_ft): AVOID strictly
   below the reduced boundary at each speed, SAFE at or above it.
9. Judge the clearance against the predicted height-velocity diagram with
   clearance_verdict(measured_boundary_ft, predicted_boundary_ft) at each
   speed: PASS when the measured avoid region does not extend above the
   predicted boundary (margin >= 0), and report the margins and verdicts
   that gate the height-velocity demonstration.
10. Confirm the deterministic checks with the contract test
    scripts/test_rotorcraft_height_velocity_diagram_test.py.

## Worked example

Representative single-rotor rotorcraft height-velocity demonstration
record, speeds 0, 10, 20, 30, 40 KTAS over the 20 to 200 ft AGL sweep
(grid 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 150, 200 ft). Per-speed
measured parameters: recognition delay 0.6 to 1.0 s, recognition-window
end sink 6.0 ft/s, steady autorotative sink 33.0 ft/s easing to 28.0 ft/s
across the speeds (quoted from the flight-mechanics autorotative-descent
sink model), establishment times 2.2 to 1.7 s, declared minimum flare
altitudes 28.0 down to 14.0 ft.

- Hover column (0 KTAS) over the sweep: from 20 ft contact at 1.901 s at
  1318.3 ft/min FAIL; 30 ft 2.310 s 1619.1 FAIL; 40 ft 2.654 s 1872.2
  FAIL; 50 ft flare at 5.3 ft, 2.968 s 1801.8 FAIL; 60 ft flare at 15.3
  ft, 3.342 s 1405.3 FAIL; 70 ft flare at 25.3 ft, 3.877 s 838.6 FAIL;
  80 ft flare at 30.1 ft, 4.542 s 300.0 PASS; 90 ft and above PASS. The
  verdict flips between 70 ft (FAIL) and 80 ft (PASS).
- Passing 80 ft hover demo reduced marks: recognition delay 0.60 s, time
  to establish autorotation 2.357 s (the flare mark sits about 0.16 s
  after establishment, past the brief unreduced steady segment), contact
  4.542 s, flare duration 1.585 s; the time identity
  0.60 + 2.36 + 1.585 = 4.542 s holds.
- Per-speed boundary from the bracketing pairs (highest FAIL height and
  sink, lowest PASS height and sink, reduced boundary, boundary with the
  1.0 s allowance): 0 KTAS 70/838.6 and 80/300.0 to 74.430 ft (80.430
  with allowance); 10 KTAS 80/751.7 and 90/300.0 to 83.358 (89.358); 20
  KTAS 70/1151.4 and 80/502.7 to 78.500 (84.500); 30 KTAS 60/829.0 and
  70/300.0 to 64.329 (70.329); 40 KTAS 40/1182.3 and 50/300.0 to 46.600
  (52.600). The reduced dead-man-curve boundary rises from 74.430 ft at
  hover to the knee at 83.358 ft near 10 KTAS and falls to 46.600 ft at
  40 KTAS as recoverable translational energy grows.
- Marginal-pass split identity at every speed: 80 ft hover gives 49.877 +
  30.123 = 80.0 ft; 10 KTAS at 90 ft 54.497 + 35.503 = 90.0 ft; 20 KTAS
  at 80 ft 48.000 + 32.000 = 80.0 ft; 30 KTAS at 70 ft 45.938 + 24.062 =
  70.0 ft; 40 KTAS at 50 ft 34.465 + 15.535 = 50.0 ft; residual 0.00e+00
  at every speed.
- Measured avoid-region map: 60 cells, 27 AVOID and 33 SAFE, per speed 6,
  7, 6, 5, 3 AVOID cells below the 74.4, 83.4, 78.5, 64.3 and 46.6 ft
  boundaries: the avoid region tops out near the 10 KTAS knee and shrinks
  as speed adds recoverable energy.
- Clearance against the predicted height-velocity diagram (96.855,
  104.055, 103.110, 92.428 and 80.522 ft, quoted input from the
  flight-mechanics sink model in the standard energy reduction):
  measured with allowance 80.430, 89.358, 84.500, 70.329 and 52.600 ft,
  margins 16.424, 14.697, 18.610, 22.098 and 27.922 ft, PASS at every
  speed: the demonstration data show a tighter dead-man-curve region than
  the conservative analytic prediction.

## Verification

- Confirm recognition_delay(0.6, 0.0) = 0.6 s on the hover record and
  the mark-subtraction identity on any valid pair.
- Confirm recognition_loss_with_allowance(1.8, 6.0) = 7.8 ft with the
  default allowance and equals 1.8 ft with allowance_s = 0.
- Confirm time_to_establish_autorotation(2.957, 0.6) = 2.357 s on the
  marginal hover pass mark.
- Confirm the split identity on every marginal passing demonstration:
  height_lost_to_flare + flare_recovery_altitude equals the starting
  height to float noise, and the time identity recognition delay plus
  establishment time plus flare duration equals the failure-to-touchdown
  time.
- Confirm touchdown_verdict passes at 300.0 and exactly 600.0 ft/min and
  fails at 600.1 ft/min.
- Confirm interpolate_boundary_height(70.0, 80.0, 838.6, 300.0) =
  74.430 ft lies strictly inside the bracket and rises exactly 6.0 ft
  with the reaction allowance, and the per-speed ordering 74.430 <
  83.358 > 78.500 > 64.329 > 46.600 reproduces the dead-man-curve knee
  near 10 KTAS.
- Confirm build_avoid_map over the worked grid yields 60 cells with 27
  AVOID and 33 SAFE and marks a cell AVOID exactly when the height is
  strictly below the reduced boundary at that speed.
- Confirm clearance_verdict passes all five worked speeds with the quoted
  margins and passes inclusively when predicted equals measured.
- Confirm every non-physical input raises ValueError across the nine
  functions (26 offending-input cases in the contract test), and that
  repeated calls are identical.
- Run the contract test offline: python3
  scripts/test_rotorcraft_height_velocity_diagram_test.py (34 tests,
  deterministic).

## Related leaves

- flight-test-operations/performance/rotorcraft-autorotation-flight-test:
  the steady-descent demonstration reduction (least-squares sink-rate
  regression over the steady window, rotor-RPM checks, altitude lost to a
  recovery ending in re-established level flight), the high-altitude
  complement fenced by regime and framing.
- flight-mechanics/performance/rotorcraft-autorotative-descent: the
  analytic power-off sink model whose steady sink rates and predicted
  height-velocity diagram enter this leaf as quoted inputs.
- flight-mechanics/performance/rotorcraft-vertical-climb-performance:
  hover-axis climb prediction, out of scope here (every record of this
  leaf descends to a touchdown).

## Pitfalls

- Regressing the steady segment: a passing high-start demonstration
  carries a brief steady autorotation segment between establishment and
  the standard flare (about 0.16 s on the marginal hover pass). This leaf
  stops its reduction at the flare-initiation mark, keeps the segment as
  flown, and never fits it or runs rotor-RPM checks; those belong to the
  steady-descent demonstration leaf.
- Measuring the wrong height loss: the boundary identity requires the
  measured height loss plus the recovery altitude to equal the starting
  height on the marginal pass. Losses must be read from the baro/radar
  trace between the failure mark and the touchdown, never from the
  generator-side or analytic models.
- Applying the allowance twice: the published boundary already carries
  the 1.0 s reaction allowance (the measured boundary plus 6.0 ft in the
  worked record); judging clearance against the predicted diagram must
  compare like for like, the measured boundary with the allowance against
  the predicted boundary.
- Interpolating without a verdict flip: the boundary is only defined
  through a FAIL to PASS pair; if the highest failing demonstration sits
  at or under the limit or the lowest passing one above it, the height
  sweep must extend further, and the module raises ValueError rather than
  extrapolating.
- Treating the predicted diagram as measured data: the predicted
  height-velocity boundary is an input table from the analytic sink
  model, quoted not re-derived; this leaf only subtracts it for the
  clearance margin.
- Reproducing standard text: FAR 29 frames the height-velocity
  demonstration requirement by name only, no rule text is reproduced.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_height_velocity_diagram_test.py

The test covers the full reduction workflow of the SKILL.md: the
recognition delay on the worked hover record and its mark-subtraction
identity, the recognition-phase height loss with and without the reaction
allowance, the establishment and flare times on the marginal hover pass
mark, the height-loss split with the flare and recovery altitudes, the
PASS or FAIL touchdown verdict at and around the inclusive 600 ft/min
limit, the hover column reduction over the whole 20 to 200 ft sweep
(verdict flip between 70 and 80 ft, touchdown sinks within 0.05 ft/min of
the quoted values), the sampled-trace reduction and its time identity,
the marginal-pass split and time identities at every speed, the per-speed
height-velocity boundary reduction with the dead-man-curve knee near 10
KTAS and the exact 6.0 ft allowance rise, the measured avoid-region map
counts and strict-below region rule over the 60-cell grid, the per-speed
clearance margins and verdicts against the predicted height-velocity
diagram, the 26-case ValueError suite across the nine functions,
determinism of repeated calls, and the stdlib-only, no-randomness module
discipline.

## Compliance

- Standards referenced, not reproduced: FAR 29 is named and framed only
  (it frames the rotorcraft height-velocity demonstration requirement);
  the reduction relations above are standard flight-test engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
