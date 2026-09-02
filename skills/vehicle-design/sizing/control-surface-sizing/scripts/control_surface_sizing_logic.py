#!/usr/bin/env python3
"""Control surface sizing logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): conceptual control surface sizing sizes the aileron, the
elevator, and the rudder from control power requirements. The aileron
is sized so the rolling moment derivative C_l_delta_a with the
maximum deflection produces the target steady roll rate against the
roll damping derivative C_l_p. The elevator is sized so the pitching
moment derivative C_m_delta_e with the maximum deflection covers the
required pitch moment change, and the rudder is sized so the yawing
moment derivative C_n_delta_r with the maximum deflection covers the
required yaw moment (typically the engine-out case). The rolling
moment derivative follows from the aileron geometry: C_l_delta_a =
2 * tau_a * C_L_alpha_w * y_a * S_a / (S_w * b), with tau_a the
aileron effectiveness, C_L_alpha_w the wing lift curve slope, y_a the
spanwise centroid of the aileron, S_a the total aileron area (both
wings), S_w the wing reference area, and b the span. The elevator
pitch derivative follows from the tail: C_m_delta_e = -eta_t * V_H *
C_L_alpha_t * tau_e, with eta_t the tail dynamic pressure ratio, V_H
the horizontal tail volume coefficient, C_L_alpha_t the tail lift
curve slope, and tau_e the elevator effectiveness. The rudder yaw
derivative follows from the vertical tail: C_n_delta_r = -eta_v *
V_V * C_L_alpha_v * tau_r. The hinge moment for actuator sizing is
H = C_h * q * S_surf * c_surf, with C_h the hinge moment coefficient,
q the dynamic pressure, S_surf the control surface area, and c_surf
its mean chord. Typical deflection limits are about +/-25 deg for the
aileron, +25/-15 deg for the elevator (trailing edge down positive),
and +/-30 deg for the rudder.

Units are SI throughout: areas in m^2, lengths in m, speeds in m/s,
dynamic pressure in Pa, moments in N m, angles in rad (deg where
noted), derivatives per radian. Invalid inputs raise ValueError
throughout.
"""


def roll_rate_achieved(c_l_delta, delta, v, b, c_l_p):
    """Steady-state roll rate (rad/s) for a given aileron deflection.

    p = -2 * V * C_l_delta * delta / (b * C_l_p), the balance of the
    rolling moment from the aileron against the roll damping moment.
    C_l_p is negative for a stable wing, so a positive C_l_delta and
    delta give a positive roll rate. Worked anchor: C_l_delta = 0.1032,
    delta = 0.436 rad, V = 85 m/s, b = 34 m, C_l_p = -0.45 gives
    p = -2*85*0.1032*0.436/(34*(-0.45)) = 0.4999 rad/s.

    Raises ValueError if c_l_delta, delta, v, b are not positive or
    if c_l_p is not negative.
    """
    if c_l_delta <= 0:
        raise ValueError("c_l_delta must be positive, got %r" % (c_l_delta,))
    if delta <= 0:
        raise ValueError("delta must be positive, got %r" % (delta,))
    if v <= 0:
        raise ValueError("v must be positive, got %r" % (v,))
    if b <= 0:
        raise ValueError("b must be positive, got %r" % (b,))
    if c_l_p >= 0:
        raise ValueError("c_l_p must be negative (roll damping), got %r" % (c_l_p,))
    return -2.0 * v * c_l_delta * delta / (b * c_l_p)


def aileron_control_derivative(s_a, tau, c_l_alpha, y_a, s_w, b):
    """Rolling moment derivative C_l_delta_a (per rad) from geometry.

    C_l_delta_a = 2 * tau * C_L_alpha * y_a * S_a / (S_w * b), with
    S_a the total aileron area of both wings (m^2), tau the aileron
    effectiveness (0 < tau < 1), C_L_alpha the wing lift curve slope
    (per rad), y_a the spanwise centroid of the aileron (m), S_w the
    wing reference area (m^2), and b the span (m). Worked anchor:
    S_a = 5.67 m^2, tau = 0.5, C_L_alpha = 5.5, y_a = 13.5 m,
    S_w = 120 m^2, b = 34 m gives C_l_delta_a = 2*0.5*5.5*13.5*5.67/
    (120*34) = 0.1032 per rad.

    Raises ValueError if any input is not positive.
    """
    if s_a <= 0:
        raise ValueError("s_a must be positive, got %r" % (s_a,))
    if tau <= 0 or tau >= 1:
        raise ValueError("tau must be in (0, 1), got %r" % (tau,))
    if c_l_alpha <= 0:
        raise ValueError("c_l_alpha must be positive, got %r" % (c_l_alpha,))
    if y_a <= 0:
        raise ValueError("y_a must be positive, got %r" % (y_a,))
    if s_w <= 0:
        raise ValueError("s_w must be positive, got %r" % (s_w,))
    if b <= 0:
        raise ValueError("b must be positive, got %r" % (b,))
    return 2.0 * tau * c_l_alpha * y_a * s_a / (s_w * b)


def aileron_area_required(p_req, v, b, c_l_p, delta_max, tau, c_l_alpha, y_a, s_w):
    """Required total aileron area (m^2, both wings) for a target roll rate.

    Inverts the steady roll rate balance: the required derivative is
    C_l_delta = -p_req * b * C_l_p / (2 * V * delta_max), then the
    required area is S_a = C_l_delta * S_w * b / (2 * tau *
    C_L_alpha * y_a). p_req is the target roll rate (rad/s), V the
    maneuvering speed (m/s), b the span (m), C_l_p the roll damping
    derivative (negative, per rad), delta_max the maximum aileron
    deflection (rad), tau the aileron effectiveness, C_L_alpha the
    wing lift curve slope (per rad), y_a the aileron spanwise centroid
    (m), S_w the wing reference area (m^2). Worked anchor: p_req =
    0.5 rad/s, V = 85 m/s, b = 34 m, C_l_p = -0.45, delta_max =
    0.436 rad, tau = 0.5, C_L_alpha = 5.5, y_a = 13.5 m, S_w =
    120 m^2 gives S_a = 5.6714 m^2 (about 2.84 m^2 per aileron).

    Raises ValueError on invalid inputs; c_l_p must be negative.
    """
    if p_req <= 0:
        raise ValueError("p_req must be positive, got %r" % (p_req,))
    if v <= 0:
        raise ValueError("v must be positive, got %r" % (v,))
    if b <= 0:
        raise ValueError("b must be positive, got %r" % (b,))
    if c_l_p >= 0:
        raise ValueError("c_l_p must be negative (roll damping), got %r" % (c_l_p,))
    if delta_max <= 0:
        raise ValueError("delta_max must be positive, got %r" % (delta_max,))
    if tau <= 0 or tau >= 1:
        raise ValueError("tau must be in (0, 1), got %r" % (tau,))
    if c_l_alpha <= 0:
        raise ValueError("c_l_alpha must be positive, got %r" % (c_l_alpha,))
    if y_a <= 0:
        raise ValueError("y_a must be positive, got %r" % (y_a,))
    if s_w <= 0:
        raise ValueError("s_w must be positive, got %r" % (s_w,))
    c_l_delta = -p_req * b * c_l_p / (2.0 * v * delta_max)
    return c_l_delta * s_w * b / (2.0 * tau * c_l_alpha * y_a)


def elevator_pitch_derivative(eta_t, v_h, c_l_alpha_t, tau_e):
    """Pitching moment derivative C_m_delta_e (per rad) from the tail.

    C_m_delta_e = -eta_t * V_H * C_L_alpha_t * tau_e, with eta_t the
    tail dynamic pressure ratio, V_H the horizontal tail volume
    coefficient, C_L_alpha_t the horizontal tail lift curve slope
    (per rad), and tau_e the elevator effectiveness. Negative for an
    aft tail: a trailing-edge-down elevator deflection produces a
    nose-up moment. Worked anchor: eta_t = 0.9, V_H = 0.7,
    C_L_alpha_t = 4.5, tau_e = 0.6 gives C_m_delta_e = -0.9*0.7*4.5*0.6
    = -1.701 per rad.

    Raises ValueError if any input is not positive.
    """
    if eta_t <= 0:
        raise ValueError("eta_t must be positive, got %r" % (eta_t,))
    if v_h <= 0:
        raise ValueError("v_h must be positive, got %r" % (v_h,))
    if c_l_alpha_t <= 0:
        raise ValueError("c_l_alpha_t must be positive, got %r" % (c_l_alpha_t,))
    if tau_e <= 0 or tau_e >= 1:
        raise ValueError("tau_e must be in (0, 1), got %r" % (tau_e,))
    return -eta_t * v_h * c_l_alpha_t * tau_e


def elevator_area_required(c_m_req, s_t, eta_t, v_h, c_l_alpha_t, tau_e, delta_max):
    """Required elevator area (m^2) for a pitch moment requirement.

    S_e = C_m_req * S_t / (eta_t * V_H * C_L_alpha_t * tau_e *
    delta_max), with C_m_req the nose-up pitch moment coefficient the
    elevator must provide (unitless, positive), S_t the horizontal
    tail area (m^2), eta_t the tail dynamic pressure ratio, V_H the
    horizontal tail volume coefficient, C_L_alpha_t the tail lift
    curve slope (per rad), tau_e the elevator effectiveness, and
    delta_max the maximum elevator deflection (rad). Worked anchor:
    C_m_req = 0.22, S_t = 21 m^2, eta_t = 0.9, V_H = 0.7,
    C_L_alpha_t = 4.5, tau_e = 0.6, delta_max = 0.436 rad gives
    S_e = 0.22*21/(0.9*0.7*4.5*0.6*0.436) = 6.2295 m^2, about 30% of
    the horizontal tail area.

    Raises ValueError on invalid inputs.
    """
    if c_m_req <= 0:
        raise ValueError("c_m_req must be positive, got %r" % (c_m_req,))
    if s_t <= 0:
        raise ValueError("s_t must be positive, got %r" % (s_t,))
    if eta_t <= 0:
        raise ValueError("eta_t must be positive, got %r" % (eta_t,))
    if v_h <= 0:
        raise ValueError("v_h must be positive, got %r" % (v_h,))
    if c_l_alpha_t <= 0:
        raise ValueError("c_l_alpha_t must be positive, got %r" % (c_l_alpha_t,))
    if tau_e <= 0 or tau_e >= 1:
        raise ValueError("tau_e must be in (0, 1), got %r" % (tau_e,))
    if delta_max <= 0:
        raise ValueError("delta_max must be positive, got %r" % (delta_max,))
    return c_m_req * s_t / (eta_t * v_h * c_l_alpha_t * tau_e * delta_max)


def rudder_yaw_derivative(eta_v, v_v, c_l_alpha_v, tau_r):
    """Yawing moment derivative C_n_delta_r (per rad) from the tail.

    C_n_delta_r = -eta_v * V_V * C_L_alpha_v * tau_r, with eta_v the
    vertical tail dynamic pressure ratio, V_V the vertical tail volume
    coefficient, C_L_alpha_v the vertical tail lift curve slope (per
    rad), and tau_r the rudder effectiveness. Negative for a
    conventional aft fin: a right rudder deflection produces a
    nose-right yawing moment. Worked anchor: eta_v = 0.9, V_V = 0.06,
    C_L_alpha_v = 3.5, tau_r = 0.6 gives C_n_delta_r = -0.9*0.06*3.5*0.6
    = -0.1134 per rad.

    Raises ValueError if any input is not positive.
    """
    if eta_v <= 0:
        raise ValueError("eta_v must be positive, got %r" % (eta_v,))
    if v_v <= 0:
        raise ValueError("v_v must be positive, got %r" % (v_v,))
    if c_l_alpha_v <= 0:
        raise ValueError("c_l_alpha_v must be positive, got %r" % (c_l_alpha_v,))
    if tau_r <= 0 or tau_r >= 1:
        raise ValueError("tau_r must be in (0, 1), got %r" % (tau_r,))
    return -eta_v * v_v * c_l_alpha_v * tau_r


def rudder_area_required(c_n_req, s_v, eta_v, v_v, c_l_alpha_v, tau_r, delta_max):
    """Required rudder area (m^2) for a yaw moment requirement.

    S_r = C_n_req * S_v / (eta_v * V_V * C_L_alpha_v * tau_r *
    delta_max), with C_n_req the yawing moment coefficient the rudder
    must provide (unitless, positive), S_v the vertical tail area
    (m^2), eta_v the vertical tail dynamic pressure ratio, V_V the
    vertical tail volume coefficient, C_L_alpha_v the vertical tail
    lift curve slope (per rad), tau_r the rudder effectiveness, and
    delta_max the maximum rudder deflection (rad). The requirement
    usually comes from the engine-out asymmetric thrust case. Worked
    anchor: C_n_req = 0.022, S_v = 18.83 m^2, eta_v = 0.9, V_V =
    0.06, C_L_alpha_v = 3.5, tau_r = 0.6, delta_max = 0.524 rad gives
    S_r = 0.022*18.83/(0.9*0.06*3.5*0.6*0.524) = 6.9715 m^2, about
    37% of the vertical tail area.

    Raises ValueError on invalid inputs.
    """
    if c_n_req <= 0:
        raise ValueError("c_n_req must be positive, got %r" % (c_n_req,))
    if s_v <= 0:
        raise ValueError("s_v must be positive, got %r" % (s_v,))
    if eta_v <= 0:
        raise ValueError("eta_v must be positive, got %r" % (eta_v,))
    if v_v <= 0:
        raise ValueError("v_v must be positive, got %r" % (v_v,))
    if c_l_alpha_v <= 0:
        raise ValueError("c_l_alpha_v must be positive, got %r" % (c_l_alpha_v,))
    if tau_r <= 0 or tau_r >= 1:
        raise ValueError("tau_r must be in (0, 1), got %r" % (tau_r,))
    if delta_max <= 0:
        raise ValueError("delta_max must be positive, got %r" % (delta_max,))
    return c_n_req * s_v / (eta_v * v_v * c_l_alpha_v * tau_r * delta_max)


def control_power(c_derivative, delta_max):
    """Control power magnitude (unitless) of a control derivative.

    |C_delta| * delta_max, the maximum dimensionless moment the
    control surface can produce at its deflection limit. c_derivative
    is the moment derivative in per rad (positive or negative), and
    delta_max the maximum deflection in rad. Worked anchor: C_m_delta_e
    = -1.701 per rad with delta_max = 0.436 rad gives control power
    0.7416, which covers the C_m_req = 0.22 pitch moment requirement.

    Raises ValueError if delta_max is not positive.
    """
    if delta_max <= 0:
        raise ValueError("delta_max must be positive, got %r" % (delta_max,))
    return abs(c_derivative) * delta_max


def hinge_moment(c_h, q, s_surf, c_surf):
    """Hinge moment (N m) for actuator sizing.

    H = C_h * q * S_surf * c_surf, with C_h the hinge moment
    coefficient (unitless, sign follows the deflection), q the dynamic
    pressure (Pa), S_surf the control surface area (m^2), and c_surf
    the mean chord of the control surface (m). Worked anchor: C_h =
    0.1526, q = 4425.31 Pa (85 m/s at sea level), S_surf = 6.22 m^2,
    c_surf = 0.35 m gives H = 0.1526*4425.31*6.22*0.35 = 1470.13 N m.

    Raises ValueError if any input is not positive.
    """
    if c_h <= 0:
        raise ValueError("c_h must be positive, got %r" % (c_h,))
    if q <= 0:
        raise ValueError("q must be positive, got %r" % (q,))
    if s_surf <= 0:
        raise ValueError("s_surf must be positive, got %r" % (s_surf,))
    if c_surf <= 0:
        raise ValueError("c_surf must be positive, got %r" % (c_surf,))
    return c_h * q * s_surf * c_surf


def deflection_limit_check(deflection_deg, lower_deg, upper_deg):
    """Check a deflection (deg) against its travel limits (deg).

    Returns {"within": bool, "margin_deg": float, "verdict": str}.
    margin_deg is the smaller distance to either limit, positive when
    within the band and negative when outside. Typical limits: aileron
    +/-25 deg, elevator +25/-15 deg (trailing edge down positive),
    rudder +/-30 deg. Worked anchor: elevator deflection 20 deg against
    the [-15, 25] band is within with margin 5 deg; 26 deg is outside
    with margin -1 deg.

    Raises ValueError if lower_deg >= upper_deg.
    """
    if lower_deg >= upper_deg:
        raise ValueError(
            "lower_deg must be below upper_deg, got %r >= %r"
            % (lower_deg, upper_deg)
        )
    within = lower_deg <= deflection_deg <= upper_deg
    margin = min(deflection_deg - lower_deg, upper_deg - deflection_deg)
    if within:
        verdict = "deflection within limits, margin %g deg" % margin
    elif deflection_deg < lower_deg:
        verdict = "deflection below lower limit by %g deg" % (-margin)
    else:
        verdict = "deflection above upper limit by %g deg" % (-margin)
    return {"within": within, "margin_deg": margin, "verdict": verdict}
