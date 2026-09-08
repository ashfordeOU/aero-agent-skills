"""Landing gear height sizing: static ground line, main and nose gear
heights, hard point clearance margins and the height verdict.

Pure stdlib, closed form, deterministic. Body frame at the level attitude:
stations x in metres aft of the fuselage datum, z in metres positive up
from the main gear attach plane. See SKILL.md for the full derivation.
"""

import math

DEG2RAD = math.pi / 180.0
MAX_ROTATION_DEG = 25.0


def _check_rotation_deg(theta_deg, allow_zero):
    """Reject a rotation angle outside the physical design band."""
    lower = 0.0 if allow_zero else 0.0
    if theta_deg < lower or theta_deg > MAX_ROTATION_DEG:
        raise ValueError(
            "theta_deg %r outside [0, %.1f] deg band" % (theta_deg, MAX_ROTATION_DEG)
        )


def clearance_at_attitude(z_body, x_point, x_mg, h_ground_line, theta_deg):
    """Clearance c(theta) of a hard point during a nose-up rotation about x_mg."""
    if h_ground_line <= 0:
        raise ValueError("h_ground_line must be positive, got %r" % h_ground_line)
    _check_rotation_deg(theta_deg, allow_zero=True)
    theta = theta_deg * DEG2RAD
    arm = x_point - x_mg
    return (h_ground_line + z_body) * math.cos(theta) - arm * math.sin(theta)


def required_ground_line(z_body, x_point, x_mg, theta_deg, clearance_req):
    """Static ground line needed so the point keeps clearance_req at theta_deg."""
    if clearance_req < 0:
        raise ValueError("clearance_req must be non-negative, got %r" % clearance_req)
    _check_rotation_deg(theta_deg, allow_zero=True)
    theta = theta_deg * DEG2RAD
    arm = x_point - x_mg
    return clearance_req / math.cos(theta) + arm * math.tan(theta) - z_body


def static_ground_line(points, theta_rot_deg, x_mg, x_ng):
    """Solve H_gl as the max required ground line over all points and attitudes.

    Each point dict: {"station", "z_body", "clearance_level" (default 0.0),
    "clearance_rotation" (default None), "name"}.
    Returns (H_gl, binding_point_name).
    """
    if x_mg <= x_ng:
        raise ValueError("wheelbase not positive: x_mg %r <= x_ng %r" % (x_mg, x_ng))
    if theta_rot_deg <= 0 or theta_rot_deg > MAX_ROTATION_DEG:
        raise ValueError(
            "theta_rot_deg %r outside (0, %.1f] deg band" % (theta_rot_deg, MAX_ROTATION_DEG)
        )
    if not points:
        raise ValueError("points must be a non-empty list")

    best_h = None
    best_name = None
    for point in points:
        station = point["station"]
        z_body = point["z_body"]
        name = point["name"]
        clearance_level = point.get("clearance_level", 0.0)
        clearance_rotation = point.get("clearance_rotation", None)
        if clearance_level < 0:
            raise ValueError("clearance_level for %r must be non-negative" % name)
        if clearance_rotation is not None and clearance_rotation < 0:
            raise ValueError("clearance_rotation for %r must be non-negative" % name)

        h_level = required_ground_line(z_body, station, x_mg, 0.0, clearance_level)
        if best_h is None or h_level > best_h:
            best_h = h_level
            best_name = name

        if clearance_rotation is not None:
            h_rot = required_ground_line(z_body, station, x_mg, theta_rot_deg, clearance_rotation)
            if h_rot > best_h:
                best_h = h_rot
                best_name = name

    return best_h, best_name


def gear_heights(h_ground_line, nose_attach_z_body):
    """Main and nose gear heights and their difference, m."""
    if h_ground_line <= 0:
        raise ValueError("h_ground_line must be positive, got %r" % h_ground_line)
    nose_gear_height = h_ground_line + nose_attach_z_body
    if nose_gear_height <= 0:
        raise ValueError(
            "nose gear height not positive: %r" % nose_gear_height
        )
    main_gear_height = h_ground_line
    return {
        "main_gear_height": main_gear_height,
        "nose_gear_height": nose_gear_height,
        "height_difference": main_gear_height - nose_gear_height,
    }


def propeller_low_point(z_hub_body, radius):
    """Propeller disc lowest point body height, m."""
    if radius <= 0:
        raise ValueError("radius must be positive, got %r" % radius)
    return z_hub_body - radius


def static_load_share(x_cg, x_mg, x_ng):
    """Nose gear static load share at the design CG, feasibility-only."""
    if x_mg <= x_ng:
        raise ValueError("wheelbase not positive: x_mg %r <= x_ng %r" % (x_mg, x_ng))
    if not (x_ng < x_cg < x_mg):
        raise ValueError("design CG %r not strictly inside the wheelbase" % x_cg)
    return (x_mg - x_cg) / (x_mg - x_ng)


def clearance_margin(z_body, x_point, x_mg, h_ground_line, theta_deg, clearance_req):
    """Achieved clearance minus required clearance at one attitude, m."""
    if clearance_req < 0:
        raise ValueError("clearance_req must be non-negative, got %r" % clearance_req)
    achieved = clearance_at_attitude(z_body, x_point, x_mg, h_ground_line, theta_deg)
    return achieved - clearance_req


def tail_strike_angle_deg(h_tail_contact, tail_arm):
    """Tail strike angle of the solved geometry, deg (layout sibling relation)."""
    if h_tail_contact <= 0:
        raise ValueError("h_tail_contact must be positive, got %r" % h_tail_contact)
    if tail_arm <= 0:
        raise ValueError("tail_arm must be positive, got %r" % tail_arm)
    return math.atan(h_tail_contact / tail_arm) / DEG2RAD
