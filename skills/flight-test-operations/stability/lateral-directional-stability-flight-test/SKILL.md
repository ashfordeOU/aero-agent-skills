---
name: lateral-directional-stability-flight-test
description: "Use when you must plan and reduce the static lateral-directional stability flight test from steady-heading sideslip data: build the rudder-fixed and rudder-free sideslip sweep matrix at constant airspeed, fit the rudder and aileron deflection gradients versus sideslip angle, estimate the directional stability from the fitted rudder gradient with a declared rudder control power and the lateral dihedral stability from the fitted aileron gradient with a declared aileron control power, record the pedal-force gradient, and issue the weathercock and dihedral stability verdicts for the stability demonstration. Produces the sweep matrix, the fitted gradients, the signed directional and lateral stability estimates, the pedal-force gradient and the verdicts that gate the demonstration. Trigger: steady-heading sideslip, sideslip sweep, rudder gradient, aileron gradient, rudder-fixed stability, rudder-free stability, weathercock stability, dihedral effect, pedal-force gradient."
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
  tags: [lateral-directional-stability-flight-test, steady-sideslip-sweep, rudder-fixed-stability, rudder-free-stability, weathercock-stability, dihedral-effect, pedal-force-gradient]
  version: 0.1.0
  author: AeroSkills
---

# Lateral-Directional Stability Flight Test (flight-test-operations/stability/lateral-directional-stability-flight-test)

Use when the task is planning and reducing the static lateral-directional
stability flight test of a fixed-wing aircraft from steady-heading
sideslip (SHS) data: the sideslip sweep matrix, the fitted rudder,
aileron and pedal-force gradients, and the signed directional and lateral
stability estimates that gate the demonstration. This leaf implements the
reduction in pure Python, stdlib only. It pairs with the pitch-axis
static stability flight test sibling (trim and margin demonstration) and
the dynamic mode damping sibling for the rest of the stability picture.

## Domain quick reference

- Sign convention (documented for every reduction): beta is the sideslip
  angle in degrees, positive when the nose is LEFT of the velocity vector
  (left slip); delta_r positive = right pedal; delta_a positive = right
  aileron (left roll). Measured in steady-heading sideslip maneuvers at
  constant CAS and altitude, the pilot holding heading with aileron and
  setting the slip with rudder.
- Rudder gradient: s_r = d(delta_r)/d(beta) in deg/deg (unitless). For a
  directionally stable aircraft the pilot pushes the rudder INTO the slip
  to increase it, so s_r is positive with the conventional control sign.
- Aileron gradient: s_a = d(delta_a)/d(beta) in deg/deg. For a laterally
  stable aircraft (dihedral effect) the pilot holds the left slip with
  aileron against the roll, so s_a is negative.
- Pedal-force gradient: g_p = d(F_pedal)/d(beta) in N/deg, from the
  rudder-free run (the force the pilot must apply at each beta).
- Signed estimates from the trim balances:
  Cn_beta_est = -cn_dr * s_r and Cl_beta_est = -cl_da * s_a, both in
  /rad. The deg/deg gradient ratios enter as unitless slopes because the
  deg/deg and rad/rad ratios are numerically identical. cn_dr < 0 and
  cl_da < 0 are the conventional signed control powers (right pedal yaws
  the nose right, right aileron rolls left). A stable aircraft yields
  Cn_beta_est > 0 (weathercock stable) and Cl_beta_est < 0 (dihedral
  stable).
- Least squares: fit_slope fits offset plus slope (dy/dx) through the
  sweep points; from two points up, more points tighten the fit, and any
  vertical point set (zero x variance) is rejected.
- Test limit: build_sideslip_matrix holds every commanded beta target
  inside the declared +-15 deg limit (SIDESLIP_LIMIT_DEG) at the constant
  CAS. A sweep needs at least 2 points (BETA_SWEEP_MIN) up to a 40 point
  planning cap (BETA_SWEEP_MAX).
- FAR 25.177 frames the static lateral-directional stability
  demonstration criteria; only paraphrased criteria appear here
  (weathercock stable when the directional estimate is positive, lateral
  stable when the dihedral estimate is negative). Regulation text is
  never reproduced.

## Workflow

1. Plan the sweep: build_sideslip_matrix over the commanded beta targets
   at the constant CAS and altitude, with rudder-fixed and rudder-free
   runs inside the declared +-15 deg limit.
2. Fit the control gradients from the rudder-fixed run:
   rudder_gradient(beta_deg, delta_r_deg) and
   aileron_gradient(beta_deg, delta_a_deg).
3. Fit the rudder-free case: pedal_force_gradient(beta_deg,
   pedal_force_N).
4. Declare the control-power inputs cn_dr_per_rad and cl_da_per_rad
   (predicted by the flight-mechanics analysis leaf or wind tunnel; they
   are inputs here, never claimed as measured).
5. Form the signed estimates: signed_directional_estimate(cn_dr_per_rad,
   s_r) and signed_lateral_estimate(cl_da_per_rad, s_a).
6. Judge the demonstration: weathercock_verdict on the directional
   estimate and dihedral_verdict on the lateral estimate.
7. For a full sweep, call reduce_sideslip_sweep once with the optional
   pedal-force and control-power arguments; the convenience dict returns
   every gradient, estimate, verdict and the point count, with None
   fields for any optional input not supplied.
8. Confirm the deterministic checks with the contract test.

## Worked example

Stable transport configuration at constant CAS 80 m/s and altitude
3000 m. Measured sweep beta (deg) = [2, 5, 8, 11, 14]; rudder deflection
(deg) = [+0.24, +0.58, +0.96, +1.34, +1.70]; aileron deflection (deg) =
[-0.35, -0.80, -1.30, -1.80, -2.30]; rudder-free pedal force (N) =
[0, -95, -185, -275, -360]. Declared control powers cn_dr = -0.90 /rad
and cl_da = -0.35 /rad. Real module outputs:

- Rudder gradient s_r = +0.1227 deg/deg (spec magnitude 0.10-0.15): the
  pilot pushes the right pedal into the left slip, positive slope.
- Aileron gradient s_a = -0.1633 deg/deg (spec magnitude -0.20 to
  -0.12): aileron holds the slip against the dihedral roll, negative
  slope.
- Pedal-force gradient g_p = -30.0 N/deg (spec magnitude -40 to -20).
- Directional estimate Cn_beta_est = -(-0.90) * (+0.1227) = +0.110 /rad
  (spec 0.08-0.15), weathercock verdict "stable".
- Lateral estimate Cl_beta_est = -(-0.35) * (-0.1633) = -0.057 /rad
  (spec -0.10 to -0.03), dihedral verdict "stable".
- build_sideslip_matrix([0, 5, 10], 80, 3000) returns 3 rows with
  beta_target_deg [0, 5, 10] and cas_ms 80; a beta target of 20 deg
  raises ValueError (outside the declared +-15 deg limit).

## Verification

- Confirm the worked sweep gradients: rudder +0.1227 (positive), aileron
  -0.1633 (negative), pedal -30.0 N/deg, exact least squares through the
  five points.
- Confirm the signed estimates +0.110 /rad and -0.057 /rad and the
  "stable" weathercock and dihedral verdicts.
- Sign logic: a negative rudder slope (reverse control or directionally
  unstable aircraft) returns "unstable" for weathercock_verdict; a
  positive aileron slope returns "unstable" for dihedral_verdict; an
  estimate of exactly 0.0 returns "unstable" at the threshold edge.
- Confirm ValueError rejection of non-physical inputs: mismatched or
  too-short series, zero x variance, cn_dr = 0, cl_da = 0, beta targets
  beyond +-15 deg, and non-positive CAS.
- Determinism: no RNG anywhere; run-to-run floats are identical.
- Run the offline contract test: python3
  scripts/test_lateral_directional_stability_flight_test.py.

## Related leaves

- flight-test-operations/stability/static-stability-flight-test: the
  pitch-axis static stability demonstration alongside this one.
- flight-test-operations/stability/dynamic-stability-flight-test: the
  mode damping complement to the static lateral-directional picture.
- flight-mechanics/stability-control/lateral-directional-stability: the
  prediction sibling that supplies the control-power parameters this leaf
  takes as declared inputs.
- flight-test-operations/planning/test-point-matrix-design: sweep matrix
  planning for the test campaign.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_lateral_directional_stability_flight_test.py

The test covers the worked example end to end (gradients and estimates
within the spec magnitude bounds and exact to 6 places), the least
squares core and its ValueError rejections, the sign logic and verdict
threshold edges, the sideslip matrix row contract and declared limit
enforcement, the convenience dict keys and None fields for optional
inputs, and run-to-run determinism.

## Compliance

- FAR 25.177 is cited reference-only per standards-map.yaml; the static
  lateral-directional stability criteria above are paraphrased
  summary-only, never reproduced from the regulation.
- compliance: STANDARDS-REF, gated: false.
