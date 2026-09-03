# Wave-24R leaf spec: reaction-wheel-control (space-systems)

- Path: skills/space-systems/adcs/reaction-wheel-control/
- Pack: adcs (existing: attitude-control-sizing,
  attitude-determination-triad, magnetorquer-control, star-tracker,
  sun-pointing)
- Standards ids: ecss  (Ledger Standard: ecss)
- Family: space-systems

## Claim

Reaction wheel attitude control law for spacecraft: command wheel
torques from an attitude and rate error (PD or PID on quaternion error),
account for the wheel momentum coupling term, check wheel torque and
momentum saturation, and compute a momentum desaturation torque command
for the magnetorquers. Produces the commanded wheel torque vector, the
accumulated wheel momentum, the saturation verdict, and the desaturation
dipole estimate.

Does NOT do: wheel SIZING for a slew (attitude-control-sizing owns
momentum capacity for commanded slews and margins), magnetorquer-only
detumbling (magnetorquer-control), attitude determination (triad /
star-tracker), rigid-body dynamics propagation in depth
(gnc-autonomy/space/attitude-dynamics). This leaf is the CONTROL LAW and
momentum management for a wheel-based actuator suite.

## Model (implement exactly)

Quaternion error: given the current attitude quaternion q (body to
reference) and the reference/target q_ref, the error quaternion
q_err = q_ref^-1 (x) q (document the convention), with vector part
q_err_vec (3-vector). Small-angle attitude error theta_err ~
2 * q_err_vec (rad).

Rate error: omega_err = omega_body - omega_ref (omega_ref input; default
0 for inertial pointing).

Control law (PD in the body frame, wheels produce torque about each
body axis):
- h_wheel_desired accumulation handled by the plant model below.
- Wheel torque command: tau_cmd = -Kp * (2*q_err_vec) - Kd * omega_err
  (+ optional feedforward of the reference rate dynamics; keep the PD
  form and document that integral action is on the wheel momentum, not
  the attitude).
Wheel plant (simplified, deterministic): each wheel i has moment of
inertia J_w (kg m^2) and speed omega_w_i (rad/s); wheel momentum
h_w = J_w * omega_w (body axis aligned wheel cluster, 3 orthogonal
wheels assumed; document assumption). The wheel torque changes the wheel
momentum: h_w_dot = tau_cmd - omega_body x h_w (transport term; the
body-rate cross coupling). Integrate wheel speed with dt.

Saturation:
- Torque saturation: if |tau_cmd_i| > tau_max_i, clip and flag.
- Momentum saturation: if |h_w_i| > h_max_i, flag; momentum
  desaturation needed.

Desaturation with magnetorquers: required torque to unload the excess
wheel momentum over the desat horizon T_desat:
- tau_desat = -(h_w - h_target)/T_desat (h_target input, default 0)
- dipole command m_desat = (tau_desat x B)/|B|^2 where B is the local
  magnetic field vector input (T); warn when tau_desat is nearly aligned
  with B (|cross| small).

Functions:
- quaternion_error(q_current, q_ref) -> q_err (vector part and scalar)
- attitude_error_vector(q_err) -> 2*q_err_vec (rad)
- pd_wheel_torque(kp, kd, theta_err_vec, omega_err) -> tau_cmd
- wheel_momentum_update(h_w, tau_cmd, omega_body, dt) -> h_w_new
- torque_saturation(tau_cmd, tau_max) -> (tau_clipped, saturated_flag)
- momentum_saturation(h_w, h_max) -> (excess, flag)
- desaturation_torque(h_w, h_target, t_desat)
- dipole_from_torque(tau_desat, b_field) -> (m_desat, alignment_warning)
- run_wheel_control(q0, omega0, q_ref, kp, kd, j_w, h_w0, omega_body
  samples, tau_max, h_max, dt, n_steps) -> per-step history + verdicts
ValueError on: non-positive gains, J_w <= 0, dt <= 0, |B| ~ 0 when
desat requested, non-finite inputs, h_max <= 0, t_desat <= 0.

## Worked example

Spacecraft: J_w = 0.01 kg m^2 per wheel, initial body rate 0, initial
attitude q0 = [1,0,0,0], target q_ref rotates the spacecraft 10 deg
about the body z axis: q_ref = [cos(5deg), 0, 0, sin(5deg)] =
[0.99619, 0, 0, 0.08716]. kp = 0.05 (1/s^2), kd = 0.2 (1/s), dt = 0.01 s,
run 20 s. Anchors (from your run):
- The commanded torque is initially negative about z (decelerate the
  error) and the spacecraft reaches the target with small overshoot;
  the attitude error norm at 20 s is below 1 deg (assert with the value
  your run produces).
- Wheel momentum magnitude grows to roughly the impulse
  integral |integral tau dt| and stays below h_max when tau_max and
  h_max are generous.
- Saturation: rerun with tau_max tiny (e.g. 1e-4 N m); the saturated
  flag triggers and the settling is slower (assert flag true).
- Desaturation: with h_w = [0, 0, 0.2] N m s excess over h_target and
  B = [2e-5, 0, 0] T, T_desat = 100 s: tau_desat = -[0,0,0.2]/100 and
  m_desat_y ~= tau_desat_z * B_x/|B|^2 sign-correct (assert formula).
Test identities:
- With zero error, torque = 0 and wheel momentum is constant in the
  inertial... (in body frame with omega_body = 0 the transport term is
  0, so momentum is constant: assert).
- Error quaternion: q_err for q = q_ref is identity.
- Scaling: doubling kp doubles the initial torque magnitude.
- Desat dipole formula: for perpendicular geometry the resulting torque
  m x B equals tau_desat within 1e-12.
- ValueError rejections.

## Corpus tasks (2 tasks, ids w24r-reaction-wheel-control-1/2)

Distinctive tokens: reaction-wheel-control, wheel-torque-command,
wheel-momentum saturation, momentum-desaturation, quaternion-error
feedback. Avoid: "slew sizing", "momentum wheel capacity", "detumble
rate", "B-dot" (magnetorquer-control / attitude-control-sizing claims;
the B-dot detumble law belongs to the magnetorquer leaf).

1. "design the reaction wheel control law for the spacecraft pointing
   mode: command the wheel torques from the quaternion error and body
   rate with PD gains, integrate the wheel momentum with the transport
   term, and flag torque and momentum saturation during the acquisition"
2. "compute the momentum desaturation command for the wheel cluster:
   given the accumulated wheel momentum excess, the desaturation
   horizon, and the local magnetic field, find the magnetorquer dipole
   that unloads the wheels and warn if the torque demand lies along the
   field"

## SKILL body notes

Pair with attitude-control-sizing (actuator sizing and margins),
magnetorquer-control (the desaturation actuator and its B-dot law),
gnc-autonomy/space/attitude-dynamics (rigid-body plant). Worked example
uses the values above.
