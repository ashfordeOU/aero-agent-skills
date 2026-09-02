"""Control surface effectiveness and hinge moment math for fixed-wing airplanes.

Deterministic, offline, stdlib-only helpers for elevator authority and
hinge moment requirements: dynamic pressure, the hinge moment
coefficient from the tab and angle derivative terms, the hinge moment
from the elevator area and chord, the stick force from the gearing arm,
the tail volume coefficient and the elevator pitching moment
derivative, the elevator deflection required to trim and to reach a
maneuver load factor, the authority margin against the maximum
deflection, and the net pitch-up moment about the main gear for the
takeoff rotation check.

All units are SI: speeds in m/s, densities in kg/m^3, dynamic pressure
in Pa, forces and weights in N, moments in N m, areas in m^2, chords
and arms in m, angles in radians. Elevator deflection is positive
trailing edge down; a negative deflection produces tail download.

Contract exercised by scripts/test_control_surface_effectiveness.py.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2
STD_DENSITY = 1.225  # sea level ISA air density, kg/m^3


def dynamic_pressure(rho, v):
    """Return the dynamic pressure q = 0.5 * rho * V^2 in Pa.

    Anchor: dynamic_pressure(1.225, 70.0) = 3001.25 Pa (70 m/s at sea
    level ISA).

    Raises ValueError for a non-positive density or speed.
    """
    if rho <= 0:
        raise ValueError("density must be > 0, got %r" % (rho,))
    if v <= 0:
        raise ValueError("speed must be > 0, got %r" % (v,))
    return 0.5 * rho * v * v


def hinge_moment_coefficient(c_h0, c_h_alpha, alpha_t, c_h_delta, delta_e):
    """Return the elevator hinge moment coefficient C_h (dimensionless).

    C_h = C_h0 + C_h_alpha * alpha_t + C_h_delta * delta_e, with
    alpha_t the tailplane angle of attack in radians and delta_e the
    elevator deflection in radians (positive trailing edge down). C_h0
    is the tab-fixed zero term and C_h_alpha / C_h_delta are the hinge
    moment derivatives per radian; a negative C_h_delta means the hinge
    moment opposes the deflection, which is the balancing-tab design
    goal.

    Anchor: hinge_moment_coefficient(0.02, 0.25, 0.15, 0.50, 0.30) =
    0.2075.

    Raises ValueError when alpha_t or delta_e is not a finite number.
    """
    if not math.isfinite(alpha_t):
        raise ValueError("tail angle of attack must be finite, got %r" % (alpha_t,))
    if not math.isfinite(delta_e):
        raise ValueError("elevator deflection must be finite, got %r" % (delta_e,))
    return c_h0 + c_h_alpha * alpha_t + c_h_delta * delta_e


def hinge_moment(c_h, q, s_e, c_e):
    """Return the elevator hinge moment H = C_h * q * S_e * c_e in N m.

    S_e is the elevator area in m^2 and c_e the elevator mean chord in
    m; q is the dynamic pressure in Pa.

    Anchor: hinge_moment(0.2075, 3001.25, 1.2, 0.4) = 298.9245 N m.

    Raises ValueError for a negative dynamic pressure, area, or chord.
    """
    if q < 0:
        raise ValueError("dynamic pressure must be >= 0, got %r" % (q,))
    if s_e <= 0:
        raise ValueError("elevator area must be > 0, got %r" % (s_e,))
    if c_e <= 0:
        raise ValueError("elevator chord must be > 0, got %r" % (c_e,))
    return c_h * q * s_e * c_e


def stick_force(hinge_moment_value, gear_arm):
    """Return the stick force P = H / L_gear in N from the hinge moment.

    L_gear is the effective gearing arm in m (stick travel per elevator
    travel scaled to force); a longer arm reduces the stick force for a
    given hinge moment.

    Anchor: stick_force(298.9245, 0.35) = 854.07 N.

    Raises ValueError for a non-positive gearing arm.
    """
    if gear_arm <= 0:
        raise ValueError("gearing arm must be > 0, got %r" % (gear_arm,))
    return hinge_moment_value / gear_arm


def stick_force_limit_check(stick_force_value, limit):
    """Return True when the stick force stays within the controllability
    limit.

    The FAR 25.143 / CS 25.143 controllability assessment requires the
    limit maneuver to be achievable without excessive control force;
    the classical transport gate is on the order of 222 N (50 lbf) for
    the longitudinal control at the limit load factor. Returns a
    boolean verdict, limit in N.

    Anchor: stick_force_limit_check(854.07, 222.4) = False;
    stick_force_limit_check(180.0, 222.4) = True.

    Raises ValueError for a non-positive limit.
    """
    if limit <= 0:
        raise ValueError("stick force limit must be > 0, got %r" % (limit,))
    return stick_force_value <= limit


def tail_volume_coefficient(l_t, s_t, s, c_bar):
    """Return the horizontal tail volume coefficient V_H (dimensionless).

    V_H = l_t * S_t / (S * c_bar), with l_t the tail moment arm from
    the aerodynamic center to the tail aerodynamic center in m, S_t the
    tailplane area in m^2, S the wing area in m^2, and c_bar the wing
    mean aerodynamic chord in m.

    Anchor: tail_volume_coefficient(12.0, 9.0, 50.0, 2.1) = 1.0285714.

    Raises ValueError for a non-positive arm, area, wing area, or chord.
    """
    if l_t <= 0:
        raise ValueError("tail moment arm must be > 0, got %r" % (l_t,))
    if s_t <= 0:
        raise ValueError("tailplane area must be > 0, got %r" % (s_t,))
    if s <= 0:
        raise ValueError("wing area must be > 0, got %r" % (s,))
    if c_bar <= 0:
        raise ValueError("mean chord must be > 0, got %r" % (c_bar,))
    return l_t * s_t / (s * c_bar)


def elevator_pitching_derivative(v_h, c_l_delta_e, eta_t=1.0):
    """Return the elevator pitching moment derivative C_m_delta in per
    radian.

    C_m_delta = -eta_t * V_H * C_L_delta_e, with eta_t the tailplane
    dynamic pressure ratio (about 0.9 to 1.0) and C_L_delta_e the tail
    lift curve slope with elevator deflection in per radian. The
    derivative is negative for an aft tail: a positive (trailing edge
    down) deflection produces a nose-down moment.

    Anchor: elevator_pitching_derivative(1.0285714, 0.9, 1.0) =
    -0.9257143.

    Raises ValueError for a non-positive tail volume coefficient,
    C_L_delta_e, or tailplane efficiency.
    """
    if v_h <= 0:
        raise ValueError("tail volume coefficient must be > 0, got %r" % (v_h,))
    if c_l_delta_e <= 0:
        raise ValueError("C_L_delta_e must be > 0, got %r" % (c_l_delta_e,))
    if eta_t <= 0:
        raise ValueError("tailplane efficiency must be > 0, got %r" % (eta_t,))
    return -eta_t * v_h * c_l_delta_e


def trim_elevator_deflection(c_m0, c_m_alpha, alpha, c_m_delta):
    """Return the elevator deflection in radians that trims the pitching
    moment to zero.

    delta_e = -(C_m0 + C_m_alpha * alpha) / C_m_delta, with alpha the
    angle of attack in radians and C_m_delta the elevator pitching
    moment derivative per radian. A negative answer means trailing edge
    up, the usual trim setting for an aft-tailed airplane.

    Anchor: trim_elevator_deflection(0.05, -0.8, 0.1, -0.9257143) =
    -0.0324074 rad.

    Raises ValueError for a zero pitching derivative.
    """
    if c_m_delta == 0:
        raise ValueError("C_m_delta must be non-zero, got 0")
    return -(c_m0 + c_m_alpha * alpha) / c_m_delta


def maneuver_elevator_deflection(c_m0, c_m_alpha, c_l_alpha, c_l_1g, n, c_m_delta):
    """Return the elevator deflection in radians needed to hold the
    maneuver load factor n.

    The angle of attack at the maneuver is alpha = n * C_L_1g /
    C_L_alpha (linear lift curve), and the deflection follows the trim
    closure delta_e = -(C_m0 + C_m_alpha * alpha) / C_m_delta. The
    limit load factor of 2.5 is the FAR 25.143 / CS 25.143 controlla-
    bility gate.

    Anchor: maneuver_elevator_deflection(0.05, -0.8, 5.5, 0.5, 2.5,
    -0.9257143) = -0.1423962 rad.

    Raises ValueError for a load factor below 1, or a non-positive
    lift curve slope or 1g lift coefficient.
    """
    if c_l_alpha <= 0:
        raise ValueError("lift curve slope must be > 0, got %r" % (c_l_alpha,))
    if c_l_1g <= 0:
        raise ValueError("1g lift coefficient must be > 0, got %r" % (c_l_1g,))
    if n < 1.0:
        raise ValueError("load factor must be >= 1, got %r" % (n,))
    if c_m_delta == 0:
        raise ValueError("C_m_delta must be non-zero, got 0")
    alpha_man = n * c_l_1g / c_l_alpha
    return -(c_m0 + c_m_alpha * alpha_man) / c_m_delta


def authority_margin(delta_max, delta_required):
    """Return the elevator authority margin in radians.

    margin = delta_max - abs(delta_required), the deflection reserve
    before the control saturates at its mechanical stop. Negative means
    the required deflection exceeds the available travel.

    Anchor: authority_margin(0.35, -0.0324074) = 0.3175926 rad.

    Raises ValueError for a non-positive maximum deflection.
    """
    if delta_max <= 0:
        raise ValueError("maximum deflection must be > 0, got %r" % (delta_max,))
    return delta_max - abs(delta_required)


def rotation_net_moment(tail_download, tail_arm, weight, cg_to_gear):
    """Return the net pitch-up moment about the main gear in N m.

    M = L_t_down * l_t - W * x_cg, with L_t_down the tail download in N
    (positive downward), l_t the tail to main gear moment arm in m,
    W the takeoff weight in N, and x_cg the CG distance ahead of the
    main gear in m (positive). Positive means the elevator can rotate
    the airplane nose up at the lift-off speed.

    Anchor: rotation_net_moment(8000.0, 12.0, 30000.0, 0.5) =
    81000.0 N m.

    Raises ValueError for a negative tail download, or a non-positive
    arm, weight, or CG arm.
    """
    if tail_download < 0:
        raise ValueError("tail download must be >= 0, got %r" % (tail_download,))
    if tail_arm <= 0:
        raise ValueError("tail moment arm must be > 0, got %r" % (tail_arm,))
    if weight <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight,))
    if cg_to_gear <= 0:
        raise ValueError("CG to gear distance must be > 0, got %r" % (cg_to_gear,))
    return tail_download * tail_arm - weight * cg_to_gear


def rotation_authority_check(net_moment, margin=0.0):
    """Return True when the net pitch-up moment about the main gear
    exceeds the rotation margin.

    The elevator authority is adequate when the tail download moment
    overcomes the nose-down weight moment about the gear with the
    required margin (N m, default zero).

    Anchor: rotation_authority_check(81000.0) = True;
    rotation_authority_check(-5000.0) = False.

    Raises ValueError for a negative margin.
    """
    if margin < 0:
        raise ValueError("rotation margin must be >= 0, got %r" % (margin,))
    return net_moment > margin
