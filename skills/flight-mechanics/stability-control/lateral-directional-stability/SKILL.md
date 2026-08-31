---
name: lateral-directional-stability
description: "Use when you must assess the lateral-directional stability of an aircraft: compute the directional stability derivative Cn beta from the vertical tail volume coefficient, fin efficiency, and fin lift slope; compute the dihedral contribution to the roll stability derivative Cl beta from the wing dihedral angle and lift coefficient; and characterize the lateral-directional modes: Dutch roll frequency and damping ratio from the simplified yaw sideslip model, the roll mode time constant from the roll damping derivative, and the spiral mode stability classification. Produces the stability derivatives, the mode metrics, and the stable or unstable verdicts that gate the lateral-directional stability assessment. Trigger: lateral directional stability, dihedral effect, directional stability, vertical tail volume, Dutch roll, roll mode, spiral mode, sideslip, yaw stability."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: stability-control
  tags: [lateral-directional-stability, directional-stability, dihedral-effect, vertical-tail-volume, dutch-roll, roll-mode, spiral-mode, sideslip, roll-stability, yaw-stability]
  version: 0.1.0
  author: AeroSkills
---

# Lateral-Directional Stability (flight-mechanics/stability-control/lateral-directional-stability)

Use when the task is lateral-directional stability analysis: the
directional stability derivative from the vertical tail, the dihedral
contribution to roll stability, and the roll, Dutch roll, and spiral
mode characteristics.

## Domain quick reference

Documented convention (stability axes): x forward, y out the right
wing, z down. The sideslip angle beta is positive when the relative
wind comes from the left, so the velocity vector points to the right
of the plane of symmetry. The yawing moment coefficient C_n is
positive when the nose turns toward the relative wind; the rolling
moment coefficient C_l is positive when the right wing rolls down.

- Directional (yaw) stability: a positive sideslip must produce a
  restoring yawing moment, so the total derivative C_n_beta > 0. The
  vertical tail contributes
  C_n_beta_vt = eta_vt * V_v * a_vt * (1 + k_s), where
  V_v = (S_vt * l_vt) / (S * b) is the vertical tail volume
  coefficient (dimensionless), eta_vt is the fin efficiency (sidewash
  and dynamic pressure ratio, dimensionless, 0 < eta_vt <= 1), a_vt
  is the fin lift slope (1/rad), and k_s is the sidewash gradient
  (dimensionless, >= 0). The fuselage adds a usually negative term
  C_n_beta_fuselage. Texts that define beta with the opposite sign
  write the fin term with a leading minus; the magnitude is unchanged.
- Lateral (roll) stability: a positive sideslip must produce a
  restoring rolling moment, so the total derivative C_l_beta < 0. The
  first-order dihedral contribution is C_l_beta_gamma = -C_L * gamma,
  with C_L the wing lift coefficient and gamma the dihedral angle in
  radians; the windward panel gains lift and the leeward panel loses
  it for positive dihedral. Anhedral (negative gamma) reverses the
  effect and destabilizes the roll response.
- Roll mode: the simplified roll equation p_dot = L_p * p gives the
  roll subsidence time constant tau = -1 / L_p, with the roll damping
  derivative L_p = (q_bar * S * b^2 * C_lp) / (2 * V * I_xx) built
  from the roll damping coefficient C_lp (negative), the dynamic
  pressure q_bar, the wing area S, the span b, the speed V, and the
  roll inertia I_xx. Roll damping always stabilizes the roll mode.
- Dutch roll: the simplified yaw-sideslip model (states beta and yaw
  rate r) gives the natural frequency
  omega_n = sqrt(N_beta + (N_r * Y_beta - N_beta * Y_r) / V) and the
  damping ratio zeta = -(Y_beta / V + N_r) / (2 * omega_n), where
  N_beta is the yaw stiffness (1/s^2), N_r and Y_r are the rate
  derivatives (1/s), Y_beta is the side force derivative (m/s^2), and
  V is the speed (m/s). Dutch roll is an oscillatory yaw-sideslip
  motion with a lightly damped character on many aircraft.
- Spiral mode: the slow lateral root approximates
  lambda_s = (g / V) * (L_beta * N_r - L_r * N_beta) / (N_beta * L_p);
  with N_beta > 0 and L_p < 0 the spiral mode is convergent (stable)
  when L_beta * N_r - L_r * N_beta > 0, and divergent otherwise.
- FAR-25 and CS-25 require positive directional and lateral static
  stability and adequate lateral-directional oscillation damping for
  transport aeroplanes; the derivative and mode computations above
  are the standard methodology used to check those characteristics.

## Workflow

1. Collect the vertical tail area and arm (S_vt, l_vt) and the wing
   reference area and span (S, b); compute the volume coefficient
   with vertical_tail_volume.
2. Compute the fin contribution with cn_beta_vertical_tail, add any
   fuselage term with cn_beta_total, and check the verdict with
   directionally_stable.
3. Take the wing lift coefficient and dihedral angle, compute the
   dihedral contribution with cl_beta_dihedral, and check the verdict
   with laterally_stable.
4. Compute the roll damping derivative with roll_damping_derivative
   and the roll mode time constant with roll_mode_time_constant.
5. Assemble the yaw and side force derivatives and compute the Dutch
   roll frequency and damping ratio with dutch_roll_frequency and
   dutch_roll_damping_ratio.
6. Classify the spiral mode with spiral_mode_stable and report the
   approximate root with spiral_eigenvalue.
7. Gate the lateral-directional stability assessment on the three
   verdicts (directional, lateral, spiral) and the Dutch roll
   damping ratio.

## Pitfalls

- Reversing the derivative signs: directional stability needs
  C_n_beta > 0 and lateral (roll) stability needs C_l_beta < 0 in
  this convention; flipping either sign flips the verdict.
- Mixing sign conventions: some textbooks define beta with the
  opposite sign and write the fin term with a leading minus; state
  the convention before comparing numbers.
- Converting the dihedral angle twice: cl_beta_dihedral takes degrees
  and converts internally; passing radians already converted
  misstates the derivative by a factor of 57.3.
- Confusing the volume coefficient with the derivative: V_v is a
  geometric ratio; C_n_beta_vt also needs the fin efficiency and lift
  slope.
- Accepting a non-negative roll damping derivative: L_p must be
  negative; roll_mode_time_constant rejects non-negative values
  because the roll mode would not subside.
- Reading the spiral criterion backwards: with L_p < 0 the spiral
  mode converges when L_beta * N_r - L_r * N_beta > 0; the opposite
  sign diverges.

## Behavior contract (gate 3)

The lateral-directional stability logic is exercised by the gate 3
contract test: scripts/test_lateral_directional.py against
scripts/lateral_directional_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_lateral_directional.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 require
  positive directional and lateral stability and adequate
  lateral-directional oscillation damping for transport aeroplanes;
  the derivative and mode computations are common flight mechanics
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
