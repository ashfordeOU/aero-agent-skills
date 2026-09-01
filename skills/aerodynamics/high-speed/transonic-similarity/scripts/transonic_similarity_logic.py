#!/usr/bin/env python3
"""Transonic similarity logic: compressibility corrections (stdlib only).

Common-knowledge summary (standards-map.yaml, naca-tr-824: reference
data): linearized compressible-flow theory gives the Prandtl-Glauert
factor 1 / sqrt(1 - M^2) for thin airfoils at subsonic Mach numbers.
The Karman-Tsien correction extends the pressure coefficient toward
M ~ 0.85:
  C_p = C_p0 / (sqrt(1 - M^2) + (M^2 / (1 + sqrt(1 - M^2))) * C_p0 / 2)
The transonic similarity parameter K = (1 - M^2) / tau^(2/3) groups
thickness-ratio and Mach effects near M = 1. The critical pressure
coefficient (isentropic sonic limit) at freestream Mach M is
  C_p* = (2/(gamma M^2)) * (((1 + (gamma-1)/2 M^2)/((gamma+1)/2))^(gamma/(gamma-1)) - 1)
and the critical Mach number solves C_p0 / sqrt(1 - M^2) = C_p*(M).
"""

import math

_GAMMA_DEFAULT = 1.4


def _check_mach(M, allow_one=False):
    if M < 0.0:
        raise ValueError("Mach number must be >= 0, got %r" % (M,))
    if M > 1.0 or (M == 1.0 and not allow_one):
        raise ValueError("Mach number must be < 1, got %r" % (M,))


def _check_gamma(gamma):
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must be > 1, got %r" % (gamma,))


def prandtl_glauert_factor(M):
    """Prandtl-Glauert compressibility factor 1 / sqrt(1 - M^2).

    Applies to thin-airfoil perturbation quantities below M ~ 0.7.
    """
    _check_mach(M)
    return 1.0 / math.sqrt(1.0 - M * M)


def prandtl_glauert_correction(cp0, M):
    """Incompressible pressure coefficient corrected by Prandtl-Glauert."""
    return cp0 * prandtl_glauert_factor(M)


def karman_tsien_correction(cp0, M):
    """Pressure coefficient corrected by the Karman-Tsien rule.

    C_p = C_p0 / (sqrt(1 - M^2) + (M^2 / (1 + sqrt(1 - M^2))) * C_p0 / 2)
    """
    _check_mach(M)
    root = math.sqrt(1.0 - M * M)
    return cp0 / (root + (M * M / (1.0 + root)) * cp0 / 2.0)


def corrected_lift_slope(a0, M):
    """Section lift-curve slope a0 corrected by the Prandtl-Glauert rule."""
    return a0 * prandtl_glauert_factor(M)


def transonic_similarity_parameter(M, tau):
    """Transonic similarity parameter K = (1 - M^2) / tau^(2/3).

    tau is the thickness ratio in (0, 1); M in [0, 1]. Equal K groups
    thin configurations with similar transonic pressure fields.
    """
    _check_mach(M, allow_one=True)
    if not (0.0 < tau < 1.0):
        raise ValueError("thickness ratio tau must be in (0, 1), got %r" % (tau,))
    return (1.0 - M * M) / (tau ** (2.0 / 3.0))


def critical_pressure_coefficient(M, gamma=_GAMMA_DEFAULT):
    """Isentropic pressure coefficient at which local flow reaches M = 1.

    C_p* = (2/(gamma M^2)) * (((1 + (gamma-1)/2 M^2)/((gamma+1)/2))^(gamma/(gamma-1)) - 1)
    """
    _check_mach(M, allow_one=True)
    if M == 0.0:
        raise ValueError("Mach number must be > 0 for C_p*, got 0")
    _check_gamma(gamma)
    g = gamma
    term = (1.0 + (g - 1.0) / 2.0 * M * M) / (1.0 + (g - 1.0) / 2.0)
    return (2.0 / (g * M * M)) * (term ** (g / (g - 1.0)) - 1.0)


def critical_mach_number(cp_min0, gamma=_GAMMA_DEFAULT, tol=1e-10):
    """Critical Mach number for a given incompressible peak suction C_p0.

    Solves C_p0 / sqrt(1 - M^2) = C_p*(M) by bisection on M in
    [0.02, 0.999]. cp_min0 must be negative (a suction peak); the
    equation has exactly one root below M = 1 for cp_min0 < 0.
    """
    if cp_min0 >= 0.0:
        raise ValueError("peak suction cp_min0 must be negative, got %r" % (cp_min0,))
    _check_gamma(gamma)
    lo, hi = 0.02, 0.999
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lhs = cp_min0 / math.sqrt(1.0 - mid * mid)
        rhs = critical_pressure_coefficient(mid, gamma)
        if lhs - rhs > 0.0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)
