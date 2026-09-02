#!/usr/bin/env python3
"""Wing box structural sizing logic (paraphrase, common conceptual design).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): the wing box is the primary bending and shear
structure of the wing. The classical box-beam idealization carries the
root bending moment as a couple between the upper and lower spar caps
and carries the shear as shear flow in the spar webs. For an elliptical
spanwise lift distribution the centerline root bending moment is
M = (2/(3*pi)) * n * W * b, with n the load factor, W the design weight
in newtons, and b the span in meters; a uniform distribution gives
M = n * W * b / 4. FAR-25.303 requires a factor of safety of 1.5
between limit and ultimate loads, so M_ultimate = 1.5 * M_limit. The
spar cap area follows from the bending stress relation
M = sigma * A * h, so A = M / (sigma * h) with h the box depth; the web
thickness follows from the shear flow q = V / (n_webs * h) and the
allowable shear stress, t = q / tau. Units: newtons, meters, pascals.
"""

import math


def wing_root_bending_moment(load_factor, weight_n, span_m, distribution="elliptical"):
    """Centerline root bending moment in N m under the design load case.

    Elliptical spanwise lift distribution: M = (2/(3*pi)) * n * W * b.
    Uniform spanwise lift distribution: M = n * W * b / 4.
    Raises ValueError on non-positive load factor, weight, or span, and
    on an unknown distribution name.
    """
    if load_factor <= 0:
        raise ValueError("load factor must be > 0, got %r" % (load_factor,))
    if weight_n <= 0:
        raise ValueError("weight must be > 0 N, got %r" % (weight_n,))
    if span_m <= 0:
        raise ValueError("span must be > 0 m, got %r" % (span_m,))
    if distribution == "elliptical":
        factor = 2.0 / (3.0 * math.pi)
    elif distribution == "uniform":
        factor = 0.25
    else:
        raise ValueError(
            "distribution must be 'elliptical' or 'uniform', got %r" % (distribution,)
        )
    return factor * load_factor * weight_n * span_m


def wing_root_shear(load_factor, weight_n):
    """Root shear force in newtons carried by one half-wing, n * W / 2."""
    if load_factor <= 0:
        raise ValueError("load factor must be > 0, got %r" % (load_factor,))
    if weight_n <= 0:
        raise ValueError("weight must be > 0 N, got %r" % (weight_n,))
    return load_factor * weight_n / 2.0


def ultimate_moment(limit_moment_nm, safety_factor=1.5):
    """Ultimate bending moment from the limit moment and the safety factor.

    FAR-25.303 context: ultimate = 1.5 * limit for transport aeroplanes.
    """
    if limit_moment_nm <= 0:
        raise ValueError("limit moment must be > 0 N m, got %r" % (limit_moment_nm,))
    if safety_factor <= 0:
        raise ValueError("safety factor must be > 0, got %r" % (safety_factor,))
    return safety_factor * limit_moment_nm


def spar_cap_area(bending_moment_nm, allowable_stress_pa, box_depth_m):
    """Spar cap area in m^2 per cap from M = sigma * A * h.

    One cap per side (upper and lower); each cap carries the full couple
    arm h between cap centroids.
    """
    if bending_moment_nm <= 0:
        raise ValueError("bending moment must be > 0 N m, got %r" % (bending_moment_nm,))
    if allowable_stress_pa <= 0:
        raise ValueError(
            "allowable stress must be > 0 Pa, got %r" % (allowable_stress_pa,)
        )
    if box_depth_m <= 0:
        raise ValueError("box depth must be > 0 m, got %r" % (box_depth_m,))
    return bending_moment_nm / (allowable_stress_pa * box_depth_m)


def web_shear_flow(shear_force_n, box_depth_m, web_count=2):
    """Shear flow in N/m per spar web, q = V / (n_webs * h)."""
    if shear_force_n < 0:
        raise ValueError("shear force must be >= 0 N, got %r" % (shear_force_n,))
    if box_depth_m <= 0:
        raise ValueError("box depth must be > 0 m, got %r" % (box_depth_m,))
    if web_count < 1:
        raise ValueError("web count must be >= 1, got %r" % (web_count,))
    return shear_force_n / (web_count * box_depth_m)


def web_thickness(shear_flow_n_per_m, allowable_shear_pa):
    """Spar web thickness in m from the shear flow and the allowable shear.

    t = q / tau, with tau the allowable shear stress in pascals.
    """
    if shear_flow_n_per_m < 0:
        raise ValueError(
            "shear flow must be >= 0 N/m, got %r" % (shear_flow_n_per_m,)
        )
    if allowable_shear_pa <= 0:
        raise ValueError(
            "allowable shear must be > 0 Pa, got %r" % (allowable_shear_pa,)
        )
    return shear_flow_n_per_m / allowable_shear_pa


def wing_box_verdict(cap_area_required, cap_area_available,
                     web_thickness_required, web_thickness_available):
    """Sizing verdict: 'box sized' or 'box undersized'.

    Both the spar cap area and the web thickness must fit within the
    available values for the box to close.
    """
    if cap_area_required < 0 or cap_area_available < 0:
        raise ValueError("cap areas must be >= 0 m^2")
    if web_thickness_required < 0 or web_thickness_available < 0:
        raise ValueError("web thicknesses must be >= 0 m")
    if cap_area_required <= cap_area_available and (
        web_thickness_required <= web_thickness_available
    ):
        return "box sized"
    return "box undersized"
