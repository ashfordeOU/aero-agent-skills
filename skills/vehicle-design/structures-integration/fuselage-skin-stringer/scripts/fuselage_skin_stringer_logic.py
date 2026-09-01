#!/usr/bin/env python3
"""Pressurized fuselage skin-stringer panel sizing (common knowledge).

Common-knowledge summary (standards-map.yaml far-25 / cs-25 context):
FAR-25.303 sets the 1.5 factor of safety between limit and ultimate
loads and FAR-25.365 covers pressurization loads. The thin-cylinder
membrane stresses from the cabin differential pressure p and radius r
are the hoop stress sigma_h = p * r / t and the longitudinal stress
sigma_l = p * r / (2 * t). The pressure skin thickness follows from
the governing hoop stress scaled by the factor of safety, floored by
the minimum gauge. The stringer spacing comes from flat panel
buckling sigma_cr = k * pi^2 * E * (t / b)^2 / (12 * (1 - nu^2)); the
frame pitch comes from the stringer column buckling length
sigma_cr = pi^2 * E * I / (A * L^2). The stringer area follows from
the compression strip load and the effective skin width
b_eff = 1.9 * t * sqrt(E / sigma_allowable). Units: Pa, m, m^2, m^4,
N.
"""

import math


def hoop_stress(pressure_pa, radius_m, thickness_m):
    """Thin-cylinder hoop membrane stress p * r / t in Pa.

    Raises ValueError on non-positive pressure, radius, or thickness.
    """
    if pressure_pa <= 0:
        raise ValueError("pressure must be > 0 Pa, got %r" % (pressure_pa,))
    if radius_m <= 0:
        raise ValueError("radius must be > 0 m, got %r" % (radius_m,))
    if thickness_m <= 0:
        raise ValueError("thickness must be > 0 m, got %r" % (thickness_m,))
    return pressure_pa * radius_m / thickness_m


def longitudinal_stress(pressure_pa, radius_m, thickness_m):
    """Thin-cylinder longitudinal membrane stress p * r / (2 * t) in Pa.

    Half the hoop stress. Raises ValueError on non-positive pressure,
    radius, or thickness.
    """
    if pressure_pa <= 0:
        raise ValueError("pressure must be > 0 Pa, got %r" % (pressure_pa,))
    if radius_m <= 0:
        raise ValueError("radius must be > 0 m, got %r" % (radius_m,))
    if thickness_m <= 0:
        raise ValueError("thickness must be > 0 m, got %r" % (thickness_m,))
    return pressure_pa * radius_m / (2.0 * thickness_m)


def skin_thickness(
    pressure_pa,
    radius_m,
    allowable_pa,
    factor_of_safety=1.5,
    minimum_gauge_m=0.0012,
):
    """Pressure skin thickness in m from the governing hoop stress.

    t_hoop = p * r * FS / allowable; t_long = p * r * FS / (2 *
    allowable); the result is the maximum of the two and the minimum
    gauge. The hoop term governs under pressure. Raises ValueError on
    non-positive pressure, radius, allowable, or gauge, or on a
    factor of safety below 1.0.
    """
    if pressure_pa <= 0:
        raise ValueError("pressure must be > 0 Pa, got %r" % (pressure_pa,))
    if radius_m <= 0:
        raise ValueError("radius must be > 0 m, got %r" % (radius_m,))
    if allowable_pa <= 0:
        raise ValueError("allowable must be > 0 Pa, got %r" % (allowable_pa,))
    if factor_of_safety < 1.0:
        raise ValueError(
            "factor of safety must be >= 1.0, got %r" % (factor_of_safety,)
        )
    if minimum_gauge_m <= 0:
        raise ValueError(
            "minimum gauge must be > 0 m, got %r" % (minimum_gauge_m,)
        )
    t_hoop = pressure_pa * radius_m * factor_of_safety / allowable_pa
    t_long = pressure_pa * radius_m * factor_of_safety / (2.0 * allowable_pa)
    return max(t_hoop, t_long, minimum_gauge_m)


def stringer_spacing(
    skin_thickness_m,
    modulus_pa,
    buckling_allowable_pa,
    k=4.0,
    poisson=0.3,
):
    """Stringer spacing b in m from the flat panel buckling allowable.

    sigma_cr = k * pi^2 * E * (t / b)^2 / (12 * (1 - nu^2)) solved for
    b, with k default 4.0 (long plate, simply supported edges, axial
    compression). Raises ValueError on non-positive skin thickness,
    modulus, allowable, or k, or on a Poisson ratio outside the open
    interval (0, 0.5).
    """
    if skin_thickness_m <= 0:
        raise ValueError(
            "skin thickness must be > 0 m, got %r" % (skin_thickness_m,)
        )
    if modulus_pa <= 0:
        raise ValueError("modulus must be > 0 Pa, got %r" % (modulus_pa,))
    if buckling_allowable_pa <= 0:
        raise ValueError(
            "buckling allowable must be > 0 Pa, got %r" % (buckling_allowable_pa,)
        )
    if k <= 0:
        raise ValueError("buckling coefficient k must be > 0, got %r" % (k,))
    if not (0.0 < poisson < 0.5):
        raise ValueError(
            "Poisson ratio must be in (0, 0.5), got %r" % (poisson,)
        )
    denom = 12.0 * (1.0 - poisson * poisson) * buckling_allowable_pa
    return skin_thickness_m * math.pi * math.sqrt(k * modulus_pa / denom)


def frame_pitch(stringer_area_m2, stringer_inertia_m4, modulus_pa, buckling_allowable_pa):
    """Frame pitch L in m from the stringer column buckling length.

    Euler column between frames: sigma_cr = pi^2 * E * I / (A * L^2)
    solved for L. Raises ValueError on non-positive area, inertia,
    modulus, or allowable.
    """
    if stringer_area_m2 <= 0:
        raise ValueError(
            "stringer area must be > 0 m^2, got %r" % (stringer_area_m2,)
        )
    if stringer_inertia_m4 <= 0:
        raise ValueError(
            "stringer inertia must be > 0 m^4, got %r" % (stringer_inertia_m4,)
        )
    if modulus_pa <= 0:
        raise ValueError("modulus must be > 0 Pa, got %r" % (modulus_pa,))
    if buckling_allowable_pa <= 0:
        raise ValueError(
            "buckling allowable must be > 0 Pa, got %r" % (buckling_allowable_pa,)
        )
    return math.pi * math.sqrt(
        modulus_pa * stringer_inertia_m4
        / (stringer_area_m2 * buckling_allowable_pa)
    )


def effective_skin_width(skin_thickness_m, modulus_pa, allowable_pa):
    """Effective skin width b_eff in m: 1.9 * t * sqrt(E / sigma).

    The width of skin that stays effective with the stringer in
    compression. Raises ValueError on non-positive skin thickness,
    modulus, or allowable.
    """
    if skin_thickness_m <= 0:
        raise ValueError(
            "skin thickness must be > 0 m, got %r" % (skin_thickness_m,)
        )
    if modulus_pa <= 0:
        raise ValueError("modulus must be > 0 Pa, got %r" % (modulus_pa,))
    if allowable_pa <= 0:
        raise ValueError("allowable must be > 0 Pa, got %r" % (allowable_pa,))
    return 1.9 * skin_thickness_m * math.sqrt(modulus_pa / allowable_pa)


def stringer_area(
    strip_load_n,
    effective_skin_width_m,
    skin_thickness_m,
    allowable_pa,
):
    """Stringer area in m^2 from the compression strip load.

    A = P / sigma_allowable - b_eff * t, the strip load beyond what
    the effective skin carries. Raises ValueError when the effective
    skin alone carries the strip (result at or below zero) or on
    non-positive inputs.
    """
    if strip_load_n <= 0:
        raise ValueError("strip load must be > 0 N, got %r" % (strip_load_n,))
    if effective_skin_width_m <= 0:
        raise ValueError(
            "effective skin width must be > 0 m, got %r" % (effective_skin_width_m,)
        )
    if skin_thickness_m <= 0:
        raise ValueError(
            "skin thickness must be > 0 m, got %r" % (skin_thickness_m,)
        )
    if allowable_pa <= 0:
        raise ValueError("allowable must be > 0 Pa, got %r" % (allowable_pa,))
    area = strip_load_n / allowable_pa - effective_skin_width_m * skin_thickness_m
    if area <= 0:
        raise ValueError(
            "effective skin alone carries the strip load; "
            "no stringer area required for %r N" % (strip_load_n,)
        )
    return area
