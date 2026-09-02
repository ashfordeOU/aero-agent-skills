---
name: high-angle-of-attack-testing
description: "Plan and run the high angle of attack flight test: calibrate the angle of attack sensor position error against a tower fly-by or trailing cone reference, size the post-stall and deep stall test points across configurations and center of gravity conditions, estimate the stall warning margin against the required margin in the certification context, and judge the departure resistance and spin entry resistance in the post-stall envelope. Produces the corrected AoA calibration, the HiAOA test matrix, the stall margin verdict, and the departure and spin resistance assessment. Use when the task is post-stall envelope definition, AoA instrumentation calibration, or deep stall testing. Trigger: high angle of attack, AoA calibration, deep stall, departure resistance, post-stall, spin entry."
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
  subdomain: envelope
  tags: [high-angle-of-attack, post-stall, deep-stall, aoa-calibration, position-error-correction, stall-margin, departure-resistance, spin-entry, stall-warning, flight-test-envelope]
  version: 0.1.0
  author: Aero Agent Skills
---

# High Angle of Attack Testing (flight-test-operations/envelope/high-angle-of-attack-testing)

Use when the task is the high angle of attack (HiAOA) flight test: the
post-stall and deep stall test envelope, angle of attack sensor position
error calibration, stall warning margin assessment, and departure and
spin entry resistance judgment. This leaf covers the envelope beyond the
stall boundary and the instrumentation calibration that makes the AoA
data meaningful; the stall boundary test matrix, warning onset
verification, and recovery demonstration at the stall are the
stall-characteristics-testing leaf.

## Domain quick reference

- HiAOA envelope: the angle of attack region from the stall angle
  through the post-stall range up to the maximum tested AoA, including
  the deep stall region where the aircraft can settle into a stable
  stalled attitude with the nose above the horizon. Each configuration
  and center of gravity condition is probed at the warning angle, the
  stall angle, post-stall steps, and the deep stall point.
- AoA position error: the local flow direction at the sensor differs
  from the free stream because of fuselage upwash and downwash and the
  sensor mounting position, so the indicated AoA carries a bias and a
  scale error. The correction relates indicated AoA to a reference AoA
  measured by an independent method.
- Reference methods: a tower fly-by gives a reference by flying at
  constant speed past a tower-mounted sighting baseline, and a trailing
  cone trailed behind the aircraft gives reference static pressure from
  which the flow angle is derived; both are used to calibrate the
  installed AoA sensor over the test range.
- Calibration model: corrected = bias + scale * indicated, fitted by
  least squares over the calibration points, with the residual spread
  judging the quality of the fit before the correction is applied to
  the flight data.
- Stall warning margin (FAR 25.201 / CS-25.201 context, paraphrased):
  the stall demonstration must show the stall break and the warning
  onset, and the warning must be distinct and must begin ahead of the
  stall with margin; in AoA terms the margin is the difference between
  the stall angle and the warning onset angle, compared with the
  required margin of the test program.
- Departure resistance (FAR 25.203 / CS-25.203 context, paraphrased):
  at and beyond the stall the aircraft must show no excessive pitch-up
  and no uncontrollable rolling or yawing; the departure resistance
  index scores the observed roll-off, yaw divergence, and pitch-up
  against reference levels.
- Spin entry resistance: with pro-spin controls applied at the high AoA
  points, the aircraft must resist entering autorotation; the observed
  roll-off and yaw rate against the allowed limits, plus the recovery
  altitude loss and turn count, give the verdict.

## Workflow

1. Build the HiAOA test matrix with
   build_test_matrix(configs, cg_conditions, warning_aoa_deg,
   stall_aoa_deg, max_aoa_deg, post_stall_step_deg): the matrix covers
   the warning onset, the stall angle, the post-stall progression, and
   the deep stall point for every configuration and c.g. condition.
2. Calibrate the AoA sensor with
   aoa_least_squares_calibration(indicated_aoas, reference_aoas) from
   the tower fly-by or trailing cone data, then correct every flight
   AoA with apply_aoa_correction(indicated_aoa_deg, calibration).
3. Compute the observed stall warning margin with stall_margin_deg
   (stall_aoa_deg, warning_aoa_deg) and judge it with
   stall_margin_verdict(stall_aoa_deg, warning_aoa_deg,
   required_margin_deg).
4. Score the departure behavior with
   departure_resistance_index(roll_off_deg, yaw_divergence_deg,
   pitch_up_deg) at each post-stall point.
5. Judge spin entry resistance with
   spin_entry_resistance_verdict(roll_off_deg, yaw_rate_deg_s,
   max_roll_off_deg, max_yaw_rate_deg_s) and the recovery with
   spin_recovery_verdict(altitude_loss_m, altitude_loss_limit_m,
   turns_to_recover, turns_limit).

## AoA position error calibration model

The installed sensor reports an indicated angle alpha_i that differs
from the true (reference) angle alpha_r by a position error that is
well modeled over the test range as

    alpha_r ~= bias + scale * alpha_i

with scale near 1 and bias in degrees. The least squares fit minimizes
the sum of squared residuals r_k = alpha_r,k - (bias + scale *
alpha_i,k) over the calibration points, giving

    scale = cov(alpha_i, alpha_r) / var(alpha_i)
    bias  = mean(alpha_r) - scale * mean(alpha_i)

The residual root mean square and the maximum absolute residual
(aoa_least_squares_calibration outputs) show how well the linear model
holds; a large residual at the ends of the range warns that the sensor
position error is nonlinear there and the correction should not be
extrapolated beyond the calibrated AoA range.

## Worked example

Tower fly-by calibration over five points: indicated [6.0, 8.0, 10.0,
12.0, 14.0] deg versus reference [8.2, 10.1, 12.0, 13.9, 15.8] deg.
The fit returns scale 0.95 and bias 2.5 deg, so corrected = 2.5 + 0.95
* indicated: 10.0 deg indicated corrects to 12.0 deg, matching the
reference. Residuals are near zero over the range, so the correction is
accepted.

Stall margin: with stall at 15.5 deg and warning onset at 12.0 deg the
margin is 3.5 deg; against a required margin of 2.0 deg the verdict is
ok. A warning onset at 14.0 deg would leave only 1.5 deg and would fail
the same requirement.

Departure resistance: roll-off 4 deg, yaw divergence 2 deg, pitch-up 1
deg give penalty 0.5 * 4/20 + 0.3 * 2/10 + 0.2 * 1/10 = 0.18, index
0.82, rated high. Roll-off 20 deg with yaw divergence 10 deg and
pitch-up 10 deg give index 0.0, rated low.

## Pitfalls

- Extrapolating the AoA correction beyond the calibrated range: the
  position error is linear only over the calibration points, so the
  deep stall points must stay inside the calibrated AoA range or the
  correction is carried outside its validity.
- Calibrating with a single reference point: the least squares fit
  needs at least two points with varying indicated AoA, otherwise
  neither bias nor scale can be separated.
- Confusing the stall angle with the stall warning onset angle: the
  warning margin is the difference between the two, and a warning that
  fires at or after the stall break carries no margin at all.
- Judging departure resistance from one axis only: roll-off alone
  misses yaw divergence and pitch-up, and the index combines all three
  motions.
- Testing the deep stall point without pro-spin control checks: the
  spin entry resistance verdict only means something when the aircraft
  is probed with pro-spin controls at the high AoA points.
- Using uncorrected AoA for the stall margin: the margin verdict is
  only valid on corrected AoA, otherwise a sensor bias of several
  degrees hides or fakes the margin.
- Passing negative angles, empty configuration lists, or non-finite
  data to the logic functions; the module raises ValueError instead of
  returning a meaningless matrix or verdict.

## Behavior contract (gate 3)

The calibration fit, correction, stall margin, departure resistance,
spin entry resistance, recovery, and test matrix logic is exercised by
the gate 3 contract test:
scripts/test_high_angle_of_attack_testing.py against
scripts/high_angle_of_attack_testing_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_high_angle_of_attack_testing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the HiAOA envelope
  practice, AoA calibration methods, stall margin, and departure
  resistance checks are common flight test methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
