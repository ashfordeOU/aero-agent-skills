---
name: reaction-wheel-control
description: "Use when you must design the reaction wheel control law for a spacecraft pointing maneuver: command wheel torques from quaternion error feedback and body rate with PD gains, integrate wheel momentum with the body rate transport term, clip torque commands and flag wheel momentum saturation, and compute the momentum desaturation command with its magnetorquer dipole estimate. Produces the commanded wheel torque vector, the accumulated wheel momentum, the saturation verdict, and the desaturation torque and dipole. Trigger: reaction wheel control, wheel torque command, wheel momentum saturation, momentum desaturation, desaturation horizon, wheel momentum excess, unloads wheel cluster, local magnetic field, magnetorquer dipole, torque demand along the field, warn when the demand lies along the field, find the desaturation dipole for the target momentum, quaternion error feedback, desaturation torque, spacecraft pointing."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: adcs
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: adcs
  tags: [reaction-wheel-control, wheel-torque-command, wheel-momentum-saturation, momentum-desaturation, quaternion-error-feedback, desaturation-torque, reaction-wheel-cluster, spacecraft-pointing]
  version: 0.1.0
  author: AeroSkills
---

# Reaction Wheel Control (space-systems/adcs/reaction-wheel-control)

Use when the task is the reaction wheel attitude control law for a
spacecraft pointing mode: commanding wheel torques from the quaternion
error and the body rate with PD gains, propagating the wheel momentum
including the body rate transport coupling, clipping torque commands
and flagging wheel momentum saturation during an acquisition, and
computing the magnetorquer momentum desaturation command that unloads
an accumulated wheel momentum excess. This leaf implements the wheel
control loop in pure Python, stdlib only. It pairs with
space-systems/adcs/attitude-control-sizing for actuator sizing and
margins, space-systems/adcs/magnetorquer-control for the desaturation
actuator, and gnc-autonomy/space/attitude-dynamics for the rigid body
plant; this leaf is the control law and momentum management, not the
sizing, not the detumbling law, not the attitude determination.

Conventions: quaternions are scalar-first (w, x, y, z) unit tuples with
the Hamilton product. The error quaternion is q_err = q_current (x)
q_ref^-1 (rotation from the reference attitude to the current attitude,
identity at the target), which equals the q_ref^-1 (x) q form under the
Shuster product convention. tau_cmd is the torque the wheel cluster
produces about the body axes, so in the closed loop demo the bus obeys
I * omega_dot = tau_cmd with the module spacecraft inertia I_SC = 0.5
kg m^2 (inertially spherical, documented module constant). The wheel
momentum h_w follows the commanded torque impulse, so during the z slew
of the worked example it mirrors the z command sign.

## Domain quick reference

- Error quaternion: q_err = q_current (x) q_ref^-1, identity when the
  spacecraft is at the target; small angle attitude error
  theta_err ~= 2 * q_err_vec (rad).
- Rate error: omega_err = omega_body - omega_ref (omega_ref = 0 for
  inertial pointing).
- PD wheel torque command (body frame): tau_cmd = -kp * theta_err -
  kd * omega_err, kp in 1/s^2, kd in 1/s. Integral action lives in the
  wheel momentum, not in an attitude integrator.
- Wheel momentum plant: h_w_dot = tau_cmd - omega_body x h_w, where
  the cross term is the body rate transport coupling. Three orthogonal
  body axis wheels, each of inertia j_w, give wheel speeds
  omega_w_i = h_w_i / j_w.
- Torque saturation: clip each axis at +-tau_max and flag when clipped.
- Momentum saturation: flag when |h_w_i| exceeds h_max_i and report the
  excess; desaturation is then required.
- Momentum desaturation torque over horizon T_desat:
  tau_desat = -(h_w - h_target) / T_desat, h_target default 0.
- Desaturation dipole: m_desat = (B x tau_desat) / |B|^2 solves
  torque = m x B, so m_desat x B equals tau_desat for the torque
  component perpendicular to B; warn when tau_desat lies nearly along B
  (the cross product magnitude is then small and the achievable torque
  is small).
- Units are SI throughout: N m, N m s, rad, rad/s, kg m^2, s, T, A m^2.
- ECSS frames the spacecraft control context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Set the pointing target: reference quaternion q_ref, reference rate
   omega_ref (default 0), and the initial attitude q and body rate
   omega from the attitude determination leaf or the mission timeline.
2. Form the error with quaternion_error(q_current, q_ref) and map it to
   the small angle vector with attitude_error_vector (2 * q_err_vec).
3. Command the wheel torque with pd_wheel_torque(kp, kd, theta_err,
   omega_err). Choose kp and kd from the closed loop frequency and
   damping: omega_n = sqrt(kp / I) and zeta = kd / (2 * sqrt(kp * I))
   for a bus inertia I.
4. Clip the command at the wheel torque authority with
   torque_saturation(tau_cmd, tau_max) and honor the flag.
5. Advance the wheel momentum with wheel_momentum_update(h_w, tau_cmd,
   omega_body, dt), then check momentum_saturation(h_w, h_max); a flag
   here means desaturation is needed.
6. For acquisition, run the closed loop demo with run_wheel_control
   (omega_body_samples = None integrates the body rate from omega0);
   pass a sampled body rate profile instead to evaluate commands along
   a recorded trajectory. The demo uses the module bus inertia I_SC.
7. When the wheels are saturated, compute the unload torque with
   desaturation_torque(h_w, h_target, t_desat) and the dipole with
   dipole_from_torque(tau_desat, b_field), and heed the alignment
   warning before passing the dipole to the magnetorquer leaf.
8. Confirm the deterministic checks with the contract test
   scripts/test_reaction_wheel_control.py.

## Worked example

Spacecraft with three orthogonal wheels, j_w = 0.01 kg m^2 each, at
rest at q0 = [1, 0, 0, 0]. Target q_ref = [cos 5 deg, 0, 0, sin 5 deg]
rotates the spacecraft 10 deg about the body z axis. Gains kp = 0.05
1/s^2, kd = 0.2 1/s, dt = 0.01 s, run 20 s (2000 steps), tau_max =
0.1 N m, h_max = 0.5 N m s.

- Error at start: q_err = q0 (x) q_ref^-1 gives q_err_vec =
  (0, 0, -sin 5 deg), so theta_err = (0, 0, -0.1743) rad and the first
  wheel torque command is +0.0087 N m about +z, driving the bus toward
  the target (the wheel reaction on the bus is opposite about the z
  axis). The rate term damps once the bus rotates.
- Acquisition: the bus settles with small overshoot (attitude error
  peaks near 0.76 deg after the first crossing) and the attitude error
  at 20 s is 0.11 deg, below the 1 deg acquisition tolerance.
- Wheel momentum: h_w follows the signed torque impulse integral; the
  magnitude peaks at 0.0134 N m s (wheel speed 1.34 rad/s, about 13
  rpm) and returns near zero as the braking torque cancels the
  acceleration impulse. Both saturation flags stay clear with the
  generous limits.
- Torque saturation: rerun with tau_max = 1e-4 N m; the command clips
  immediately, the flag trips, and the error at 20 s is 7.7 deg, much
  slower than the unconstrained 0.11 deg.
- Momentum saturation: rerun with h_max = 0.004 N m s; the momentum
  flag trips at the peak of the maneuver.
- Desaturation: with h_w = [0, 0, 0.2] N m s excess over h_target and
  B = [2e-5, 0, 0] T over T_desat = 100 s: tau_desat =
  -[0, 0, 0.2] / 100 = [0, 0, -0.002] N m and m_desat =
  (B x tau_desat) / |B|^2 = [0, 100, 0] A m^2; m_desat x B reproduces
  tau_desat exactly (perpendicular geometry) with no alignment warning.

## Verification

- Confirm quaternion_error returns identity when q_current = q_ref and
  unit norm otherwise; doubling kp doubles the initial torque
  magnitude; zero error and zero rate give exactly zero torque.
- Confirm the acquisition run reaches the 10 deg z target with the
  attitude error below 1 deg at 20 s (measured 0.11 deg on this
  implementation) and small overshoot.
- Confirm h_w equals the signed torque impulse integral during the z
  slew (the transport term vanishes for the parallel geometry) and
  stays bounded under generous tau_max and h_max.
- Confirm torque_saturation clips per axis and flags, and that the
  tiny tau_max rerun flags with slower settling.
- Confirm the desaturation numbers: tau_desat = -0.002 N m about z,
  m_desat = +100 A m^2 about y for B along x, m_desat x B within
  1e-12 of tau_desat, and the alignment warning trips for a torque
  demand along the field.
- Confirm ValueError rejection of non-positive gains, j_w <= 0,
  dt <= 0, h_max <= 0, tau_max <= 0, t_desat <= 0, a field at or below
  1e-12 T, and any non-finite input.
- Run the contract test offline: python3
  scripts/test_reaction_wheel_control.py (35 tests, deterministic).

## Related leaves

- space-systems/adcs/attitude-control-sizing: momentum wheel sizing and
  margins for a commanded maneuver; this leaf commands what that leaf
  sizes.
- space-systems/adcs/magnetorquer-control: the desaturation actuator
  and the dipole to torque link, same m x B convention.
- space-systems/adcs/attitude-determination-triad: the attitude
  reference used by the control law.
- space-systems/adcs/star-tracker: fine attitude reference for
  precision pointing.
- space-systems/adcs/sun-pointing: the safe hold pointing target.
- gnc-autonomy/space/attitude-dynamics: the rigid body plant and
  propagation that this leaf keeps simplified.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_reaction_wheel_control.py

The test covers the worked example acquisition (10 deg z slew reaches
the target below 1 deg error at 20 s, small overshoot), the PD
identities (zero error gives zero torque, doubling kp doubles the
initial command, the rate term opposes the rate), the quaternion error
identity at the target and its worked example vector part, wheel
momentum integration with the transport term, per axis torque clipping
and momentum excess flags, torque and momentum saturation in the run,
the momentum equals impulse integral identity, the desaturation torque
and dipole worked example with the m x B reconstruction to 1e-12 and
the alignment warning, the rate profile evaluation mode, and ValueError
rejection of every non-physical input class.

## Compliance

- Standards referenced, not reproduced: ECSS covers spacecraft control
  (standards-map.yaml); the control law relations above are standard
  engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
