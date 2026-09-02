---
name: dynamic-stability
description: "Use when you must evaluate the dynamic stability of an aircraft: compute the longitudinal stability derivatives (pitch stiffness M_alpha, pitch damping M_q, vertical force Z_alpha), estimate the short period and phugoid natural frequency and damping ratio from those derivatives, classify the lateral-directional modes (Dutch roll, roll subsidence, spiral) from the eigenvalues, and check each dynamic stability criterion: the short period damping band, the minimum Dutch roll damping, the spiral time to double, the roll subsidence limit, and the non-divergent phugoid. Produces the mode metrics and the adequate or inadequate verdicts that gate the dynamic stability assessment. Trigger: dynamic stability, short period, phugoid, stability derivatives, classify modes, damping ratio, natural frequency, eigenvalues, time to double, roll subsidence."
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
  tags: [dynamic-stability, short-period, phugoid, stability-derivatives, classify-modes, damping-ratio, natural-frequency, eigenvalues, time-to-double, roll-subsidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# Dynamic Stability (flight-mechanics/stability-control/dynamic-stability)

Use when the task is dynamic stability analysis: the longitudinal
modes (short period, phugoid), the lateral-directional mode
classification, and the damping and frequency criteria.

## Domain quick reference

Documented convention (stability axes): x forward, y out the right
wing, z down. Perturbation states are the angle of attack alpha and
the pitch rate q. All stability derivatives below are per unit mass:
M_alpha and M_q use the pitch inertia I_yy, Z_alpha uses the mass m.
The pitch stiffness M_alpha, the pitch damping M_q, and the vertical
force derivative Z_alpha are negative for a pitch-stable, damped
configuration; all angles in radians.

- Short period: the reduced-order (alpha, q) model with the state
  matrix A = [[Z_alpha/V, 1], [M_alpha, M_q]] gives the natural
  frequency omega_ns = sqrt(det A) = sqrt(M_q * Z_alpha / V - M_alpha)
  and the damping ratio from tr A = Z_alpha / V + M_q = -2 * zeta_s *
  omega_ns. The short period is a fast, well damped pitch oscillation,
  roughly 1-4 s on transport aircraft.
- Phugoid: the slow pitch-speed oscillation. The Lanchester
  approximation gives omega_np = sqrt(2) * g / V, the period
  T_p = sqrt(2) * pi * V / g (roughly 30-60 s), and the damping ratio
  zeta_p = 1 / (sqrt(2) * (L/D)). The phugoid is lightly damped.
- Stability derivatives: Z_alpha = -(q_bar * S * C_Lalpha) / m,
  M_alpha = (q_bar * S * c_bar * C_malpha) / I_yy, and
  M_q = (q_bar * S * c_bar^2 * C_mq) / (2 * V * I_yy), with the dynamic
  pressure q_bar, the wing area S, the mean chord c_bar, and the lift
  and moment coefficient slopes C_Lalpha, C_malpha, C_mq.
- Lateral-directional modes: a complex eigenvalue pair (non-zero
  imaginary part) is an oscillatory mode: a damped Dutch roll when the
  real part is negative, a divergent oscillation when it is positive.
  Real negative eigenvalues are convergent non-oscillatory modes: the
  fast roll subsidence (roll mode, time constant tau = -1 / L_p) and
  the slow stable spiral. A real positive eigenvalue is a divergent
  spiral. For a complex pair lambda = re + im * j the natural
  frequency is omega_n = |lambda| and the damping ratio is
  zeta = -re / |lambda|.
- Metrics: a divergent real root doubles amplitude in
  T2 = ln(2) / lambda; a convergent real root halves amplitude in
  T_half = ln(2) / |lambda|.
- Criteria: FAR-25.181 requires short period oscillations to be
  heavily damped and phugoid oscillations not to grow in amplitude.
  Common level 1 handling-quality criteria (MIL-F-8785C style,
  summary only, not reproduced): short period damping ratio in
  [0.3, 2.0]; Dutch roll damping ratio at least 0.08 with
  zeta * omega_n at least 0.15; roll subsidence time constant at most
  1.0 s; divergent spiral time to double at least 20 s; phugoid
  damping ratio positive.

## Workflow

1. Collect the dynamic pressure, wing area, mean chord, mass, pitch
   inertia, speed, and the coefficient slopes C_Lalpha, C_malpha,
   C_mq.
2. Compute the derivatives with z_alpha, m_alpha, and m_q.
3. Compute the short period frequency and damping ratio with
   short_period_frequency and short_period_damping; check the band
   with short_period_damping_adequate.
4. Compute the phugoid frequency, period, and damping ratio with
   phugoid_frequency, phugoid_period, and phugoid_damping; check the
   verdict with phugoid_acceptable.
5. Collect the lateral eigenvalues, classify each with classify_mode,
   and derive the damping ratio with damping_ratio, the time to double
   with time_to_double, or the time to half with time_to_half.
6. Check the Dutch roll criterion with dutch_roll_adequate, the roll
   subsidence limit with roll_mode_acceptable, and the spiral with
   spiral_acceptable.
7. Gate the dynamic stability assessment on the short period band,
   the phugoid verdict, and the three lateral criteria.

## Pitfalls

- Confusing the sign of the pitch stiffness: M_alpha negative is
  pitch-stable; a positive M_alpha drives the short period radicand
  toward zero or negative, which the model rejects.
- Forgetting the per-unit-mass normalization: M_alpha and M_q need
  I_yy in the denominator, Z_alpha needs m.
- Mixing units: the short period and phugoid formulas assume V in
  m/s, g in m/s^2, and radian-based derivatives; feeding degrees
  misstates every result.
- Reading the spiral criterion backwards: a divergent spiral passes
  only when the time to double is at least 20 s; a stable spiral
  (negative root) always passes.
- Confusing time to double with time to half: time_to_double needs a
  positive divergent root, time_to_half needs a negative convergent
  root, and each rejects the wrong sign.
- Treating every complex pair as damped: the real part decides; a
  positive real part is a divergent oscillation regardless of the
  imaginary part.

## Behavior contract (gate 3)

The dynamic stability logic is exercised by the gate 3 contract test:
scripts/test_dynamic_stability.py against
scripts/dynamic_stability_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_dynamic_stability.py

## Compliance

- Standards referenced, not reproduced: FAR-25.181 and CS-25.181
  require heavily damped short period oscillations and non-growing
  phugoid oscillations for transport aeroplanes; the derivative and
  mode computations are common flight mechanics methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
