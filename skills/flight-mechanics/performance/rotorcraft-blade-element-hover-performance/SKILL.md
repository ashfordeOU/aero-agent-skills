---
name: rotorcraft-blade-element-hover-performance
description: "Use when you must determine the blade-element hover performance of a helicopter main rotor: the thrust coefficient from the collective pitch schedule, rotor solidity, lift-curve slope and Betz tip loss factor, the inflow ratio from the uniform-inflow hover closure, the collective pitch required to hover at a target thrust coefficient, the torque coefficient with its induced and profile split, and the rotor shaft torque, shaft power and hover figure of merit from the coefficients. Produces a hover blade-element summary and a collective pitch polar across the pitch range of the same rotor. Trigger: blade element theory, thrust coefficient, torque coefficient, collective pitch, tip loss factor, hover figure of merit."
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
  tags: [rotorcraft-blade-element-hover-performance, blade-element-theory, thrust-coefficient, torque-coefficient, collective-pitch, tip-loss-factor, hover-figure-of-merit]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Blade-Element Hover Performance (flight-mechanics/performance/rotorcraft-blade-element-hover-performance)

Use when you must determine the blade-element hover performance of a
helicopter main rotor: the rotor thrust coefficient C_T and inflow
ratio from the pitch schedule, the collective pitch required to hover,
and the torque coefficient (induced plus profile split), rotor shaft
torque and figure of merit that follow from the coefficients. This is
the pitch-to-coefficients chain, theta0 to C_T/C_Q to torque/FM, the
blade-element member of the rotorcraft vertical-flight group: the
sibling flight-mechanics/performance/rotorcraft-hover-performance leaf
takes thrust as input and is momentum-only (no C_T, C_Q, theta0,
lift-curve slope, twist or tip-loss factor in its logic), while this
leaf integrates the blade loading over the pitch schedule with the Betz
tip loss factor B. Modeled in pure Python, stdlib only, deterministic.
The blade-element and momentum models agree exactly at B = 1: shaft
power from the torque coefficient equals P_ideal + P_profile of the
momentum model and the figure of merit from coefficients equals the
momentum power ratio, which the contract test verifies against the
sibling module.

## Domain quick reference

All quantities are SI. Rotor radius R, disk area A = PI * R^2, tip
speed Vtip = Omega * R, solidity sigma, mean blade drag coefficient
Cd0, lift-curve slope a (1/rad), thrust T. The hover thrust equals the
rotorcraft weight: T = m * G, G = 9.80665 m/s^2.

- Blade-element thrust coefficient: C_T = (sigma * a / 2) * (theta0 *
  B^3 / 3 - lambda * B^2 / 2), with theta0 the collective pitch (rad)
  and B the Betz tip loss factor in (0, 1]. The B^3/3 term integrates
  the pitch loading over the blade; the B^2/2 term removes the inflow
  incidence.
- Thrust coefficient from thrust: C_T = T / (rho * A * Vtip^2), the
  standard definition used to close the hover state.
- Inflow closure (uniform inflow in hover): lambda = v_i / Vtip =
  sqrt(C_T / 2). The hover momentum balance C_T = 2 * lambda^2 closes
  the inflow ratio directly from the thrust coefficient.
- Collective for a target C_T: theta0 = (3 / B^3) * (2 * C_T / (sigma *
  a) + lambda * B^2 / 2) with lambda = sqrt(C_T / 2). Tip loss below 1
  raises the required collective at fixed thrust coefficient (about 6%
  at B = 0.97 on the worked rotor).
- Torque coefficient: C_Q = lambda * C_T + sigma * Cd0 / 8, the induced
  contribution lambda * C_T carrying the inflow work and the profile
  contribution sigma * Cd0 / 8 the section drag.
- Rotor shaft torque: Q = C_Q * rho * A * Vtip^2 * R in N m.
- Rotor shaft power: P = Q * Omega = C_Q * rho * A * Vtip^3 in W. At
  B = 1 with the closure lambda this equals the momentum hover total
  P_ideal + P_profile of the sibling leaf, and each term matches its
  momentum counterpart separately.
- Figure of merit from coefficients: FM = C_T^1.5 / (sqrt(2) * C_Q),
  the same ratio the momentum leaf forms from powers.
- Defaults: rho = 1.225 kg/m^3 at sea level, lift-curve slope
  a = 5.73 1/rad. Modelled twist is zero (untwisted, constant-chord
  blade integral); the assumption is recorded here because the spec
  formula integrates theta0 as constant along the blade.
- FAR 29 frames the rotorcraft certification context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: rotor radius R, rotorcraft mass m (hover
   thrust T = m * G), density rho, solidity sigma, mean blade drag
   coefficient Cd0, tip speed Vtip, lift-curve slope a and Betz tip
   loss factor B.
2. Get the thrust coefficient from the thrust with the standard
   definition C_T = T / (rho * A * Vtip^2), or start from a target
   C_T directly.
3. Close the inflow with inflow_ratio_from_ct(c_t), giving
   lambda = sqrt(C_T / 2).
4. Recover the required collective with
   collective_for_thrust_coefficient(c_t, solidity, lift_slope,
   tip_loss) and convert to degrees; compare against the published
   5-10 deg hover collective band.
5. Split the torque coefficient with torque_coefficient(c_t, lambda,
   solidity, drag_coefficient) and confirm the induced term
   lambda * C_T plus the profile term sigma * Cd0 / 8 gives the total.
6. Get the rotor shaft torque with rotor_torque(c_q, rho, area,
   tip_speed, radius) and the shaft power with
   rotor_power_from_torque; both consume the same arguments.
7. Compute the figure of merit with
   figure_of_merit_from_coefficients(c_t, c_q) and check it against
   the momentum power ratio for the same rotor.
8. For a single-call verdict on one hover state run
   hover_blade_element_summary(thrust_N, radius_m, rho, solidity,
   lift_slope, drag_coefficient, tip_speed, tip_loss, collective_rad),
   which returns the full dict and verifies the supplied collective
   reproduces the thrust-derived C_T (mismatched inputs raise
   ValueError). For a sweep run collective_pitch_polar(collectives_rad,
   ...), which closes lambda by fixed-point iteration for every entry.
9. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_blade_element_hover_performance.py.

## Worked example

The reference rotor (identical to the momentum hover-leaf example):
R = 5.0 m, m = 2200 kg, rho = 1.225 kg/m^3, sigma = 0.08, Cd0 = 0.012,
Vtip = 220 m/s, a = 5.73 1/rad. Real module outputs:

- Thrust: 2200 * 9.80665 = 21574.63 N; disk area PI * 5.0^2 = 78.54
  m^2.
- Thrust coefficient: C_T = 0.0046331 (spec bound about 0.00463).
- Inflow ratio: inflow_ratio_from_ct gives lambda = 0.048131, the hand
  value sqrt(C_T / 2).
- Collective at B = 1: theta0 = 0.132839 rad = 7.61 deg (spec about
  0.1328 rad, 7.6 deg; within the 5-10 deg band).
- Collective at B = 0.97: theta0 = 0.140874 rad = 8.07 deg (spec about
  0.1409 rad, 8.1 deg), 6.05% higher than at B = 1.
- Torque coefficient split: induced lambda * C_T = 2.2299e-4, profile
  sigma * Cd0 / 8 = 1.2000e-4 exactly, total C_Q = 3.4299e-4 (spec
  about 3.43e-4).
- Rotor torque: Q = 7985.97 N m (spec about 7986 N m).
- Rotor shaft power: P = 351382.76 W, equal to the momentum hover
  P_ideal + P_profile = 228447.84 + 122934.92 W to 1.7e-16 relative.
- Figure of merit: FM = 0.650140 (spec about 0.650), equal to the
  momentum FM ratio 228447.84 / 351382.76 = 0.650140.
- Round trip: feeding the recovered theta0 back through
  thrust_coefficient returns C_T to 1e-9 relative at both B = 1 and
  B = 0.97.

## Verification

- Confirm hover_blade_element_summary on the reference rotor returns
  thrust_coefficient 0.0046331, inflow_ratio 0.048131,
  torque_coefficient_total 3.4299e-4, rotor_torque_Nm 7985.97,
  rotor_power_W 351382.76 and figure_of_merit 0.650140, with the
  induced plus profile split summing to the total to 1e-12.
- Confirm collective_for_thrust_coefficient returns 0.132839 rad at
  B = 1 and 0.140874 rad at B = 0.97, and that both round-trip
  through thrust_coefficient to the target C_T within 1e-9.
- Confirm the cross-leaf identity at B = 1: power from the torque
  coefficient equals the momentum P_ideal + P_profile within 1e-6
  relative and the coefficient FM equals the momentum power ratio
  within 1e-9 (both verified against the sibling module by the
  contract test).
- Confirm tip-loss monotonicity: B = 0.97 requires a higher collective
  than B = 1.0, and higher B gives a higher C_T at fixed collective.
- Confirm the ideal-limit check FM <= 1: at the ideal C_Q =
  C_T^1.5 / sqrt(2) the figure of merit is exactly 1, and the worked
  FM sits inside (0, 1).
- Confirm every non-positive solidity, lift slope, drag coefficient,
  tip speed, radius, rho, thrust, and every tip loss outside (0, 1],
  negative collective, negative c_t and non-positive c_q raises
  ValueError, and that a collective which does not reproduce the
  thrust-derived C_T is rejected by the summary.
- Confirm determinism: repeated runs return identical floats (no RNG,
  stdlib only).
- Run the contract test offline: python3
  scripts/test_rotorcraft_blade_element_hover_performance.py (34
  tests, deterministic).

## Pitfalls

- Letting the Betz factor out of (0, 1]: B = 1 is the no-tip-loss limit
  where the blade-element power equals the momentum P_ideal + P_profile, and
  B = 0.97 already raises the required collective about 6%; B outside (0, 1]
  raises ValueError.
- Mixing radians and degrees for collective: the module works in radians
  (theta0 = 0.132839 rad = 7.61 deg on the reference rotor) and the
  published 5-10 deg band is in degrees; compare after conversion, not on
  the raw number.
- Calling the summary with a collective that does not reproduce the thrust:
  hover_blade_element_summary verifies the supplied collective reproduces
  the thrust-derived C_T and raises ValueError on a mismatch, so pass one
  consistent hover state rather than a sweep point.
- Splitting the torque coefficient incorrectly: the induced term is
  lambda*C_T and the profile term sigma*Cd0/8; they must sum to the total to
  1e-12, so do not double count profile drag when you already have a total
  C_Q.
- Reading the figure of merit above 1: FM = C_T^1.5/(sqrt(2)*C_Q) sits in
  (0, 1) for a real rotor and equals exactly 1 only at the ideal C_Q; an FM
  at or above 1 flags a coefficient inconsistency.

## Related leaves

- flight-mechanics/performance/rotorcraft-hover-performance: the
  momentum-theory power leaf; the B = 1 cross-leaf identity ties the
  two models.
- flight-mechanics/performance/rotorcraft-blade-flapping-dynamics:
  blade dynamics sibling that also consumes theta0.
- flight-mechanics/performance/rotorcraft-tail-rotor-sizing.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_blade_element_hover_performance.py

The test covers the worked example with the spec magnitude bounds
(C_T about 0.00463, inflow about 0.0481, theta0 about 0.1328 rad at
B = 1 and 0.1409 rad at B = 0.97, C_Q about 3.43e-4, Q about 7986 N m,
P about 351383 W, FM about 0.650), the closed-form formulas checked
against independent hand computation, the collective round trip to C_T
at 1e-9, the torque split identity with the profile term equal to
sigma * Cd0 / 8 exactly, the power and FM cross-leaf identities against
the momentum hover leaf, tip-loss monotonicity, figure-of-merit bounds
with the ideal limit, exact dict keys of the summary and polar chains,
the fixed-point inflow closure of the polar, run-to-run determinism,
absence of random or external imports, and ValueError rejection of
every non-physical input in the validation list.

## Compliance

- Standards referenced, not reproduced: FAR 29 (rotorcraft
  airworthiness, certification context only). The blade-element hover
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
