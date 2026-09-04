"""Constant-bearing collision course guidance geometry (2D plane, degrees).

Pure stdlib implementation of the collision-course intercept triangle for a
constant-speed pursuer against a constant-velocity target: the lead angle LA
that puts the pursuer on a collision triangle with the target, the closing
speed along the line of sight, the time to go to the predicted intercept
point, the intercept point coordinates, and the bearing-error check against
the current pursuer heading.

Heading convention (recorded assumption, per the leaf spec): los_to_target
angle is the direction of the pursuer-to-target line of sight and the target
heading is the direction of the target velocity, both plane headings in
degrees in the same frame.  beta = wrap180(target_heading - los) is the signed
angle between the target velocity vector and the line of sight on the closing
side of the triangle: beta = 0 is the head-on closing geometry where the
target flies straight at the pursuer, the lead angle vanishes, and the closing
speed is Vp + Vt.  On the constant-bearing collision triangle the target
closes the range along the LOS at Vt * cos(beta) while the pursuer leads the
LOS by LA toward the target's flight side, so the LOS does not rotate
(Vp * sin(LA) = Vt * sin(beta)) and both vehicles meet at the intercept point
after t_go.  No RNG, no state, no I/O: run-to-run identical floats.

Units: m, m/s, s; angles in degrees.  All module angles are degrees, in line
with the leaf spec (PI is the module constant; conversion helpers live in
_deg/_rad below).
"""

import math

PI = math.pi  # module constant (leaf spec)


def _deg_to_rad(angle_deg):
    """Convert degrees to radians."""
    return angle_deg * PI / 180.0


def _wrap_180(angle_deg):
    """Wrap an angle in degrees into [-180, 180]."""
    wrapped = (angle_deg + 180.0) % 360.0 - 180.0
    return wrapped


def _beta_deg(los_to_target_angle_deg, target_heading_angle_deg):
    """Signed angle beta in degrees between the target velocity and the LOS.

    beta = wrap180(target_heading_angle - los_to_target_angle), the angle of
    the target velocity vector off the line of sight on the closing side:
    beta = 0 is the head-on geometry where the target flies straight at the
    pursuer.
    """
    return _wrap_180(target_heading_angle_deg - los_to_target_angle_deg)


def lead_angle(pursuer_speed, target_speed, los_to_target_angle_deg,
               target_heading_angle_deg):
    """Collision-course lead angle LA in degrees.

    LA satisfies sin(LA) = (target_speed / pursuer_speed) * sin(beta), with
    beta the wrapped angle between the target velocity vector and the line of
    sight.  Positive toward the target's flight side.  Raises ValueError if
    pursuer_speed <= 0, target_speed < 0, or no collision course exists (the
    asin argument exceeds 1 in magnitude, i.e. the target is too fast for the
    geometry).
    """
    if pursuer_speed <= 0:
        raise ValueError("pursuer_speed must be > 0, got %r" % (pursuer_speed,))
    if target_speed < 0:
        raise ValueError("target_speed must be >= 0, got %r" % (target_speed,))
    beta = _beta_deg(los_to_target_angle_deg, target_heading_angle_deg)
    arg = (target_speed / pursuer_speed) * math.sin(_deg_to_rad(beta))
    if arg > 1.0 or arg < -1.0:
        raise ValueError(
            "no collision course: (Vt/Vp) sin(beta) = %.6g exceeds 1 in "
            "magnitude (target too fast for this geometry)" % (arg,)
        )
    return math.degrees(math.asin(arg))


def collision_closing_speed(pursuer_speed, target_speed,
                            los_to_target_angle_deg, target_heading_angle_deg):
    """Closing speed Vc along the line of sight in m/s.

    Vc = pursuer_speed * cos(LA) + target_speed * cos(beta), where LA and beta
    come from the same collision triangle; the target velocity component
    toward the pursuer is positive when the target heads along the LOS toward
    the pursuer (beta = 0 head-on closing).  Raises ValueError if the result
    is <= 0 (no closing intercept).
    """
    la = _deg_to_rad(lead_angle(pursuer_speed, target_speed,
                                los_to_target_angle_deg,
                                target_heading_angle_deg))
    beta = _deg_to_rad(_beta_deg(los_to_target_angle_deg,
                                 target_heading_angle_deg))
    vc = pursuer_speed * math.cos(la) + target_speed * math.cos(beta)
    if vc <= 0:
        raise ValueError(
            "no closing intercept: closing speed %g m/s must be > 0" % (vc,)
        )
    return vc


def time_to_go(range_m, closing_speed):
    """Time to go t_go = range / closing speed in seconds.

    Raises ValueError if range_m < 0 or closing_speed <= 0.
    """
    if range_m < 0:
        raise ValueError("range_m must be >= 0, got %r" % (range_m,))
    if closing_speed <= 0:
        raise ValueError("closing_speed must be > 0, got %r" % (closing_speed,))
    return range_m / closing_speed


def intercept_point(pursuer_x, pursuer_y, target_x, target_y, target_vx,
                    target_vy, time_to_go):
    """Predicted intercept point (x, y) in m.

    The target position extrapolated by its constant velocity over t_go:
    (target_x + target_vx * t_go, target_y + target_vy * t_go).
    """
    return (target_x + target_vx * time_to_go,
            target_y + target_vy * time_to_go)


def heading_error_deg(pursuer_heading_deg, los_angle_deg, lead_angle_deg):
    """Bearing error in degrees between the required and current headings.

    The required heading is los_angle + lead_angle; the error is the
    difference from the current pursuer heading, wrapped to [-180, 180].
    """
    required = los_angle_deg + lead_angle_deg
    return _wrap_180(required - pursuer_heading_deg)


def collision_course_assessment(pursuer_x, pursuer_y, target_x, target_y,
                                target_vx, target_vy, pursuer_speed,
                                target_speed):
    """Convenience chain: full collision-course intercept assessment.

    Computes the range and LOS angle from the position vectors, the lead
    angle and closing speed from the speeds and the LOS/target headings, the
    time to go, and the predicted intercept point.  Returns a dict with
    exactly the keys range_m, los_angle_deg, lead_angle_deg,
    closing_speed_m_s, time_to_go_s, intercept_x, intercept_y.
    """
    range_m = math.hypot(target_x - pursuer_x, target_y - pursuer_y)
    los_angle_deg = math.degrees(
        math.atan2(target_y - pursuer_y, target_x - pursuer_x)
    )
    target_heading_deg = math.degrees(math.atan2(target_vy, target_vx))
    la_deg = lead_angle(pursuer_speed, target_speed, los_angle_deg,
                        target_heading_deg)
    vc = collision_closing_speed(pursuer_speed, target_speed, los_angle_deg,
                                 target_heading_deg)
    t_go = time_to_go(range_m, vc)
    ix, iy = intercept_point(pursuer_x, pursuer_y, target_x, target_y,
                             target_vx, target_vy, t_go)
    return {
        "range_m": range_m,
        "los_angle_deg": los_angle_deg,
        "lead_angle_deg": la_deg,
        "closing_speed_m_s": vc,
        "time_to_go_s": t_go,
        "intercept_x": ix,
        "intercept_y": iy,
    }
