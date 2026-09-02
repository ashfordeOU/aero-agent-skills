---
name: short-period-mode-analysis
description: "Use when you must analyze the short-period longitudinal mode of an aircraft: convert the dimensionless stability derivatives C_m_alpha, C_m_q, C_m_alphadot, C_Z_alpha and C_Z_q to dimensional per-unit-mass derivatives with the aerodynamic timescale, compute the short-period natural frequency and damping ratio from the two-DOF pitch model, verify the phugoid separation assumption, and check the mode against the Level 1 flying qualities damping and frequency boundaries for the flight phase category. Produces the mode metrics and the Level 1, 2, or 3 verdict that feeds the dynamic stability assessment and complements the static longitudinal stability leaf. Trigger: short period, natural frequency, damping ratio, flying qualities, pitch oscillation, stability derivatives, mode analysis."
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
  tags: [short-period, short-period-mode, natural-frequency, damping-ratio, flying-qualities, stability-derivatives, dimensionless-conversion, pitch-oscillation, phugoid-separation]
  version: 0.1.0
  author: Aero Agent Skills
---

# Short-Period Mode Analysis (flight-mechanics/stability-control/short-period-mode-analysis)

Use when the task is the short-period longitudinal mode: the fast,
well-damped pitch oscillation that dominates the response to elevator
input and turbulence on transport aircraft. This leaf takes the
dimensionless stability derivatives, converts them to dimensional
per-unit-mass derivatives, and derives the short-period natural
frequency and damping ratio from the two-DOF (alpha, q) pitch model,
then checks the mode against Level 1 flying qualities damping and
frequency boundaries. It complements the static pitch stability
treatment of flight-mechanics/stability-control/longitudinal-stability
and the full-mode treatment of
flight-mechanics/stability-control/dynamic-stability.

## Domain quick reference

Documented convention (stability axes): x forward, y out the right
wing, z down. Perturbation states are the angle of attack alpha and
the pitch rate q. Dimensionless stability coefficients (per rad):
C_Z_alpha, C_Z_q, C_m_alpha, C_m_q, C_m_alphadot. Conversion to
dimensional per-unit-mass derivatives uses the dynamic pressure
q_bar, the wing area S, the mean chord c_bar, the mass m, the pitch
inertia I_yy, the speed V, and the aerodynamic timescale
tau = c_bar / (2 * V):

- Z_alpha = q_bar * S * C_Z_alpha / m, in m/s^2 per rad.
- Z_q = q_bar * S * c_bar * C_Z_q / (2 * V * m), in m/s per rad;
  the state matrix keeps the 1 + Z_q / V term only when |Z_q| / V is
  not negligible (z_q_negligible flags the case).
- M_alpha = q_bar * S * c_bar * C_m_alpha / I_yy, in 1/s^2 per rad.
- M_q = q_bar * S * c_bar^2 * C_m_q / (2 * V * I_yy), in 1/s per rad.
- M_alphadot = q_bar * S * c_bar^2 * C_m_alphadot / (2 * V * I_yy),
  in 1/s per rad.

The two-DOF pitch model with Z_q neglected has the state matrix

  A = [[Z_alpha / V, 1],
       [M_alpha + M_alphadot * Z_alpha / V, M_q + M_alphadot]]

with det(A) = M_q * Z_alpha / V - M_alpha (the M_alphadot terms
cancel in the determinant) and tr(A) = Z_alpha / V + M_q +
M_alphadot. Therefore:

- omega_nsp = sqrt(M_q * Z_alpha / V - M_alpha), in rad/s.
- zeta_sp = -(Z_alpha / V + M_q + M_alphadot) / (2 * omega_nsp),
  dimensionless.

For a pitch-stable, damped configuration M_alpha < 0, M_q < 0 and
Z_alpha < 0, so the radicand is positive. A non-positive radicand is
categorized as a non-oscillatory or divergent (unstable) mode, and
short_period_analysis returns it with level 3. Zero total damping
gives zeta_sp = 0 (undamped oscillation) and negative total damping
gives zeta_sp < 0 (divergent oscillation); both fail Level 1.

Phugoid separation: the Lanchester phugoid frequency is
omega_np = sqrt(2) * g / V. The short-period approximation assumes
the phugoid is much slower; phugoid_separation flags the mode as
separated when omega_nsp / omega_np >= 5 (default).

Level 1 flying qualities (MIL-F-8785C style summary, referenced not
reproduced): damping ratio bands 0.35-1.30 (category A), 0.30-2.00
(category B), 0.25-2.00 (category C); minimum natural frequency
0.28 rad/s (A and C) and 0.10 rad/s (B). Level 1 requires both
criteria, boundaries inclusive. A damped oscillation outside the
Level 1 band is Level 2; undamped, divergent, or non-oscillatory
modes are Level 3.

Relation to the longitudinal-stability leaf: that leaf establishes
static pitch stability from C_m_alpha (the pitch stiffness slope and
the neutral point); this leaf treats the same configuration
dynamically, where M_alpha contributes the spring term of the
short-period oscillation while M_q and M_alphadot provide the
damping.

## Workflow

1. Collect the dynamic pressure, wing area, mean chord, speed, mass,
   pitch inertia, and the coefficient slopes C_Z_alpha, C_Z_q,
   C_m_alpha, C_m_q, C_m_alphadot.
2. Convert the coefficients to dimensional derivatives with
   dimensionless_derivative_conversion; check the resulting Z_q with
   z_q_negligible to confirm the approximation holds.
3. Compute the natural frequency with short_period_frequency and the
   damping ratio with short_period_damping.
4. Verify the mode separation with phugoid_separation against the
   Lanchester phugoid frequency.
5. Get the complete verdict with short_period_analysis, which returns
   stable, oscillatory, omega_n, zeta, and the Level 1/2/3 verdict
   with reasons; pick the flight phase category (A, B, or C) for the
   band check.
6. Confirm the deterministic checks with the contract test
   scripts/test_short_period_mode_analysis.py.

## Worked example

A transport configuration at cruise: q_bar = 14000 Pa, S = 30 m^2,
c_bar = 2.5 m, V = 150 m/s, m = 12000 kg, I_yy = 85000 kg m^2,
C_Z_alpha = -5.0, C_Z_q = -3.0, C_m_alpha = -0.6, C_m_q = -12.0,
C_m_alphadot = -3.0.

- tau = 2.5 / 300 = 0.00833 s.
- Z_alpha = 14000 * 30 * (-5) / 12000 = -175 m/s^2 per rad, so
  Z_alpha / V = -1.167 /s.
- M_alpha = 14000 * 30 * 2.5 * (-0.6) / 85000 = -7.41 /s^2.
- M_q = 14000 * 30 * 6.25 * (-12) / (2 * 150 * 85000) = -1.235 /s.
- M_alphadot = 14000 * 30 * 6.25 * (-3) / (2 * 150 * 85000) =
  -0.309 /s.
- omega_nsp = sqrt((-1.235)(-175)/150 - (-7.41)) = sqrt(8.853) =
  2.98 rad/s (period about 2.1 s).
- zeta_sp = -(-1.167 - 1.235 - 0.309) / (2 * 2.98) = 0.456.
- Level 1 check (category A): zeta 0.456 is within [0.35, 1.30] and
  omega_n 2.98 rad/s is above 0.28 rad/s, so the mode is Level 1.
- Phugoid separation: omega_np = sqrt(2) * 9.80665 / 150 =
  0.0925 rad/s; the ratio omega_nsp / omega_np = 32.2, well above
  the minimum of 5, so the approximation is valid.
- Z_q negligibility: |Z_q| / V = 0.875 / 150 = 0.0058, below 0.05,
  so neglecting Z_q in the state matrix is justified.

## Related leaves

- flight-mechanics/stability-control/longitudinal-stability: static
  pitch stability, C_m_alpha sign, and neutral point; the static
  counterpart of this leaf.
- flight-mechanics/stability-control/dynamic-stability: the full
  longitudinal and lateral-directional mode set including the
  short-period band criterion at the aircraft level.
- flight-mechanics/stability-control/trim-analysis: the trimmed
  flight condition (q_bar, alpha) that fixes the operating point for
  the derivative evaluation.
- flight-mechanics/stability-control/stability-derivatives-avl:
  estimating the dimensionless coefficient slopes this leaf consumes.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_short_period_mode_analysis.py

The test covers the derivative conversion, the natural frequency and
damping anchors, the M_alphadot effect on damping, zero and negative
damping, unstable non-oscillatory modes, the Level 1 boundaries at
the band edges and frequency floors, the category-dependent bands,
phugoid separation, the Z_q negligibility check, and invalid-input
edge cases.

## Compliance

- Standards referenced, not reproduced: FAR-25.181 and CS-25.181
  require heavily damped short period oscillations for transport
  aeroplanes; the damping and frequency bands are a MIL-F-8785C style
  summary only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
