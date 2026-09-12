"""
Critical crack size and residual strength margin — ECSS E-ST-32C clause 7.3.

Implements linear elastic fracture mechanics (LEFM) for:
  - Critical crack half-length at limit load
  - Residual strength at a given crack size
  - Margin of safety against limit-load failure

All stress inputs in MPa, all length inputs in metres.
Fracture toughness K_IC in MPa·sqrt(m).
"""

import math


def compute_critical_crack_half_length(k_ic, geometry_factor, limit_stress):
    """
    Return critical crack half-length a_c (m) at limit load.

    LEFM: K_IC = Y * sigma * sqrt(pi * a_c)
    Solved: a_c = (K_IC / (Y * sigma))^2 / pi

    Args:
        k_ic            : plane-strain fracture toughness, MPa·sqrt(m) (> 0)
        geometry_factor : stress-intensity correction factor Y, dimensionless (> 0)
        limit_stress    : applied limit stress, MPa (> 0)

    Returns:
        Critical crack half-length a_c in metres.

    Raises:
        ValueError if any input is non-positive.
    """
    if k_ic <= 0:
        raise ValueError(f"k_ic must be positive; got {k_ic}")
    if geometry_factor <= 0:
        raise ValueError(f"geometry_factor must be positive; got {geometry_factor}")
    if limit_stress <= 0:
        raise ValueError(f"limit_stress must be positive; got {limit_stress}")

    return (k_ic / (geometry_factor * limit_stress)) ** 2 / math.pi


def compute_residual_strength(k_ic, geometry_factor, crack_half_length):
    """
    Return residual strength sigma_res (MPa) at a given crack size.

    LEFM: sigma_res = K_IC / (Y * sqrt(pi * a))

    Args:
        k_ic              : plane-strain fracture toughness, MPa·sqrt(m) (> 0)
        geometry_factor   : stress-intensity correction factor Y, dimensionless (> 0)
        crack_half_length : assumed crack half-length, m (> 0)

    Returns:
        Residual strength in MPa.

    Raises:
        ValueError if any input is non-positive.
    """
    if k_ic <= 0:
        raise ValueError(f"k_ic must be positive; got {k_ic}")
    if geometry_factor <= 0:
        raise ValueError(f"geometry_factor must be positive; got {geometry_factor}")
    if crack_half_length <= 0:
        raise ValueError(f"crack_half_length must be positive; got {crack_half_length}")

    return k_ic / (geometry_factor * math.sqrt(math.pi * crack_half_length))


def compute_margin_of_safety(residual_strength, limit_stress):
    """
    Return margin of safety MS = sigma_res / sigma_limit - 1.

    MS >= 0 -> adequate residual strength at limit load (pass).
    MS <  0 -> residual strength below limit stress (fail).

    Args:
        residual_strength : residual strength, MPa (>= 0)
        limit_stress      : applied limit stress, MPa (> 0)

    Returns:
        Margin of safety (dimensionless).

    Raises:
        ValueError if limit_stress is non-positive or residual_strength is negative.
    """
    if limit_stress <= 0:
        raise ValueError(f"limit_stress must be positive; got {limit_stress}")
    if residual_strength < 0:
        raise ValueError(f"residual_strength must be non-negative; got {residual_strength}")

    return residual_strength / limit_stress - 1.0


def assess_crack(k_ic, geometry_factor, limit_stress, crack_half_length):
    """
    Full fracture assessment for a single crack, geometry, and material combination.

    Computes critical crack size, residual strength, margin of safety, and
    determines whether the crack is within the safe-crack-size envelope at
    limit load per ECSS E-ST-32C clause 7.3.

    Args:
        k_ic              : plane-strain fracture toughness, MPa·sqrt(m) (> 0)
        geometry_factor   : stress-intensity geometry factor Y, dimensionless (> 0)
        limit_stress      : applied limit stress, MPa (> 0)
        crack_half_length : assumed crack half-length, m (> 0)

    Returns:
        dict with keys:
            critical_crack_half_length_m : float — a_c in metres
            residual_strength_MPa        : float — sigma_res in MPa
            margin_of_safety             : float — MS (dimensionless)
            status                       : str   — "pass" (MS >= 0) or "fail" (MS < 0)
            crack_exceeds_critical       : bool  — True if a >= a_c

    Raises:
        ValueError on non-positive inputs (propagated from sub-functions).
    """
    a_c = compute_critical_crack_half_length(k_ic, geometry_factor, limit_stress)
    sigma_res = compute_residual_strength(k_ic, geometry_factor, crack_half_length)
    ms = compute_margin_of_safety(sigma_res, limit_stress)

    return {
        "critical_crack_half_length_m": a_c,
        "residual_strength_MPa": sigma_res,
        "margin_of_safety": ms,
        "status": "pass" if ms >= 0.0 else "fail",
        "crack_exceeds_critical": crack_half_length >= a_c,
    }
