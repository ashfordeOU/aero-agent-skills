"""Diagonal tension field post-buckled shear web analysis (stdlib only).

Implements the classical complete-diagonal-tension idealization of a plane
shear web loaded above its elastic shear-buckling stress. All functions are
pure and deterministic. Units are SI throughout: shear stresses in Pa,
dimensions in m, loads in N, shear flow in N/m, angles in degrees.

Module constants:
    ALPHA_IDEAL_DEG: the classical plane-web tension field angle from the
        Kuhn sin(2 * alpha) = 1 approximation, 45 degrees.
"""

import math

ALPHA_IDEAL_DEG = 45.0


def _validate_shear_state(tau, tau_cr):
    """Reject non-physical shear stresses; return None or raise ValueError.

    The applied shear tau must be non-negative and the buckling stress
    tau_cr strictly positive (a web with no finite buckling stress has no
    diagonal-tension regime to analyze).
    """
    if tau < 0.0:
        raise ValueError("applied shear stress tau must be >= 0")
    if tau_cr <= 0.0:
        raise ValueError("buckling shear stress tau_cr must be > 0")


def _validate_angle(alpha_deg):
    """Reject a tension field angle outside the open interval (0, 90) degrees."""
    if alpha_deg is None or not (0.0 < alpha_deg < 90.0):
        raise ValueError("tension field angle must lie in (0, 90) degrees")


def tension_field_ratio(tau, tau_cr):
    """Return the tension field ratio k of the applied shear above buckling.

    k = (tau - tau_cr) / tau when the web is above its buckling stress,
    else 0.0 in the elastic regime below buckling. ValueErrors on a
    negative tau or a non-positive tau_cr.
    """
    _validate_shear_state(tau, tau_cr)
    if tau <= tau_cr:
        return 0.0
    return (tau - tau_cr) / tau


def tension_field_angle(tau, tau_cr):
    """Return the tension field angle in degrees, ALPHA_IDEAL_DEG = 45.0.

    The classical plane-web value follows from the Kuhn sin(2 * alpha) = 1
    approximation, so the angle is constant and continuous across the whole
    post-buckling range; an inclined (non-45 degree) field is entered by the
    caller as the alpha_deg argument of the stress and load functions.
    """
    _validate_shear_state(tau, tau_cr)
    return ALPHA_IDEAL_DEG


def web_tension_stress(tau, tau_cr, alpha_deg):
    """Return the diagonal web tension stress sigma_d in Pa.

    sigma_d = (tau - tau_cr) * (cot(alpha) + tan(alpha)) above the buckling
    stress, else 0.0 (the elastic web carries no diagonal tension). At 45
    degrees sigma_d equals 2 * (tau - tau_cr).
    """
    _validate_shear_state(tau, tau_cr)
    _validate_angle(alpha_deg)
    if tau <= tau_cr:
        return 0.0
    alpha_rad = math.radians(alpha_deg)
    return (tau - tau_cr) * (1.0 / math.tan(alpha_rad) + math.tan(alpha_rad))


def _validate_web_geometry(depth_m, web_thickness_m):
    """Reject non-positive web depth and thickness."""
    if depth_m <= 0.0:
        raise ValueError("web depth d must be > 0")
    if web_thickness_m <= 0.0:
        raise ValueError("web thickness t must be > 0")


def flange_axial_load(tau, tau_cr, alpha_deg, depth_m, web_thickness_m):
    """Return the flange axial load P_f in N pulled in by the diagonal tension.

    P_f = (tau - tau_cr) * t * d * cot(alpha) above the buckling stress,
    else 0.0. This is the diagonal-tension component resolved into the
    flange over the web depth d.
    """
    _validate_shear_state(tau, tau_cr)
    _validate_angle(alpha_deg)
    _validate_web_geometry(depth_m, web_thickness_m)
    if tau <= tau_cr:
        return 0.0
    alpha_rad = math.radians(alpha_deg)
    return (tau - tau_cr) * web_thickness_m * depth_m / math.tan(alpha_rad)


def end_post_load(tau, tau_cr, alpha_deg, depth_m, web_thickness_m):
    """Return the end post axial load P_e in N from the diagonal tension.

    P_e = (tau - tau_cr) * t * d * tan(alpha) above the buckling stress,
    else 0.0; at 45 degrees the flange and end post loads are equal.
    """
    _validate_shear_state(tau, tau_cr)
    _validate_angle(alpha_deg)
    _validate_web_geometry(depth_m, web_thickness_m)
    if tau <= tau_cr:
        return 0.0
    alpha_rad = math.radians(alpha_deg)
    return (tau - tau_cr) * web_thickness_m * depth_m * math.tan(alpha_rad)


def rivet_shear_flow(tau, tau_cr, alpha_deg, web_thickness_m, member):
    """Return the rivet shear flow q in N/m on a flange or end post attachment.

    For member "flange" above buckling the flow is q = t * (tau_cr +
    (tau - tau_cr) * tan(alpha)); below buckling it is the elastic flow
    q = tau * t. For member "end_post" the flow is q = tau * t in both
    regimes because the end post carries the full applied shear. At 45
    degrees the two flows coincide.
    """
    _validate_shear_state(tau, tau_cr)
    _validate_angle(alpha_deg)
    if web_thickness_m <= 0.0:
        raise ValueError("web thickness t must be > 0")
    if member not in ("flange", "end_post"):
        raise ValueError("member must be 'flange' or 'end_post'")
    if member == "end_post":
        return tau * web_thickness_m
    if tau <= tau_cr:
        return tau * web_thickness_m
    alpha_rad = math.radians(alpha_deg)
    return web_thickness_m * (tau_cr + (tau - tau_cr) * math.tan(alpha_rad))


def margin_against_buckling(tau, tau_cr):
    """Return the margin against buckling tau_cr / tau.

    The ratio is 0.0 at zero applied shear, 1.0 at the buckling stress and
    below 1.0 in the post-buckled diagonal-tension regime where the web
    works on its tension field reserve.
    """
    _validate_shear_state(tau, tau_cr)
    if tau == 0.0:
        return 0.0
    return tau_cr / tau
