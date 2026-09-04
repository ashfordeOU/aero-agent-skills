---
name: control-force-flight-test
description: "Use when you must reduce the measured control force records of a longitudinal flight test: calibrate the force transducer from applied loads and recorded counts with a closed-form least-squares fit, derive the stick force gradient versus calibrated airspeed from a speed sweep with the stable-gradient verdict, compute the stick force per g from pull-up maneuvers, extract the breakout force from the push-pull hysteresis width, and run the control centering check of the residual control position against its limit. Produces the calibrated force conversion, the gradient fit and stability verdict, force per g, breakout force and centering verdict, the measured-force complement to the position-side analysis of the stability pack. Trigger: control force flight test, stick force gradient, force per g, breakout force, control centering check, force transducer calibration, stick force stability, control force records."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: stability
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: stability
  tags: [control-force-flight-test, stick-force-gradient, stick-force-per-g, breakout-force, control-centering-check, force-transducer-calibration, stick-force-stability]
  version: 0.1.0
  author: Aero Agent Skills
---

# Control Force Flight Test (flight-test-operations/stability/control-force-flight-test)

Use when the task is reduction of the measured longitudinal control
force records of a flight test: calibrating the force transducer,
fitting the stick force gradient versus calibrated airspeed, the stick
force per g from pull-ups, the breakout force and the centering check.
This leaf reduces the measured FORCE side of the pitch control; the
position side (elevator angle trim curves and neutral points) belongs
to its sibling flight-test-operations/stability/static-stability-
flight-test. Pull (aft) forces are positive, push forces negative.
All fits are ordinary least squares computed with pure stdlib
closed-form sums (no numpy), deterministic and offline.

## Domain quick reference

- Calibration: least-squares fit of applied load y (lbf) against
  recorded counts x, y = a x + b with slope a = Sxy/Sxx and intercept
  b = y_mean - a x_mean over the closed-form sums Sxx = sum((x -
  x_mean)^2), Sxy = sum((x - x_mean)(y - y_mean)). The fitted line
  converts every recorded count to force during the test day.
- Stick force gradient: fit measured stick force (pull positive, lbf)
  against calibrated airspeed (KCAS) from a level-speed sweep. A
  positive slope (pull force increases with speed) is the stable
  convention and gives the verdict stable-gradient; a zero or negative
  slope gives unstable-gradient.
- Stick force per g: fit measured pull force against load factor from
  pull-up maneuvers at constant speed; the slope is the force per g,
  the load the pilot must pull for each additional g.
- Breakout force: from the push-pull hysteresis of the control, width
  = pull - push and breakout = width / 2, the half-width force that
  must be overcome before the control moves.
- Centering check: margin = limit - residual on the residual control
  position after release; verdict centered when the margin is
  non-negative, else exceeds-limit.
- Regression identities: on noise-free points the calibration
  reproduces the applied loads (predicted equals known), and a
  perfectly linear sweep returns r2 = 1.0.
- FAR-25 frames the certification context (reference-only); the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Calibrate: call calibrate_force_transducer(known_lbf, counts) with
   the applied loads and the recorded counts from the ground
   calibration, and keep slope_lbf_per_count and intercept_lbf for the
   whole test day.
2. Reduce the speed sweep: stick_force_gradient(speeds_kts,
   forces_lbf) returns the gradient slope_lbf_per_kt, intercept, r2
   and the verdict stable-gradient or unstable-gradient.
3. Reduce the pull-ups: force_per_g(load_factors, forces_lbf) returns
   slope_lbf_per_g (the force per g), intercept and r2.
4. Extract the breakout: breakout_force(push_lbf, pull_lbf) returns
   the hysteresis width and the half-width breakout force.
5. Run the centering check: centering_check(residual_deg, limit_deg)
   returns the margin and the centered or exceeds-limit verdict.
6. Combine the full reduction with control_force_report(...), which
   returns every sub-result plus the calibrated force at any requested
   predict count.
7. Confirm the deterministic checks with the contract test
   scripts/test_control_force_flight_test.py.

## Worked example

Reference transport pitch-force flight test, pull positive:

- Calibration: 20 lbf applied at 1230 counts, 60 lbf at 3250 counts.
  calibrate_force_transducer returns slope 0.019802 lbf/count and
  intercept -4.35644 lbf; the calibrated force at 2100 counts is
  37.2277 lbf.
- Speed sweep: V = 120, 130, 140, 150 KCAS with Fe = -3.8, -1.6, 0.5,
  2.9 lbf. stick_force_gradient returns slope 0.222 lbf/kt, intercept
  -30.47 lbf, r2 0.99927, verdict stable-gradient.
- Pull-ups: n = 1.0, 1.5, 2.0, 2.5 g with Fe = 1.2, 7.4, 14.3,
  20.8 lbf. force_per_g returns slope 13.14 lbf/g, intercept -12.07
  lbf, r2 0.99962.
- Breakout: push -4.2 lbf, pull 6.4 lbf gives hysteresis width 10.6
  lbf and breakout force 5.3 lbf.
- Centering: residual 0.42 deg against a 0.50 deg limit gives margin
  0.08 deg, verdict centered.

## Pitfalls

- Extrapolating the force calibration beyond its two points: the
  transducer is calibrated at 20 and 60 lbf (slope 0.019802 lbf/count,
  intercept -4.35644 lbf), and fewer than 2 calibration points or
  negative counts raise ValueError.
- Interpreting the gradient sign without the maneuver: the speed sweep
  gives slope 0.222 lbf/kt with verdict stable-gradient, and a
  reversed sweep returns unstable-gradient - the sign of the gradient
  carries the stability claim.
- Reading the pull-up fit as a speed effect: force_per_g fits the load
  factor pull-ups (slope 13.14 lbf/g), a different quantity from the
  speed gradient, so lbf/g and lbf/kt values are not comparable.
- Passing a push that is not more negative than the pull: the breakout
  comes from the push -4.2 lbf and pull 6.4 lbf pair (hysteresis width
  10.6 lbf, breakout 5.3 lbf), and pull not greater than push raises
  ValueError.
- Judging centering without the residual margin: a 0.42 deg residual
  against the 0.50 deg limit gives margin 0.08 deg and verdict
  centered, so the margin, not the raw residual, is the pass criterion;
  negative residuals and non-positive limits raise ValueError.
- Fitting gradients on too few points: fewer than 3 points for the
  gradient and per-g fits, and length mismatches, raise ValueError.

## Verification

- Confirm calibrate_force_transducer([20, 60], [1230, 3250]) returns
  slope 0.019802 lbf/count and intercept -4.35644 lbf, and that the
  predicted loads at the calibration counts equal the applied loads to
  1e-9 (regression identity).
- Confirm stick_force_gradient on the sweep returns slope 0.222
  lbf/kt, r2 0.99927 and verdict stable-gradient, and that a reversed
  sweep returns unstable-gradient.
- Confirm force_per_g returns 13.14 lbf/g with r2 0.99962.
- Confirm breakout_force(-4.2, 6.4) returns breakout 5.3 lbf, and that
  centering_check(0.42, 0.50) returns margin 0.08 deg, centered.
- Confirm ValueError rejection: fewer than 2 calibration points, fewer
  than 3 points for the gradient and per-g fits, length mismatches,
  negative counts, non-positive speeds, pull not greater than push,
  negative residual, non-positive limit.
- Run the contract test offline: python3
  scripts/test_control_force_flight_test.py (35 tests, deterministic).

## Related leaves

- flight-test-operations/stability/static-stability-flight-test: the
  position-side sibling; this leaf is the measured force complement.
- flight-test-operations/stability/lateral-directional-stability-
  flight-test: the lateral axis sibling.
- flight-mechanics/stability-control/control-surface-effectiveness:
  the analytic design prediction boundary.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_control_force_flight_test.py

The test covers the calibration worked values to 1e-6 with the applied
load regression identity to 1e-9 and zero residual on a third
collinear point, the gradient worked slope and r2 with the reversed
unstable verdict, the force per g worked slope and r2, the breakout
half-width including the symmetric case, the centering margin with the
exceeds-limit case, the combined report keys and prediction at 2100
counts, run-to-run determinism, and ValueError rejection of every
non-physical input in the validation list.

## Compliance

- Standards referenced, not reproduced: FAR-25 (14 CFR Part 25) frames
  the certification context for the transport-class control force
  flight test; the reduction relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
