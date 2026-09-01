---
name: spin-recovery
description: "Analyze spin entry, developed spin modes, and recovery controls for a stalled aircraft: compute the post-stall autorotative band and stall penetration, estimate the spin descent rate and rotation rate from weight, wing area, and spin drag, classify the spin mode as steep or flat, and size the altitude lost and rotation stop time during spin-recovery. Use when the task is spin recovery, autorotation, spin modes, incipient spin, flat spin, or post-stall departure recovery. Trigger: spin recovery, autorotation, flat spin, incipient spin, spin entry, anti-spin controls, post-stall departure."
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
  tags: [spin-recovery, autorotation-band, spin-modes, flat-spin, incipient-spin, anti-spin-controls, post-stall-departure]
  version: 0.1.0
  author: AeroSkills
---

# Spin Recovery (flight-mechanics/stability-control/spin-recovery)

Use when the task is spin entry, developed spin modes, autorotation,
and the recovery control sequence for a stalled aircraft.

## Domain quick reference

- A spin is a developed post-stall rotation about a near-vertical
  axis, sustained by autorotation: beyond the stall the lift curve
  slope turns negative, so the more stalled wing half loses lift and
  the asymmetric moments keep the rotation going.
- Post-stall lift model (linear drop):
  Cl = cl_max + m_post * (alpha - alpha_stall), m_post < 0.
  Worked example: cl_max = 1.4, alpha_stall = 16 deg,
  m_post = -0.02 per deg, alpha = 20 deg gives Cl = 1.32.
- Autorotative band: the alpha range on the negative-slope post-stall
  region, ending where the post-stall lift returns to zero,
  alpha_end = alpha_stall + cl_max / |m_post|. Worked example:
  16 + 1.4 / 0.02 = 86 deg. The wing is autorotating only while
  alpha_stall < alpha < alpha_end.
- Spin descent rate: V_d = sqrt(2 * W / (rho * S * C_D_spin)) with
  C_D_spin the spin drag coefficient (flat spins near 1.0 to 1.6,
  steep spins lower). Worked example: W = 15000 N, S = 16 m^2,
  rho = 1.225, C_D_spin = 1.2 gives V_d = 35.7 m/s.
- Developed spin rotation rate: Omega = 2 * V_d * nu / b with nu the
  nondimensional rotation rate. Worked example: nu = 0.4, b = 10 m
  gives Omega = 2.86 rad/s.
- Spin mode by the flatness ratio nu = Omega * b / (2 * V_d):
  below 0.3 steep (descent-dominated), 0.3 to 0.5 developed,
  above 0.5 flat (rotation-dominated). Worked example: tip speed
  Omega * b / 2 = 14.3 m/s against V_d = 35.7 m/s gives nu = 0.4.
- Recovery sizing: altitude lost is V_d * t_rec (35.7 m/s for 3 s is
  107 m), and the rotation decays exponentially,
  t_stop = tau * ln(Omega_0 / Omega_stop). Worked example:
  Omega_0 = 2.86 rad/s, tau = 1.5 s, Omega_stop = 0.2 rad/s gives
  3.99 s.
- Standard recovery sequence: power to idle, ailerons neutral, rudder
  full opposite to the rotation, elevator forward to break the stall;
  hold the inputs until rotation stops, then recover from the dive.

## Workflow

1. Confirm the departure: check the stall penetration and the
   autorotative condition with stall_penetration_deg and
   autorotative_condition.
2. Compute the post-stall lift and the band edge with
   post_stall_lift_coefficient and autorotation_band_end_deg.
3. Estimate the spin descent rate and rotation rate with
   spin_descent_rate and spin_rotation_rate.
4. Classify the mode with spin_flatness_ratio: below 0.3 steep,
   0.3 to 0.5 developed, above 0.5 flat.
5. Apply the recovery sequence: power idle, ailerons neutral, rudder
   opposite, elevator forward; hold until rotation stops.
6. Size the recovery with recovery_altitude_loss and
   rotation_stop_time, and check the altitude lost against the
   minimum recovery altitude for the flight condition.

## Pitfalls

- Routing takeoff questions here: ground roll, lift-off speed, and
  field length belong to the takeoff-performance sub-skill; the spin
  is a post-stall stability regime, not a takeoff phase.
- Routing landing questions here: approach speed, flare, ground roll,
  and stopping distance belong to the landing-performance sub-skill;
  the spin is not a landing regime.
- Routing drag breakdown questions here: the aerodynamics drag-polars
  leaves give the induced and parasite drag breakdown against lift,
  but they do not model the autorotative condition or the spin
  rotation rate.
- Treating any alpha above the stall angle as autorotative: the wing
  must sit inside the negative-slope band (alpha < alpha_end); past
  the band edge the linear post-stall model loses validity.
- Deflecting ailerons with the spin: standard recovery requires
  ailerons neutral; aileron with the rotation is a pro-spin input.
- Getting the rudder direction wrong: rudder goes opposite to the
  rotation, not with it; confuse spin direction with turn direction
  and the spin deepens.
- Using a free-air lift curve in the spin: the post-stall slope is
  negative and much flatter than the pre-stall value, so the lift
  estimate must use the post-stall model.
- Using one nondimensional rate for every spin: mixing the steep-spin
  nu near 0.2 with the flat-spin nu above 0.5 mis-sizes the rotation
  rate and the recovery altitude.

## Behavior contract (gate 3)

The post-stall lift, autorotative band, spin descent and rotation
rates, mode classification, and recovery sizing logic is exercised by
the gate 3 contract test: scripts/test_spin_recovery.py against
scripts/spin_recovery_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_spin_recovery.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 set the
  spin-recovery demonstration requirement for transport aeroplanes;
  the simplified spin models are common flight-mechanics methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
