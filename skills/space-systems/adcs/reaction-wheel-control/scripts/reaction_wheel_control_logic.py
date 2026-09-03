#!/usr/bin/env python3
"""Reaction wheel attitude control logic (stdlib only).

Reaction wheel control law for a spacecraft ADCS: command wheel torques
from a quaternion error feedback PD law, integrate the wheel momentum
with the body rate transport term, clip wheel torque commands and flag
wheel momentum saturation, and compute the magnetorquer momentum
desaturation command. Paraphrase of the standard reaction wheel control
methodology; ECSS is the pack's reference standard (standards-map.yaml)
and this logic is generic control engineering, not proprietary content.

Conventions
-----------
- All vectors are 3D tuples (x, y, z). Quaternions are scalar-first
  tuples (w, x, y, z), unit norm, representing active rotations with the
  Hamilton product:
      p (x) q = (p_w q_w - p_v.q_v, p_w q_v + q_w p_v + p_v x q_v)
- Attitude quaternion q represents the body attitude relative to the
  reference frame (rotation that carries body coordinates into
  reference coordinates). Kinematics used by the closed loop:
  q_dot = 0.5 q (x) (0, omega_body), with omega_body the body rate.
- Error quaternion: q_err = q_current (x) q_ref^-1, the rotation from
  the reference attitude to the current attitude expressed in the body
  frame (this equals the spec's q_ref^-1 (x) q when (x) is the Shuster
  product, for which p (x) q is the Hamilton product q (x) p). q_err
  is the identity when the spacecraft sits at q_ref, and a target 10
  deg about +z from the identity yields q_err_vec = (0, 0, -sin 5 deg).
- Small angle attitude error: theta_err ~= 2 * q_err_vec (rad).
- Control law (PD on quaternion error in the body frame):
      tau_cmd = -kp * theta_err - kd * omega_err
  with omega_err = omega_body - omega_ref (omega_ref = 0 for inertial
  pointing). tau_cmd is the torque the wheel cluster produces about the
  body axes, so the bus obeys I_sc * omega_dot = tau_cmd in the closed
  loop demo. Integral action is carried by the wheel momentum itself,
  not by an attitude integrator.
- Wheel plant bookkeeping: three orthogonal body-axis wheels, each with
  inertia j_w; the wheel momentum obeys
      h_w_dot = tau_cmd - omega_body x h_w
  (the body rate cross coupling, the transport term), so h_w tracks the
  commanded torque impulse delivered to the bus. Wheel speeds in rad/s
  follow as omega_w_i = h_w_i / j_w.
- Momentum desaturation with magnetorquers over horizon t_desat:
      tau_desat = -(h_w - h_target) / t_desat
      m_desat  = (B x tau_desat) / |B|^2
  solves torque = m x B for the dipole perpendicular to B (the standard
  projection, the same convention as the magnetorquer-control leaf), so
  m_desat x B equals tau_desat for the perpendicular part. A torque
  demand nearly aligned with B is flagged: m x B cannot produce torque
  along B.
- run_wheel_control integrates a simplified closed loop for the worked
  example: spacecraft body inertia I_SC is taken as a module constant
  (a compact inertially spherical bus), so the gyroscopic term omega x
  (I_SC omega) drops and the body rate obeys omega_dot = tau_cmd/I_SC
  (the wheel cluster produces the commanded torque on the bus). This
  leaf does not propagate rigid body dynamics in depth; that belongs to
  the gnc-autonomy attitude dynamics leaf.
- Units are SI throughout: N m, N m s, rad, rad/s, kg m^2, s, T, A m^2.
"""

import math

# Representative compact spacecraft bus inertia per axis, kg m^2.
I_SC = 0.5
# Field magnitude below which a desaturation dipole is undefined, T.
B_MIN = 1.0e-12
# |tau x B| / (|tau| |B|) below this flags a torque demand nearly
# aligned with B (sin of roughly 5 deg).
ALIGN_WARN_SIN = 0.0872


def _dot(u, v):
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def _cross(u, v):
    return (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )


def _norm3(v):
    return math.sqrt(_dot(v, v))


def _finite_vec3(v, name):
    """Validate a 3D vector of finite floats; raise ValueError else."""
    if len(v) != 3:
        raise ValueError("%s must be a 3D vector, got %d components" % (name, len(v)))
    for c in v:
        if not math.isfinite(c):
            raise ValueError("%s must be finite, got %r" % (name, v))
    return (float(v[0]), float(v[1]), float(v[2]))


def _quat_mult(p, q):
    """Hamilton product of two scalar-first quaternions."""
    pw, px, py, pz = p
    qw, qx, qy, qz = q
    return (
        pw * qw - px * qx - py * qy - pz * qz,
        pw * qx + px * qw + py * qz - pz * qy,
        pw * qy - px * qz + py * qw + pz * qx,
        pw * qz + px * qy - py * qx + pz * qw,
    )


def _quat_conj(q):
    return (q[0], -q[1], -q[2], -q[3])


def _quat_norm(q):
    return math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3])


def _quat_normalize(q):
    n = _quat_norm(q)
    if n == 0.0:
        raise ValueError("zero quaternion cannot be normalized")
    return (q[0] / n, q[1] / n, q[2] / n, q[3] / n)


def _check_quat(q, name):
    """Validate a finite unit quaternion; raise ValueError else."""
    if len(q) != 4:
        raise ValueError("%s must be a 4D quaternion, got %d components" % (name, len(q)))
    for c in q:
        if not math.isfinite(c):
            raise ValueError("%s must be finite, got %r" % (name, q))
    return (float(q[0]), float(q[1]), float(q[2]), float(q[3]))


def quaternion_error(q_current, q_ref):
    """Error quaternion q_err = q_current (x) q_ref^-1.

    The rotation from the reference attitude to the current attitude,
    expressed in the body frame: identity when q_current equals q_ref.
    Returns the scalar-first quaternion (w, x, y, z). Raises ValueError
    on non-finite input.
    """
    qc = _check_quat(q_current, "q_current")
    qr = _check_quat(q_ref, "q_ref")
    return _quat_normalize(_quat_mult(qc, _quat_conj(qr)))


def attitude_error_vector(q_err):
    """Small angle attitude error vector theta_err = 2 * q_err_vec (rad).

    q_err_vec is the vector part (x, y, z) of the scalar-first error
    quaternion. Exact rotation angle is 2 * atan2(|q_err_vec|, w); the
    factor 2 form is the small angle approximation. Raises ValueError
    on non-finite input.
    """
    qe = _check_quat(q_err, "q_err")
    return (2.0 * qe[1], 2.0 * qe[2], 2.0 * qe[3])


def pd_wheel_torque(kp, kd, theta_err_vec, omega_err):
    """PD wheel torque command: tau_cmd = -kp*theta_err - kd*omega_err.

    theta_err_vec is the attitude error vector (rad), omega_err the
    body rate error (rad/s), kp in 1/s^2 and kd in 1/s. Returns the
    commanded wheel torque tuple (N m). Raises ValueError on
    non-positive gains or non-finite vectors.
    """
    if kp <= 0.0:
        raise ValueError("kp must be > 0, got %r" % (kp,))
    if kd <= 0.0:
        raise ValueError("kd must be > 0, got %r" % (kd,))
    te = _finite_vec3(theta_err_vec, "theta_err_vec")
    oe = _finite_vec3(omega_err, "omega_err")
    return (
        -kp * te[0] - kd * oe[0],
        -kp * te[1] - kd * oe[1],
        -kp * te[2] - kd * oe[2],
    )


def wheel_momentum_update(h_w, tau_cmd, omega_body, dt):
    """Wheel momentum after one step: h_w_new = h_w + (tau_cmd - omega
    body x h_w) * dt. The omega x h_w term is the body rate transport
    coupling. Returns the wheel momentum tuple (N m s). Raises
    ValueError on non-finite input or dt <= 0.
    """
    if dt <= 0.0:
        raise ValueError("dt must be > 0, got %r" % (dt,))
    hw = _finite_vec3(h_w, "h_w")
    tc = _finite_vec3(tau_cmd, "tau_cmd")
    ob = _finite_vec3(omega_body, "omega_body")
    hw_dot = (
        tc[0] - _cross(ob, hw)[0],
        tc[1] - _cross(ob, hw)[1],
        tc[2] - _cross(ob, hw)[2],
    )
    return (
        hw[0] + hw_dot[0] * dt,
        hw[1] + hw_dot[1] * dt,
        hw[2] + hw_dot[2] * dt,
    )


def torque_saturation(tau_cmd, tau_max):
    """Clip a wheel torque command per axis at +-tau_max.

    tau_max may be a scalar (all axes) or a 3D vector of per-axis
    limits (N m). Returns (tau_clipped, saturated_flag) where the flag
    is True when any axis was clipped. Raises ValueError on
    non-positive limits or non-finite input.
    """
    tc = _finite_vec3(tau_cmd, "tau_cmd")
    if isinstance(tau_max, (int, float)):
        limits = (float(tau_max), float(tau_max), float(tau_max))
    else:
        limits = _finite_vec3(tau_max, "tau_max")
    clipped = []
    flagged = False
    for c, lim in zip(tc, limits):
        if lim <= 0.0:
            raise ValueError("tau_max must be > 0, got %r" % (tau_max,))
        if c > lim:
            clipped.append(lim)
            flagged = True
        elif c < -lim:
            clipped.append(-lim)
            flagged = True
        else:
            clipped.append(c)
    return (clipped[0], clipped[1], clipped[2]), flagged


def momentum_saturation(h_w, h_max):
    """Check wheel momentum against the per-axis limit h_max (N m s).

    h_max may be a scalar (all axes) or a 3D vector. Returns
    (excess, flag): excess is the per-axis amount above the limit and
    flag is True when any axis exceeds it, meaning desaturation is
    needed. Raises ValueError on non-positive limits or non-finite
    input.
    """
    hw = _finite_vec3(h_w, "h_w")
    if isinstance(h_max, (int, float)):
        limits = (float(h_max), float(h_max), float(h_max))
    else:
        limits = _finite_vec3(h_max, "h_max")
    excess = []
    flagged = False
    for c, lim in zip(hw, limits):
        if lim <= 0.0:
            raise ValueError("h_max must be > 0, got %r" % (h_max,))
        over = abs(c) - lim
        if over > 0.0:
            excess.append(over)
            flagged = True
        else:
            excess.append(0.0)
    return (excess[0], excess[1], excess[2]), flagged


def desaturation_torque(h_w, h_target, t_desat):
    """Magnetorquer torque required to unload wheel momentum excess:
    tau_desat = -(h_w - h_target) / t_desat, over the desaturation
    horizon t_desat (s). Returns the torque tuple (N m). Raises
    ValueError on t_desat <= 0 or non-finite input.
    """
    if t_desat <= 0.0:
        raise ValueError("t_desat must be > 0, got %r" % (t_desat,))
    hw = _finite_vec3(h_w, "h_w")
    ht = _finite_vec3(h_target, "h_target")
    return (
        -(hw[0] - ht[0]) / t_desat,
        -(hw[1] - ht[1]) / t_desat,
        -(hw[2] - ht[2]) / t_desat,
    )


def dipole_from_torque(tau_desat, b_field):
    """Dipole command for a desaturation torque demand: solve
    torque = m x B as m = (B x tau_desat) / |B|^2, the standard
    projection that yields m x B = tau_desat for the part of the torque
    perpendicular to B. Returns (m_desat, alignment_warning) with the
    dipole in A m^2; alignment_warning is True when tau_desat is nearly
    aligned with B (|tau x B| small, so the achievable torque is small).
    Raises ValueError on a field at or below B_MIN or non-finite input.
    """
    td = _finite_vec3(tau_desat, "tau_desat")
    bf = _finite_vec3(b_field, "b_field")
    bnorm = _norm3(bf)
    if bnorm <= B_MIN:
        raise ValueError("magnetic field too weak for a desaturation dipole, |B| = %r" % (bnorm,))
    scale = 1.0 / (bnorm * bnorm)
    bx = _cross(bf, td)
    m = (bx[0] * scale, bx[1] * scale, bx[2] * scale)
    tnorm = _norm3(td)
    if tnorm == 0.0:
        warning = False  # nothing to produce, nothing to warn about
    else:
        sin_angle = _norm3(_cross(td, bf)) / (tnorm * bnorm)
        warning = sin_angle < ALIGN_WARN_SIN
    return m, warning


def run_wheel_control(q0, omega0, q_ref, kp, kd, j_w, h_w0,
                      omega_body_samples, tau_max, h_max, dt, n_steps):
    """Closed loop wheel control acquisition run.

    Integrates the quaternion feedback PD law over n_steps of size dt:
    per step it computes the quaternion error, commands the wheel
    torque, clips it at tau_max, advances the wheel momentum with the
    transport term, checks momentum saturation against h_max, and
    integrates the body rate and attitude. Body dynamics use the
    module spacecraft inertia I_SC with the wheel cluster producing
    the commanded torque on the bus (no external torque), so this is
    the control loop demonstration, not a deep rigid body propagator.

    omega_body_samples may be None (default): the body rate is
    integrated from omega0 (acquisition mode). Otherwise pass n_steps
    body rate vectors (rad/s) to evaluate the commanded torques along a
    given rate profile; the attitude then follows kinematically from
    q0. tau_max and h_max may be scalars or 3D vectors (N m, N m s).

    Returns (history, verdicts): history is a list of per-step dicts
    (t, q, omega_body, h_w, wheel_speed_rad_s, tau_cmd,
    torque_saturated, momentum_saturated, attitude_error_deg);
    verdicts is a dict with torque_saturated, momentum_saturated,
    peak_torque_command (N m), peak_wheel_momentum (N m s),
    peak_wheel_speed_rad_s, final_wheel_momentum, and
    final_attitude_error_deg. Raises ValueError on non-physical or
    non-finite inputs.
    """
    q = _check_quat(q0, "q0")
    qr = _check_quat(q_ref, "q_ref")
    w0 = _finite_vec3(omega0, "omega0")
    hw = _finite_vec3(h_w0, "h_w0")
    if kp <= 0.0 or kd <= 0.0:
        raise ValueError("kp and kd must be > 0, got kp=%r kd=%r" % (kp, kd))
    if j_w <= 0.0:
        raise ValueError("j_w must be > 0, got %r" % (j_w,))
    if dt <= 0.0:
        raise ValueError("dt must be > 0, got %r" % (dt,))
    if not isinstance(n_steps, int) or n_steps <= 0:
        raise ValueError("n_steps must be a positive integer, got %r" % (n_steps,))
    if not math.isfinite(float(kp)) or not math.isfinite(float(kd)) or not math.isfinite(float(j_w)):
        raise ValueError("kp, kd, j_w must be finite")
    # tau_max and h_max validated lazily per step by the helpers.

    sample_mode = omega_body_samples is not None
    if sample_mode:
        samples = [tuple(_finite_vec3(s, "omega_body_samples[%d]" % i))
                   for i, s in enumerate(omega_body_samples)]
        if len(samples) != n_steps:
            raise ValueError(
                "omega_body_samples must hold n_steps=%d rate vectors, got %d"
                % (n_steps, len(samples))
            )
        omega = w0
    else:
        samples = None
        omega = w0

    omega_ref = (0.0, 0.0, 0.0)  # inertial pointing reference
    history = []
    peak_tau = 0.0
    peak_hw = 0.0
    peak_speed = 0.0
    any_tau_sat = False
    any_h_sat = False
    final_err_deg = None

    for k in range(n_steps):
        t = k * dt
        if sample_mode:
            omega = samples[k]
        q_err = quaternion_error(q, qr)
        theta_err = attitude_error_vector(q_err)
        omega_err = (omega[0] - omega_ref[0], omega[1] - omega_ref[1],
                     omega[2] - omega_ref[2])
        tau_raw = pd_wheel_torque(kp, kd, theta_err, omega_err)
        tau_cmd, tau_sat = torque_saturation(tau_raw, tau_max)
        any_tau_sat = any_tau_sat or tau_sat
        hw = wheel_momentum_update(hw, tau_cmd, omega, dt)
        _, h_sat = momentum_saturation(hw, h_max)
        any_h_sat = any_h_sat or h_sat
        # Body rate: the wheel cluster produces tau_cmd about the body
        # axes on the inertially spherical bus (gyroscopic term drops).
        # In rate profile mode the body rate comes from the samples and
        # is not integrated here.
        if not sample_mode:
            omega = (
                omega[0] + tau_cmd[0] / I_SC * dt,
                omega[1] + tau_cmd[1] / I_SC * dt,
                omega[2] + tau_cmd[2] / I_SC * dt,
            )
        # Kinematics with the updated rate.
        qw = _quat_mult(q, (0.0, omega[0], omega[1], omega[2]))
        q = _quat_normalize((
            q[0] + 0.5 * qw[0] * dt,
            q[1] + 0.5 * qw[1] * dt,
            q[2] + 0.5 * qw[2] * dt,
            q[3] + 0.5 * qw[3] * dt,
        ))
        wheel_speeds = (hw[0] / j_w, hw[1] / j_w, hw[2] / j_w)
        err_deg = math.degrees(2.0 * math.atan2(
            math.sqrt(q_err[1] ** 2 + q_err[2] ** 2 + q_err[3] ** 2), q_err[0]))
        peak_tau = max(peak_tau, max(abs(c) for c in tau_cmd))
        peak_hw = max(peak_hw, math.sqrt(hw[0] ** 2 + hw[1] ** 2 + hw[2] ** 2))
        peak_speed = max(peak_speed, max(abs(s) for s in wheel_speeds))
        history.append({
            "t": t,
            "q": q,
            "omega_body": omega,
            "h_w": hw,
            "wheel_speed_rad_s": wheel_speeds,
            "tau_cmd": tau_cmd,
            "torque_saturated": tau_sat,
            "momentum_saturated": h_sat,
            "attitude_error_deg": err_deg,
        })

    q_err_f = quaternion_error(q, qr)
    final_err_deg = math.degrees(2.0 * math.atan2(
        math.sqrt(q_err_f[1] ** 2 + q_err_f[2] ** 2 + q_err_f[3] ** 2), q_err_f[0]))
    verdicts = {
        "torque_saturated": any_tau_sat,
        "momentum_saturated": any_h_sat,
        "peak_torque_command": peak_tau,
        "peak_wheel_momentum": peak_hw,
        "peak_wheel_speed_rad_s": peak_speed,
        "final_wheel_momentum": hw,
        "final_attitude_error_deg": final_err_deg,
    }
    return history, verdicts
