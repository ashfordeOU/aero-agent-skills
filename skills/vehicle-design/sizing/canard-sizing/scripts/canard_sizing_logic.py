"""Canard sizing logic for conceptual aircraft sizing (pure stdlib).

Sizes the forward canard surface of a canard-configured aircraft:
required canard area from a target canard volume coefficient, the trim
lift share carried by the canard from the longitudinal geometry, the
canard and wing lift coefficients at the trim condition, and the stall
precedence verdict (canard must reach maximum lift before the wing so
the nose drops rather than pitches up).

Geometry convention: x is positive aft, origin at the wing
aerodynamic center. The canard lies forward of the wing (x_c < x_w =
0) and the center of gravity lies between them (x_c < x_cg < x_w).
All arms in m, areas in m2, forces in N.
"""

G0 = 9.80665  # standard gravity, m/s2


def canard_volume_coefficient(canard_area, canard_arm, wing_area, wing_mac):
    """Return the canard volume coefficient V_c = S_c * arm / (S * cbar).

    Mirrors the horizontal tail volume coefficient convention with the
    arm measured from the wing aerodynamic center to the canard
    aerodynamic center.
    """
    if canard_area <= 0:
        raise ValueError("canard_area must be positive")
    if canard_arm <= 0:
        raise ValueError("canard_arm must be positive")
    if wing_area <= 0:
        raise ValueError("wing_area must be positive")
    if wing_mac <= 0:
        raise ValueError("wing_mac must be positive")
    return canard_area * canard_arm / (wing_area * wing_mac)


def required_canard_area(target_volume_coefficient, canard_arm,
                         wing_area, wing_mac):
    """Return the canard area S_c for a target volume coefficient.

    S_c = target_volume_coefficient * wing_area * wing_mac / canard_arm.
    """
    if target_volume_coefficient <= 0:
        raise ValueError("target_volume_coefficient must be positive")
    if canard_arm <= 0:
        raise ValueError("canard_arm must be positive")
    if wing_area <= 0:
        raise ValueError("wing_area must be positive")
    if wing_mac <= 0:
        raise ValueError("wing_mac must be positive")
    return target_volume_coefficient * wing_area * wing_mac / canard_arm


def canard_lift_share(x_cg, x_w, x_c):
    """Return the fraction of weight carried by the canard in trim.

    f_c = (x_w - x_cg) / (x_w - x_c) from the moment balance about the
    center of gravity with lift up positive. Requires x_c < x_cg < x_w.
    """
    if not (x_c < x_cg < x_w):
        raise ValueError("geometry requires x_c < x_cg < x_w")
    return (x_w - x_cg) / (x_w - x_c)


def trim_lift_coefficients(weight, dynamic_pressure, wing_area,
                           canard_area, x_cg, x_w, x_c):
    """Return trim lift share, lift forces and lift coefficients dict.

    Steady level trim at the given dynamic pressure: the canard carries
    the share f_c of the weight and the wing the remainder, giving
    Cl_c = L_c / (q * S_c) and Cl_w = L_w / (q * S_w).
    """
    if weight <= 0:
        raise ValueError("weight must be positive")
    if dynamic_pressure <= 0:
        raise ValueError("dynamic_pressure must be positive")
    if wing_area <= 0:
        raise ValueError("wing_area must be positive")
    if canard_area <= 0:
        raise ValueError("canard_area must be positive")
    f_c = canard_lift_share(x_cg, x_w, x_c)
    lift_c = f_c * weight
    lift_w = weight - lift_c
    return {
        "canard_lift_share": f_c,
        "canard_lift_N": lift_c,
        "wing_lift_N": lift_w,
        "canard_cl": lift_c / (dynamic_pressure * canard_area),
        "wing_cl": lift_w / (dynamic_pressure * wing_area),
    }


def stall_precedence(canard_cl, canard_cl_max, wing_cl, wing_cl_max):
    """Return margin ratios and the stall precedence verdict.

    margin_ratio_c = canard_cl_max / canard_cl and margin_ratio_w =
    wing_cl_max / wing_cl; the surface with the smaller margin ratio
    stalls first. A canard configuration requires canard-stalls-first
    so the nose drops instead of pitching up at the stall.
    """
    if canard_cl <= 0:
        raise ValueError("canard_cl must be positive at trim for this check")
    if wing_cl <= 0:
        raise ValueError("wing_cl must be positive at trim for this check")
    if canard_cl_max <= 0:
        raise ValueError("canard_cl_max must be positive")
    if wing_cl_max <= 0:
        raise ValueError("wing_cl_max must be positive")
    margin_c = canard_cl_max / canard_cl
    margin_w = wing_cl_max / wing_cl
    verdict = ("canard-stalls-first" if margin_c < margin_w
               else "wing-stalls-first")
    return {"canard_margin_ratio": margin_c,
            "wing_margin_ratio": margin_w,
            "verdict": verdict}


def size_canard(target_volume_coefficient, canard_arm, wing_area,
                wing_mac):
    """Return the sized canard area dict for a target volume coefficient.

    Convenience wrapper over required_canard_area that also echoes the
    target volume coefficient. ValueErrors propagate unchanged.
    """
    area = required_canard_area(target_volume_coefficient, canard_arm,
                                wing_area, wing_mac)
    return {"canard_area": area,
            "canard_volume_coefficient": target_volume_coefficient}
