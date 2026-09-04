"""Augmented proportional navigation (APN) guidance for a planar intercept.

Pure stdlib implementation of the augmented proportional navigation law for a
maneuvering target: APN = N' * (Vc * lamdot + a_T_perp / 2), where lamdot is
the planar line-of-sight rate, Vc the closing velocity, a_T_perp the target
lateral acceleration perpendicular to the line of sight, and N' the effective
navigation ratio. The augmentation term (N' / 2) * a_T_perp is the distinct
output of this leaf over the unaugmented proportional navigation law owned by
the proportional-navigation sibling leaf.

All angles in radians, SI units throughout (m, m/s, rad/s, m/s2, s).
Fully deterministic: no stochastic draws, no state, no I/O.
"""

import math

G0 = 9.80665  # standard gravity, m/s2
N_DEFAULT = 4.0  # effective navigation ratio default


def _range_sq(rel_pos_x, rel_pos_y):
    """Squared planar range; raises ValueError on the zero position vector."""
    r_sq = rel_pos_x * rel_pos_x + rel_pos_y * rel_pos_y
    if r_sq == 0.0:
        raise ValueError("zero relative position vector: range is undefined")
    return r_sq


def los_rate(rel_pos_x, rel_pos_y, rel_vel_x, rel_vel_y):
    """Planar line-of-sight rate in rad/s.

    lamdot = (rel_pos_x * rel_vel_y - rel_pos_y * rel_vel_x) / r^2, the
    rotation rate of the interceptor-to-target line. Raises ValueError on the
    zero relative position vector.
    """
    r_sq = _range_sq(rel_pos_x, rel_pos_y)
    return (rel_pos_x * rel_vel_y - rel_pos_y * rel_vel_x) / r_sq


def closing_velocity(rel_pos_x, rel_pos_y, rel_vel_x, rel_vel_y):
    """Closing velocity Vc in m/s.

    Vc = -(rel_pos_x * rel_vel_x + rel_pos_y * rel_vel_y) / r. Positive when
    the range is decreasing (closing), negative for opening geometry and
    passed through unchanged. Raises ValueError on the zero relative position
    vector.
    """
    r_sq = _range_sq(rel_pos_x, rel_pos_y)
    return -(rel_pos_x * rel_vel_x + rel_pos_y * rel_vel_y) / math.sqrt(r_sq)


def pn_command(navigation_ratio, closing_velocity, los_rate):
    """Pure proportional navigation command a_pn = N * Vc * lamdot in m/s2.

    Raises ValueError if navigation_ratio <= 0.
    """
    if navigation_ratio <= 0:
        raise ValueError("navigation_ratio must be > 0")
    return navigation_ratio * closing_velocity * los_rate


def apn_command(navigation_ratio, closing_velocity, los_rate,
                target_lateral_accel):
    """Augmented proportional navigation command in m/s2.

    a_apn = N * (Vc * lamdot + a_T_perp / 2), with a_T_perp the target lateral
    acceleration perpendicular to the line of sight (any sign allowed).
    Raises ValueError if navigation_ratio <= 0.
    """
    if navigation_ratio <= 0:
        raise ValueError("navigation_ratio must be > 0")
    return navigation_ratio * (
        closing_velocity * los_rate + target_lateral_accel / 2.0
    )


def commanded_accel_g(accel_m_s2):
    """Commanded acceleration in g: accel / G0."""
    return accel_m_s2 / G0


def time_to_go(range_m, closing_velocity):
    """Time to go estimate t_go = range / Vc in seconds.

    Raises ValueError if range_m < 0 or closing_velocity <= 0.
    """
    if range_m < 0:
        raise ValueError("range_m must be >= 0")
    if closing_velocity <= 0:
        raise ValueError("closing_velocity must be > 0 for time to go")
    return range_m / closing_velocity


def apn_assessment(rel_pos_x, rel_pos_y, rel_vel_x, rel_vel_y,
                   target_lateral_accel, navigation_ratio=N_DEFAULT,
                   range_m=None):
    """Convenience chain for a planar augmented-PN intercept assessment.

    Returns a dict with exactly the keys los_rate, closing_velocity,
    pn_command_m_s2, apn_command_m_s2, pn_command_g, apn_command_g and
    time_to_go_s (None when range_m is None).
    """
    lamdot = los_rate(rel_pos_x, rel_pos_y, rel_vel_x, rel_vel_y)
    vc = closing_velocity(rel_pos_x, rel_pos_y, rel_vel_x, rel_vel_y)
    a_pn = pn_command(navigation_ratio, vc, lamdot)
    a_apn = apn_command(navigation_ratio, vc, lamdot, target_lateral_accel)
    return {
        "los_rate": lamdot,
        "closing_velocity": vc,
        "pn_command_m_s2": a_pn,
        "apn_command_m_s2": a_apn,
        "pn_command_g": commanded_accel_g(a_pn),
        "apn_command_g": commanded_accel_g(a_apn),
        "time_to_go_s": time_to_go(range_m, vc) if range_m is not None else None,
    }
