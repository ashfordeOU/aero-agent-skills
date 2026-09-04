---
name: rotorcraft-blade-flapping-dynamics
description: "Use when you must compute the blade-flapping dynamics of a helicopter main rotor: the blade Lock number from the air density, the section lift-curve slope, the blade chord, the rotor radius and the blade flap moment of inertia, the steady hover coning angle from the Lock number, the collective pitch and the uniform inflow ratio, and the rotating flap natural frequency ratio for a flap hinge offset. Produces the Lock number, the coning angle in radians and degrees and the flap frequency ratio per revolution that gate a rotor-dynamics assessment. Trigger: rotorcraft blade flapping, Lock number, coning angle, flap frequency ratio, rotor dynamics, hinge offset, helicopter main rotor, articulated blade."
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
  tags: [rotorcraft-blade-flapping-dynamics, rotor-blade-flapping, coning-angle, lock-number, flap-frequency-ratio, rotor-dynamics, hinge-offset]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Blade Flapping Dynamics (flight-mechanics/performance/rotorcraft-blade-flapping-dynamics)

Use when the task is the basic blade-flapping dynamics of a helicopter
main rotor: the Lock number that fixes the ratio of aerodynamic flap
moment to centrifugal restoring moment, the steady hover coning angle
of an untwisted centrally hinged blade under uniform inflow, and the
rotating flap natural frequency ratio for a flap hinge offset. This
leaf implements the classical articulated-rotor flap model (Johnson,
Helicopter Theory ch.4 and Leishman, Principles of Helicopter
Aerodynamics ch.4, paraphrased, never reproduced) in pure Python,
stdlib only, deterministic. It is the first blade-dynamics leaf in the
rotorcraft subdomain: the momentum-theory POWER leaves
(rotorcraft-hover-performance and siblings) own hover power, induced
velocity and figure of merit, while this leaf owns flap motion only.
Flap dynamics here covers coning and frequency ratio, not ground
resonance or lag dynamics.

## Domain quick reference

- Lock number: gamma = rho * a * c * R^4 / I_beta, where rho is the
  air density, a the section lift-curve slope (typical 5.73 /rad), c
  the blade chord, R the rotor radius and I_beta the blade flap moment
  of inertia. The Lock number is the ratio of the aerodynamic flap
  moment to the centrifugal restoring moment; published rotor values
  fall in the 5-12 band.
- Uniform-blade flap inertia: I_beta = m_b * R^2 / 3 for a blade of
  mass m_b flapping about the rotation axis.
- Hover coning angle: a0 = 0.5 * gamma * (theta0 / 4 - lambda / 3)
  rad, from the steady flap-moment balance. The aerodynamic flap
  moment 0.5 * rho * a * c * Omega^2 * R^4 * (theta0/4 - lambda/3)
  equals the centrifugal restoring moment I_beta * Omega^2 * a0 for an
  untwisted centrally hinged blade with uniform inflow, where theta0
  is the collective pitch and lambda the uniform inflow ratio. Hover
  coning is typically 3-8 deg.
- Rotating flap frequency ratio: nu = sqrt(1 + 1.5 * e / (1 - e)),
  with e the flap hinge offset as a fraction of rotor radius. This is
  algebraically identical to nu^2 = (1 - 3e/2 + e^3/2) / (1 - e)^3 for
  a uniform blade. The central hinge limit e = 0 gives exactly 1.0
  (1/rev); articulated flap frequencies run about 1.02-1.08 per rev.
- Flap frequency per revolution: because the flapping natural
  frequency scales with rotor speed, the ratio nu already expresses
  the frequency in units of rotor revolutions and no rotor speed input
  is required.
- Units are SI throughout: kg, m, rad, /rad, dimensionless ratios.
- FAR-29 frames the transport-category rotorcraft certification
  context for rotor loads; the relations above are standard
  engineering methodology, summary-only.

## Workflow

1. Fix the blade geometry and operating point: blade mass m_b, radius
   R, chord c, collective theta0, uniform inflow ratio lambda, hinge
   offset fraction e, and optionally rho and the lift-curve slope a.
2. Get the flap inertia with blade_flap_inertia_uniform (uniform blade
   about the rotation axis); the module order is mass, radius, chord,
   theta0, lambda, e, then the optional lift_slope and rho defaults.
3. Compute the Lock number with lock_number from rho, a, c, R and
   I_beta, and sanity check it against the published 5-12 band.
4. Compute the hover coning with hover_coning_angle(gamma, theta0,
   lambda); a0 near zero means collective and inflow nearly balance.
5. Compute the flap frequency with flap_frequency_ratio(e); e = 0 is
   the central hinge 1/rev limit, larger offsets stiffen the blade.
6. Run blade_flapping_summary for the one-call assessment dict with
   all six documented keys (lock_number, flap_inertia_kg_m2,
   coning_angle_rad, coning_angle_deg, flap_frequency_ratio,
   flap_frequency_per_rev).
7. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_blade_flapping_dynamics.py.

## Worked example

A typical light-to-medium helicopter blade: rho = 1.225 kg/m3, a =
5.73 /rad, chord c = 0.50 m, radius R = 6.0 m, blade mass m_b = 50 kg
(I_beta = 600 kg m2), collective theta0 = 0.170 rad, uniform inflow
ratio lambda = 0.050, hinge offset e = 0.05. Real module outputs:

- blade_flap_inertia_uniform(50, 6.0) = 600.0 kg m2 exactly
  (50 * 36 / 3).
- lock_number(1.225, 5.73, 0.5, 6.0, 600.0) = 7.58079, inside the
  published 6-10 rotor band (hand check 1.225 * 5.73 * 0.5 * 1296 /
  600 = 7.58079).
- hover_coning_angle(7.58079, 0.170, 0.050) = 0.09792 rad =
  5.61032 deg, inside the published 3-8 deg hover coning band.
- flap_frequency_ratio(0.05) = 1.03872, inside the published
  1.02-1.08 per rev articulated flap band.
- blade_flapping_summary(50, 6.0, 0.50, 0.170, 0.050, 0.05) returns
  lock_number 7.58079, flap_inertia_kg_m2 600.0, coning_angle_rad
  0.09792, coning_angle_deg 5.61032, flap_frequency_ratio 1.03872 and
  flap_frequency_per_rev 1.03872.

## Verification

- Confirm blade_flap_inertia_uniform(50, 6.0) returns 600.0 exactly.
- Confirm lock_number(1.225, 5.73, 0.5, 6.0, 600.0) returns 7.58079
  and falls in the 6-10 band.
- Confirm hover_coning_angle(7.58079, 0.170, 0.050) returns about
  0.09792 rad and 5.61 deg, inside 3-8 deg.
- Confirm the coning limiting behaviour: theta0/4 equal to lambda/3
  gives a0 = 0.0, higher collective raises a0, higher inflow lowers it.
- Confirm flap_frequency_ratio(0.0) equals exactly 1.0, e = 0.05 gives
  about 1.0387, and e = 0.5 gives sqrt(2.5) = 1.5811; larger offsets
  always raise nu.
- Confirm the summary dict contains exactly the six documented keys and
  that flap_frequency_per_rev equals flap_frequency_ratio.
- Confirm ValueError rejection of non-positive mass, radius, chord,
  lift slope, density, inertia and gamma, of negative collective or
  inflow ratio, and of hinge offset below 0 or at or above 1.
- Run the contract test offline: python3
  scripts/test_rotorcraft_blade_flapping_dynamics.py (34 tests,
  deterministic, no network).

## Pitfalls

- Using a non-uniform flap inertia without saying so:
  blade_flap_inertia_uniform assumes I_beta = m_b*R^2/3 about the rotation
  axis; the Lock number (and coning) is only as good as the inertia input.
- Sanity-checking the Lock number against the wrong band: published rotor
  values run 5-12 (the worked example lands at 7.58); treat the band as a
  plausibility check, not a pass/fail gate.
- Expecting coning sign intuition to hold: a0 = 0.5*gamma*(theta0/4 -
  lambda/3), so higher inflow lowers coning and theta0/4 = lambda/3 gives
  exactly zero; a 'negative coning' reading means collective and inflow are
  out of balance, not a sign error in the formula.
- Passing hinge offset e at or above 1 (or negative): flap_frequency_ratio
  raises ValueError there; e = 0 is the exact central-hinge 1/rev limit and
  larger offsets stiffen the blade.
- Forgetting the units convention: SI throughout (kg, m, rad) with gamma
  dimensionless; a negative collective or inflow ratio raises ValueError,
  and coning_angle_deg is the only degree output.

## Related leaves

- flight-mechanics/performance/rotorcraft-hover-performance: the
  momentum-theory hover power leaf; its blade geometry inputs (radius,
  chord, solidity) are shared with this leaf.
- flight-mechanics/performance/rotorcraft-tail-rotor-sizing: tail
  rotor anti-torque sizing, the power-side complement to main rotor
  dynamics.
- flight-mechanics/stability-control/spin-recovery: fixed-wing
  autorotation of a stalled wing is a different topic from rotor blade
  flapping and lives in the fixed-wing stability leaves.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_blade_flapping_dynamics.py

The test covers the worked example magnitude bounds (Lock number 6-10
about 7.58, coning about 0.0979 rad = 5.61 deg inside 3-8 deg, flap
frequency ratio about 1.0387 inside 1.02-1.08 per rev), the exact
uniform-blade inertia value, the flap-moment balance zero, monotonic
coning responses, the closed-form flap frequency identities including
the exact central hinge limit, scaling relations, ValueError rejection
of every non-physical input, and run-to-run determinism.

## Compliance

- Standards referenced, not reproduced: FAR-29 is the FAA
  transport-category rotorcraft airworthiness standard (ecfr.gov); the
  flap relations above are standard engineering methodology
  (Johnson, Leishman), summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
