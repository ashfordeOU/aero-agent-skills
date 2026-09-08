---
name: rotorcraft-forward-flight-flapping
description: "Use when you must compute the steady first-harmonic (1/rev) flapping equilibrium of a helicopter main rotor blade in forward flight under uniform inflow: the longitudinal flapping angle a1s (the tip-path-plane aft tilt, negative few degrees at cruise) and the lateral flapping angle b1s of the idealized centrally hinged untwisted blade from the advance ratio, the inflow ratio, the collective pitch and the blade Lock number gamma, with the forward-flight coning angle a0 that reduces to the hover coning value at zero advance ratio. Produces the longitudinal and lateral flapping angles and the coning angle in radians and degrees and the first-harmonic flap summary that gates rotorcraft trim assessments and tip-path-plane checks. Trigger: rotorcraft forward flight flapping, tip path plane tilt, first harmonic flap response, longitudinal flapping angle, lateral flapping angle, advance ratio flapping, flap equilibrium tilt."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [forward-flight-flapping, tip-path-plane-tilt, first-harmonic-flap-response, longitudinal-flapping-angle, lateral-flapping-angle, advance-ratio-flapping, flap-equilibrium-tilt]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Forward-Flight Flapping (flight-mechanics/performance/rotorcraft-forward-flight-flapping)

Use when the task is the steady first-harmonic flapping equilibrium of a
helicopter main rotor blade in forward flight: the tip-path-plane tilt
that the idealized centrally hinged, untwisted blade settles into under
uniform inflow at a given advance ratio. This leaf implements the
classical harmonic balance of the flap equation (Johnson, Helicopter
Theory ch. 4 and Leishman, Principles of Helicopter Aerodynamics ch. 4,
paraphrased, never reproduced) in pure Python, stdlib only,
deterministic. It is the forward-flight extension of
flight-mechanics/performance/rotorcraft-blade-flapping-dynamics, which
owns only the hover-state Lock number, hover coning angle and flap
frequency ratio; the forward-flight flap equilibrium, tip-path-plane
tilt and first-harmonic content live here.

## Domain quick reference

- Blade element velocities in the hub plane frame: u_T = x + mu*sin(psi)
  (tangential, x = r/R) and u_P = lambda + x*beta' + mu*beta*cos(psi)
  (perpendicular), with psi measured from the downwind blade position,
  advancing side at psi = pi/2.
- First-harmonic flap ansatz: beta(psi) = a0 + a1s*cos(psi) +
  b1s*sin(psi), with a0 the coning angle, a1s the longitudinal (cos)
  component and b1s the lateral (sin) component.
- Flap equation with nu = 1 (central hinge): beta'' + beta =
  (gamma/2)*M(psi). The steady part fixes a0 (centrifugal balance); the
  1/rev part vanishes identically at resonance, so equilibrium nulls the
  cos and sin projections of the aerodynamic flap moment M(psi).
- Closed forms (exact solution of the 3 by 3 harmonic-balance system):
  a0 = (gamma/2)*(theta0*(1 + mu^2)/4 - lambda/3),
  a1s = -4*mu*(2*theta0/3 - lambda/2)/(1 - mu^2/2),
  b1s = -(4*mu/3)*a0/(1 + mu^2/2).
- a1s is gamma-free: the aerodynamic forcing and damping both scale with
  the Lock number and cancel in the 1/rev cos balance. b1s carries gamma
  through the coning coupling to a0.
- Hover limit: mu = 0 gives a0 equal to the hover leaf closed form
  0.5*gamma*(theta0/4 - lambda/3), and a1s = b1s = 0 exactly.
- Sign convention: a1s < 0 means the tip-path plane tilts aft (the
  flapping-back direction of forward flight); b1s < 0 means the
  advancing blade (psi = pi/2) tip sits below the coning plane.
- Scope: 0 <= mu < 1 (singular at mu = 1, reverse flow out of scope),
  lambda > 0 (downward-positive convention), theta0 > 0, centrally
  hinged, first harmonic only, small angles.
- Units are radians for the angle inputs and the _rad outputs; the
  _deg outputs are the _rad values times 180/pi.
- FAR-29 frames the transport-category rotorcraft certification
  context for rotor loads; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Fix the operating point: advance ratio mu, uniform inflow ratio
   lambda, collective pitch theta0 and blade Lock number gamma (the
   same gamma the hover sibling computes from blade geometry).
2. Compute the forward-flight coning angle with forward_coning_angle
   and compare it against the hover coning value at the same theta0 and
   lambda (the theta0*mu^2/4 dynamic-pressure gain).
3. Compute the longitudinal flapping angle with
   longitudinal_flapping_angle and read the tip-path-plane aft tilt (no
   gamma argument: it cancels in the 1/rev balance).
4. Compute the lateral flapping angle with lateral_flapping_angle and
   confirm the coning-coupling identity against forward_coning_angle.
5. Run forward_flap_summary for the one-call dict with all six
   documented keys in radians and degrees.
6. Check the inflow sensitivity of the tip-path-plane tilt: raising
   lambda relaxes the aft tilt, lowering it steepens the aft tilt, and
   the two-point differences are exact closed-form linear slopes.
7. Confirm the flapping angles grow in magnitude with advance ratio mu
   over the operating range and stay inside the published few-degree
   band.
8. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_forward_flight_flapping.py.

## Worked example

Cruise case: advance ratio mu = 0.3, uniform inflow ratio lambda = 0.06,
collective theta0 = 0.14 rad, Lock number gamma = 6.0 (a light-to-medium
blade in the hover sibling's gamma 5-8 and lambda 0.05-0.08 band). Real
module outputs:

- forward_coning_angle(0.3, 0.06, 0.14, 6.0) = 0.05445 rad = 3.11976
  deg, 21 percent above the hover value 0.045 rad at the same theta0
  and lambda.
- longitudinal_flapping_angle(0.3, 0.06, 0.14) = -0.07958 rad = -4.5597
  deg: the tip-path plane tilts aft by about 4.56 deg. The magnitude
  grows with mu: 1.459 deg at mu = 0.1, 2.962 deg at mu = 0.2, 4.560 deg
  at mu = 0.3, 5.412 deg at mu = 0.35.
- lateral_flapping_angle(0.3, 0.06, 0.14, 6.0) = -0.02084 rad = -1.1942
  deg: the advancing side sits about 1.19 deg below the coning plane,
  also growing with mu.
- Inflow sensitivity at the worked point: raising lambda to 0.08
  relaxes the aft tilt to a1s = -3.8397 deg; lowering it to 0.05
  steepens the aft tilt to -4.9196 deg.
- Hover-limit anchor at the same theta0, lambda, gamma: mu = 0.0 gives
  a0 = 0.045 rad, a1s = 0.0 and b1s = 0.0 exactly.
- forward_flap_summary(0.3, 0.06, 0.14, 6.0) returns the six-key dict:
  coning_angle_rad 0.05445, coning_angle_deg 3.11976,
  longitudinal_flapping_rad -0.07958, longitudinal_flapping_deg
  -4.5597, lateral_flapping_rad -0.02084, lateral_flapping_deg -1.1942.

## Verification

- Confirm forward_coning_angle(0.3, 0.06, 0.14, 6.0) matches the worked
  value and that mu = 0.0 reproduces the hover sibling closed form
  0.5*gamma*(theta0/4 - lambda/3).
- Confirm longitudinal_flapping_angle(0.3, 0.06, 0.14) matches the
  worked value, is exactly 0.0 at mu = 0.0, and is exactly 0.0 at the
  collective-inflow balance theta0 = 3*lambda/4.
- Confirm lateral_flapping_angle satisfies the coning-coupling identity
  -(4*mu/3)*forward_coning_angle/(1 + mu^2/2) at the worked point and at
  a second point.
- Confirm the two-point inflow differences match the exact closed-form
  slopes 2*mu/(1 - mu^2/2), -gamma/6 and (2*mu*gamma/9)/(1 + mu^2/2).
- Confirm |a1s| and |b1s| strictly increase over mu = 0.1, 0.2, 0.3,
  0.35 at fixed lambda and theta0.
- Confirm forward_flap_summary returns exactly the six documented keys
  and each matches the corresponding component function.
- Confirm ValueError rejection of mu < 0, mu >= 1, lambda <= 0,
  theta0 <= 0, gamma <= 0 and any non-finite argument (mu = 0.0 is a
  valid hover-limit input).
- Run the contract test offline: python3
  scripts/test_rotorcraft_forward_flight_flapping.py (34 tests,
  deterministic, no network).

## Pitfalls

- Passing gamma to longitudinal_flapping_angle: the function takes no
  Lock number argument by design, because gamma cancels exactly in the
  1/rev cos balance; only mu, lam and theta0 are needed.
- Reading a1s sign as an error: a1s < 0 is the pinned convention for
  the aft tip-path-plane tilt of forward flight, not a bug; it grows
  more negative as mu increases.
- Using this leaf for hover: at mu = 0 the leaf reduces exactly to the
  hover sibling's coning closed form, but the hover Lock number, hover
  coning angle and flap frequency ratio quantities themselves belong to
  rotorcraft-blade-flapping-dynamics.
- Extrapolating past mu = 1: the model is singular at mu = 1
  (denominator 1 - mu^2/2 stays finite there, but the underlying
  uniform-inflow idealization and reverse-flow omission break down long
  before mu = 1); ValueError rejects mu >= 1.0.
- Treating the first-harmonic truncation as exact: the model omits
  2/rev and higher flapping harmonics, whose residual is documented in
  the spec at order 1e-2 rad at the worked point and does not enter the
  tip-path-plane tilt reported here.

## Related leaves

- flight-mechanics/performance/rotorcraft-blade-flapping-dynamics: the
  hover-state sibling that owns the Lock number, the hover coning angle
  and the flap frequency ratio; this leaf's hover limit reproduces its
  coning closed form.
- flight-mechanics/performance/rotorcraft-forward-flight-performance:
  the power and best-speeds leaf of forward flight (Glauert inflow,
  induced, parasite and profile power); it never touches blade motion.
- flight-mechanics/performance/rotorcraft-lead-lag-dynamics: the
  in-plane blade motion sibling, lag frequency ratio and ground
  resonance clearance, distinct from out-of-plane flapping.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_forward_flight_flapping.py

The test covers the worked-example values of the coning, longitudinal
and lateral flapping angles in radians and degrees, the hover
cross-leaf coning identity, the collective-inflow balance zero, the
coning-coupling identity, the exact two-point inflow linearity of the
tilt slopes, the monotone growth of the flapping magnitudes with
advance ratio, the one-call summary dict contract, ValueError rejection
of every non-physical or non-finite input, and run-to-run determinism.

## Compliance

- Standards referenced, not reproduced: FAR-29 is the FAA
  transport-category rotorcraft airworthiness standard (ecfr.gov); the
  flap-equilibrium relations above are standard engineering methodology
  (Johnson, Leishman), summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
