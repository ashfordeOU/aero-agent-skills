"""Landing gear retraction mechanism sizing (conceptual level).

Pure stdlib module for sizing the landing gear retraction system:
the gear moment about the retract pivot from the gear weight and its
CG arm, the retraction actuator force from that moment and the
actuator arm with a design factor, the actuator stroke from the
linkage geometry (law of cosines on the two fixed links between the
down-locked and up-locked positions), the down-lock and up-lock hold
loads at their lock arms, and the gear bay stowage fit of the wheel
and folded strut envelope.

Conventions: gear weight in N, arms in m, angles in degrees. Units are
SI throughout. All functions are deterministic and pure; every
non-physical input raises ValueError.
"""

import math

DESIGN_FACTOR_DEFAULT = 1.5  # sizing factor on the retraction moment
LOCK_FACTOR_DEFAULT = 1.0  # hold-load factor for the lock reactions


def retraction_moment(gear_weight_n, cg_arm_m):
    """Gear moment about the retract pivot: moment = W * d.

    cg_arm_m is the gear CG arm ahead of the retract pivot. Returns
    {moment_nm, cg_arm_m}. Raises ValueError on non-positive inputs.
    """
    if gear_weight_n <= 0:
        raise ValueError("gear_weight_n must be positive")
    if cg_arm_m <= 0:
        raise ValueError("cg_arm_m must be positive")
    return {"moment_nm": gear_weight_n * cg_arm_m, "cg_arm_m": cg_arm_m}


def actuator_force(moment_nm, actuator_arm_m,
                   design_factor=DESIGN_FACTOR_DEFAULT):
    """Retraction actuator force from the gear moment and actuator arm.

    force = design_factor * moment / actuator_arm_m. Returns
    {force_n, moment_nm, actuator_arm_m}. Raises ValueError when the
    moment or actuator arm is non-positive or the design factor < 1.
    """
    if moment_nm <= 0:
        raise ValueError("moment_nm must be positive")
    if actuator_arm_m <= 0:
        raise ValueError("actuator_arm_m must be positive")
    if design_factor < 1:
        raise ValueError("design_factor must be >= 1")
    return {"force_n": design_factor * moment_nm / actuator_arm_m,
            "moment_nm": moment_nm,
            "actuator_arm_m": actuator_arm_m}


def link_length(a_m, b_m, angle_deg):
    """Effective link length between the two attach points.

    Law of cosines on the linkage triangle: L = sqrt(a^2 + b^2 -
    2 a b cos(angle)). a_m and b_m are the fixed links from the retract
    pivot to the gear attach and actuator attach points; angle_deg is
    the angle between the down-locked and retracted actuator lines.
    Returns the link length in m. Raises ValueError for non-positive
    links, an angle outside (0, 180) degrees, or a geometry whose
    resulting length cannot lie between |a - b| and a + b.
    """
    if a_m <= 0:
        raise ValueError("a_m must be positive")
    if b_m <= 0:
        raise ValueError("b_m must be positive")
    if not 0 < angle_deg < 180:
        raise ValueError("angle_deg must lie in (0, 180)")
    length = math.sqrt(a_m ** 2 + b_m ** 2
                       - 2.0 * a_m * b_m * math.cos(math.radians(angle_deg)))
    if length > a_m + b_m + 1e-12 or length < abs(a_m - b_m) - 1e-12:
        raise ValueError(
            "geometry impossible: link length outside [|a-b|, a+b]")
    return length


def actuator_stroke(a_m, b_m, down_angle_deg, up_angle_deg):
    """Actuator stroke between the down-locked and up-locked geometry.

    stroke = L(down) - L(up) with both links from link_length. Returns
    {down_link_m, up_link_m, stroke_m}. Raises ValueError when the
    stroke is not positive (the up-lock geometry is longer than the
    down-lock geometry, so the actuator cannot retract the gear).
    """
    down_link = link_length(a_m, b_m, down_angle_deg)
    up_link = link_length(a_m, b_m, up_angle_deg)
    stroke = down_link - up_link
    if stroke <= 0:
        raise ValueError("up-lock not reachable: stroke must be positive")
    return {"down_link_m": down_link, "up_link_m": up_link,
            "stroke_m": stroke}


def lock_reaction(moment_nm, lock_arm_m, factor=LOCK_FACTOR_DEFAULT):
    """Lock hold load at a lock arm: reaction = factor * moment / arm.

    Returns {reaction_n, lock_arm_m}. Raises ValueError on
    non-positive inputs (moment, lock arm or factor).
    """
    if moment_nm <= 0:
        raise ValueError("moment_nm must be positive")
    if lock_arm_m <= 0:
        raise ValueError("lock_arm_m must be positive")
    if factor <= 0:
        raise ValueError("factor must be positive")
    return {"reaction_n": factor * moment_nm / lock_arm_m,
            "lock_arm_m": lock_arm_m}


def stowage_check(wheel_diameter_m, wheel_width_m, folded_strut_m,
                  bay_length_m, bay_width_m, bay_depth_m):
    """Gear bay stowage fit of the wheel and folded strut envelope.

    Verdict PASS when wheel_diameter <= bay_length, wheel_width <=
    bay_width and folded_strut <= bay_depth; otherwise FAIL with the
    list of violated dimensions in reasons. Raises ValueError on
    non-positive dimensions.
    """
    for name, value in (("wheel_diameter_m", wheel_diameter_m),
                        ("wheel_width_m", wheel_width_m),
                        ("folded_strut_m", folded_strut_m),
                        ("bay_length_m", bay_length_m),
                        ("bay_width_m", bay_width_m),
                        ("bay_depth_m", bay_depth_m)):
        if value <= 0:
            raise ValueError("%s must be positive" % name)
    reasons = []
    if wheel_diameter_m > bay_length_m:
        reasons.append("wheel_diameter %.4f m exceeds bay_length %.4f m"
                       % (wheel_diameter_m, bay_length_m))
    if wheel_width_m > bay_width_m:
        reasons.append("wheel_width %.4f m exceeds bay_width %.4f m"
                       % (wheel_width_m, bay_width_m))
    if folded_strut_m > bay_depth_m:
        reasons.append("folded_strut %.4f m exceeds bay_depth %.4f m"
                       % (folded_strut_m, bay_depth_m))
    verdict = "PASS" if not reasons else "FAIL"
    return {"verdict": verdict, "reasons": reasons}


def retraction_summary(gear_weight_n, cg_arm_m, actuator_arm_m,
                       a_m, b_m, down_angle_deg, up_angle_deg,
                       down_lock_arm_m, up_lock_arm_m,
                       wheel_diameter_m, wheel_width_m, folded_strut_m,
                       bay_length_m, bay_width_m, bay_depth_m,
                       design_factor=DESIGN_FACTOR_DEFAULT):
    """Complete retraction sizing summary dict for a main gear.

    Chains retraction_moment, actuator_force, actuator_stroke,
    lock_reaction at the down and up lock arms and stowage_check.
    Returns one dict with the moment, force, stroke, linkage, lock
    reaction and stowage keys documented in the SKILL body.
    """
    moment = retraction_moment(gear_weight_n, cg_arm_m)
    force = actuator_force(moment["moment_nm"], actuator_arm_m,
                           design_factor)
    stroke = actuator_stroke(a_m, b_m, down_angle_deg, up_angle_deg)
    down_lock = lock_reaction(moment["moment_nm"], down_lock_arm_m)
    up_lock = lock_reaction(moment["moment_nm"], up_lock_arm_m)
    stowage = stowage_check(wheel_diameter_m, wheel_width_m,
                            folded_strut_m, bay_length_m, bay_width_m,
                            bay_depth_m)
    return {
        "moment_nm": moment["moment_nm"],
        "cg_arm_m": moment["cg_arm_m"],
        "force_n": force["force_n"],
        "actuator_arm_m": force["actuator_arm_m"],
        "a_m": a_m,
        "b_m": b_m,
        "down_angle_deg": down_angle_deg,
        "up_angle_deg": up_angle_deg,
        "down_link_m": stroke["down_link_m"],
        "up_link_m": stroke["up_link_m"],
        "stroke_m": stroke["stroke_m"],
        "design_factor": design_factor,
        "down_lock_arm_m": down_lock_arm_m,
        "up_lock_arm_m": up_lock_arm_m,
        "down_lock_reaction_n": down_lock["reaction_n"],
        "up_lock_reaction_n": up_lock["reaction_n"],
        "stowage": stowage,
    }
