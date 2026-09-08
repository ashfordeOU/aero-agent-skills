#!/usr/bin/env python3
"""Crack-tip plastic-zone correction logic (common engineering methodology).

Common-knowledge summary (standards-map.yaml, mmpsd): the classical Irwin
single-pass plastic-zone correction estimates the effective crack length
a_eff = a + r_p that a linear-elastic crack tip model needs to account for
the small zone of yielded material ahead of the tip, and the Dugdale
strip-yield model gives the exact closed-form zone for a center crack in
an infinite sheet. Both corrections feed a corrected stress intensity
K_eff at the effective crack, and the small-scale-yielding size rule
(the same 2.5*(K/sigma_ys)^2 arithmetic the ASTM E399 plane-strain
validity rule uses) judges whether the underlying linear-elastic result
still applies.

Units: stresses in MPa, crack sizes and zones in meters, so K and K_eff
are in MPa*sqrt(m). All functions raise ValueError on non-physical
inputs.
"""

import math

COEF_IRWIN_PS = 1.0 / math.pi
COEF_IRWIN_PE = 1.0 / (3.0 * math.pi)
COEF_DUGDALE_SSY = math.pi / 8.0
SIZE_RULE_FACTOR = 2.5
RHO_OVER_RP_PS = COEF_DUGDALE_SSY / COEF_IRWIN_PS

_PLANE_STRESS = "plane-stress"
_PLANE_STRAIN = "plane-strain"


def _check_positive(value, name):
    if value <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def stress_intensity(sigma_mpa, a_m, y):
    """K = y*sigma*sqrt(pi*a) in MPa*sqrt(m)."""
    _check_positive(sigma_mpa, "sigma_mpa")
    _check_positive(a_m, "a_m")
    _check_positive(y, "y")
    return y * sigma_mpa * math.sqrt(math.pi * a_m)


def irwin_plastic_zone(k_mpa_sqrtm, sigma_ys_mpa, constraint):
    """Irwin plastic-zone radius r_p in meters for the given constraint state."""
    _check_positive(k_mpa_sqrtm, "k_mpa_sqrtm")
    _check_positive(sigma_ys_mpa, "sigma_ys_mpa")
    if constraint == _PLANE_STRESS:
        coef = COEF_IRWIN_PS
    elif constraint == _PLANE_STRAIN:
        coef = COEF_IRWIN_PE
    else:
        raise ValueError(
            "constraint must be 'plane-stress' or 'plane-strain', got %r" % (constraint,)
        )
    return coef * (k_mpa_sqrtm / sigma_ys_mpa) ** 2


def effective_crack_length(a_m, r_p_m):
    """a_eff = a + r_p in meters."""
    _check_positive(a_m, "a_m")
    if r_p_m < 0:
        raise ValueError("r_p_m must be >= 0, got %r" % (r_p_m,))
    return a_m + r_p_m


def irwin_effective_correction(sigma_mpa, a_m, y, sigma_ys_mpa, constraint):
    """Single-pass Irwin effective-crack correction: r_p from the uncorrected
    elastic K, a_eff = a + r_p, K_eff at a_eff."""
    k = stress_intensity(sigma_mpa, a_m, y)
    r_p = irwin_plastic_zone(k, sigma_ys_mpa, constraint)
    a_eff = effective_crack_length(a_m, r_p)
    k_eff = stress_intensity(sigma_mpa, a_eff, y)
    return {
        "k_mpa_sqrtm": k,
        "r_p_m": r_p,
        "a_eff_m": a_eff,
        "k_eff_mpa_sqrtm": k_eff,
        "k_eff_over_k": k_eff / k,
    }


def dugdale_strip_zone(a_m, sigma_mpa, sigma_0_mpa):
    """Exact Dugdale strip-yield zone rho = a*(sec(pi*sigma/(2*sigma_0)) - 1)
    for the infinite-sheet center crack, in meters."""
    _check_positive(a_m, "a_m")
    _check_positive(sigma_mpa, "sigma_mpa")
    _check_positive(sigma_0_mpa, "sigma_0_mpa")
    if sigma_mpa >= sigma_0_mpa:
        raise ValueError(
            "sigma_mpa must be < sigma_0_mpa (strip-yield zone undefined at or "
            "beyond full-strip yield), got sigma=%r sigma_0=%r" % (sigma_mpa, sigma_0_mpa)
        )
    sec = 1.0 / math.cos(math.pi * sigma_mpa / (2.0 * sigma_0_mpa))
    return a_m * (sec - 1.0)


def dugdale_ssy_zone(k_mpa_sqrtm, sigma_0_mpa):
    """Dugdale small-scale-yielding asymptote rho_ssy = (pi/8)*(k/sigma_0)^2."""
    _check_positive(k_mpa_sqrtm, "k_mpa_sqrtm")
    _check_positive(sigma_0_mpa, "sigma_0_mpa")
    return COEF_DUGDALE_SSY * (k_mpa_sqrtm / sigma_0_mpa) ** 2


def dugdale_effective_correction(sigma_mpa, a_m, sigma_0_mpa):
    """Full Dugdale effective-crack correction for a center crack (Y = 1)."""
    k = stress_intensity(sigma_mpa, a_m, 1.0)
    rho = dugdale_strip_zone(a_m, sigma_mpa, sigma_0_mpa)
    a_eff = effective_crack_length(a_m, rho)
    k_eff = stress_intensity(sigma_mpa, a_eff, 1.0)
    return {
        "k_mpa_sqrtm": k,
        "rho_m": rho,
        "a_eff_m": a_eff,
        "k_eff_mpa_sqrtm": k_eff,
        "k_eff_over_k": k_eff / k,
    }


def sxy_validity(k_mpa_sqrtm, sigma_ys_mpa, a_m):
    """Small-scale-yielding (LEFM-validity) verdict from the applied-K size rule."""
    _check_positive(k_mpa_sqrtm, "k_mpa_sqrtm")
    _check_positive(sigma_ys_mpa, "sigma_ys_mpa")
    _check_positive(a_m, "a_m")
    required_a_m = SIZE_RULE_FACTOR * (k_mpa_sqrtm / sigma_ys_mpa) ** 2
    r_p_ps = irwin_plastic_zone(k_mpa_sqrtm, sigma_ys_mpa, _PLANE_STRESS)
    r_p_pe = irwin_plastic_zone(k_mpa_sqrtm, sigma_ys_mpa, _PLANE_STRAIN)
    return {
        "required_a_m": required_a_m,
        "a_over_required": a_m / required_a_m,
        "r_p_ps_over_a": r_p_ps / a_m,
        "r_p_pe_over_a": r_p_pe / a_m,
        "valid": a_m >= required_a_m,
    }
