#!/usr/bin/env python3
"""Load factor envelope (V-n diagram) logic for flight test (paraphrase,
common knowledge).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: public
domain / free-download regulation context): the V-n diagram bounds the
flight envelope with the stall speed boundary V_s = sqrt(2 n W/S /
(rho CL_max)), the corner point V_A at the positive limit load factor,
the discrete gust line increment in the FAR 25.341 form, and the
placard speed cap. Transport positive and negative limit maneuvering
load factors are 2.5 and -1.0 (FAR 25.337 / CS-25.337 context). All
values are SI (m/s, Pa, kg/m^3) unless the mixed-unit FAR 25.341 form
is used explicitly.
"""

import math

SEA_LEVEL_DENSITY = 1.225  # kg/m^3
# 2 / (rho_ssl * 1.68781): the sea level density constant of the FAR
# 25.341 mixed-unit gust formula (U_de in ft/s, V_eas in knots).
FAR_GUST_CONSTANT = 498.0
TRANSPORT_POSITIVE_LIMIT = 2.5
TRANSPORT_NEGATIVE_LIMIT = -1.0


def stall_speed_boundary(wing_loading, cl_max, load_factor, rho):
    """Stall speed boundary of the V-n diagram, m/s EAS.

    V_s = sqrt(2 n W/S / (rho CL_max)) with wing_loading W/S in Pa
    (N/m^2), cl_max dimensionless, load_factor n dimensionless, and
    rho in kg/m^3. Raises ValueError when any input is non-positive.
    """
    if wing_loading <= 0:
        raise ValueError("wing loading must be > 0, got %r" % (wing_loading,))
    if cl_max <= 0:
        raise ValueError("maximum lift coefficient must be > 0, got %r" % (cl_max,))
    if load_factor <= 0:
        raise ValueError("load factor must be > 0, got %r" % (load_factor,))
    if rho <= 0:
        raise ValueError("air density must be > 0, got %r" % (rho,))
    return math.sqrt(2.0 * load_factor * wing_loading / (rho * cl_max))


def corner_speed(wing_loading, cl_max, limit_load_factor, rho):
    """Corner point (maneuvering speed VA), m/s EAS.

    The stall speed boundary evaluated at n = limit_load_factor.
    Raises ValueError when limit_load_factor <= 1 (a limit below 1 g
    makes the corner point meaningless).
    """
    if limit_load_factor <= 1:
        raise ValueError(
            "limit load factor must be > 1, got %r" % (limit_load_factor,)
        )
    return stall_speed_boundary(wing_loading, cl_max, limit_load_factor, rho)


def _check_gust_inputs(k_g, u_de, v_eas, lift_curve_slope, wing_loading):
    if k_g <= 0:
        raise ValueError("gust alleviation factor must be > 0, got %r" % (k_g,))
    if u_de < 0:
        raise ValueError("gust velocity must be >= 0, got %r" % (u_de,))
    if v_eas <= 0:
        raise ValueError("equivalent airspeed must be > 0, got %r" % (v_eas,))
    if lift_curve_slope <= 0:
        raise ValueError("lift curve slope must be > 0, got %r" % (lift_curve_slope,))
    if wing_loading <= 0:
        raise ValueError("wing loading must be > 0, got %r" % (wing_loading,))


def gust_load_factor_increment(k_g, u_de, v_eas, lift_curve_slope, wing_loading):
    """Discrete gust load factor increment, dimensionless (FAR 25.341 form).

    delta_n = k_g * U_de * V_eas * a / (498 * W/S) with U_de in ft/s
    EAS, V_eas in knots EAS, lift_curve_slope a per radian, and W/S in
    lb/ft^2; 498 is the sea level density constant of the certification
    formula. For SI input use gust_load_factor_increment_si instead.
    Raises ValueError when k_g <= 0, u_de < 0, v_eas <= 0,
    lift_curve_slope <= 0, or wing_loading <= 0.
    """
    _check_gust_inputs(k_g, u_de, v_eas, lift_curve_slope, wing_loading)
    return k_g * u_de * v_eas * lift_curve_slope / (FAR_GUST_CONSTANT * wing_loading)


def gust_load_factor_increment_si(k_g, rho, u_de, v_eas, lift_curve_slope,
                                  wing_loading):
    """Discrete gust load factor increment in SI units, dimensionless.

    delta_n = k_g * rho * U_de * V_eas * a / (2 * W/S) with rho in
    kg/m^3, U_de and V_eas in m/s EAS, a per radian, and W/S in Pa.
    The SI form of the FAR 25.341 gust increment. Raises ValueError
    when rho <= 0 or any shared gust input is invalid.
    """
    if rho <= 0:
        raise ValueError("air density must be > 0, got %r" % (rho,))
    _check_gust_inputs(k_g, u_de, v_eas, lift_curve_slope, wing_loading)
    return k_g * rho * u_de * v_eas * lift_curve_slope / (2.0 * wing_loading)


def envelope_verdict(corner_speed_mps, placard_vne, gust_increment,
                     positive_limit, negative_limit):
    """Sanity verdicts for the load factor envelope, dict of bools.

    Checks: the corner point stays below the placard never-exceed
    speed; the gust line (1 + increment at the design speed) stays
    below the positive limit load factor; and the positive/negative
    limit maneuvering load factors match the transport values
    (+2.5 / -1.0). 'ok' is True only when every check passes.
    Raises ValueError on corner_speed_mps <= 0, placard_vne <= 0,
    gust_increment < 0, positive_limit <= 1, or negative_limit >= 0.
    """
    if corner_speed_mps <= 0:
        raise ValueError("corner speed must be > 0, got %r" % (corner_speed_mps,))
    if placard_vne <= 0:
        raise ValueError(
            "placard never-exceed speed must be > 0, got %r" % (placard_vne,)
        )
    if gust_increment < 0:
        raise ValueError("gust increment must be >= 0, got %r" % (gust_increment,))
    if positive_limit <= 1:
        raise ValueError(
            "positive limit load factor must be > 1, got %r" % (positive_limit,)
        )
    if negative_limit >= 0:
        raise ValueError(
            "negative limit load factor must be < 0, got %r" % (negative_limit,)
        )
    corner_within_placard = corner_speed_mps < placard_vne
    gust_within_maneuver = 1.0 + gust_increment <= positive_limit
    transport_limits_ok = math.isclose(
        positive_limit, TRANSPORT_POSITIVE_LIMIT, rel_tol=0.0, abs_tol=1e-9
    ) and math.isclose(
        negative_limit, TRANSPORT_NEGATIVE_LIMIT, rel_tol=0.0, abs_tol=1e-9
    )
    return {
        "corner_within_placard": corner_within_placard,
        "gust_within_maneuver": gust_within_maneuver,
        "transport_limits_ok": transport_limits_ok,
        "ok": corner_within_placard and gust_within_maneuver and transport_limits_ok,
    }
