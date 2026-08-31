#!/usr/bin/env python3
"""Residual strength logic, linear-elastic fracture mechanics (paraphrase,
common knowledge).

UNITS CONVENTION (single convention, used everywhere in this module):
  sigma   in MPa (megapascals)
  a       in meters
  K, Kc   in MPa*sqrt(m)  (mega-pascal times square-root meter)

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): FAR-25.571 damage tolerance practice requires
residual strength evaluation of damaged structure; the residual strength
is the highest stress a cracked structure carries before fracture, and
it must stay above the limit load at the assumed damage size. The mode I
stress intensity factor K = beta * sigma * sqrt(pi * a) scales the
crack-tip stress field; fracture occurs when K reaches the material
fracture toughness Kc, and the crack length at which the applied stress
drives K to Kc is the critical crack length. The residual strength
sigma_res = Kc / (beta * sqrt(pi * a)) falls with the inverse square
root of the crack length.
"""

import math


def residual_strength(kc_mpa_sqrtm, beta, a_m):
    """Residual strength sigma_res = Kc / (beta * sqrt(pi * a)).

    Kc in MPa*sqrt(m), beta dimensionless, a in meters; returns the
    residual strength in MPa. Raises ValueError when Kc, the geometry
    factor, or the crack length is not strictly positive."""
    if kc_mpa_sqrtm <= 0:
        raise ValueError(
            "fracture toughness must be > 0, got %r" % (kc_mpa_sqrtm,)
        )
    if beta <= 0:
        raise ValueError("geometry factor must be > 0, got %r" % (beta,))
    if a_m <= 0:
        raise ValueError("crack length must be > 0, got %r" % (a_m,))
    return kc_mpa_sqrtm / (beta * math.sqrt(math.pi * a_m))


def critical_crack_length(kc_mpa_sqrtm, beta, sigma_applied_mpa):
    """Critical crack length a_c = (Kc / (beta * sigma))**2 / pi.

    Kc in MPa*sqrt(m), sigma in MPa; returns meters. This is the crack
    length at which the applied stress drives the stress intensity
    factor up to Kc. Raises ValueError when Kc, the geometry factor, or
    the applied stress is not strictly positive."""
    if kc_mpa_sqrtm <= 0:
        raise ValueError(
            "fracture toughness must be > 0, got %r" % (kc_mpa_sqrtm,)
        )
    if beta <= 0:
        raise ValueError("geometry factor must be > 0, got %r" % (beta,))
    if sigma_applied_mpa <= 0:
        raise ValueError(
            "applied stress must be > 0, got %r" % (sigma_applied_mpa,)
        )
    return (kc_mpa_sqrtm / (beta * sigma_applied_mpa)) ** 2 / math.pi


def residual_margin(kc_mpa_sqrtm, beta, a_m, sigma_limit_mpa):
    """Margin of the residual strength over the limit load.

    margin = sigma_res / sigma_limit; sigma_res from residual_strength.
    Returns a dict with the residual strength ("residual_mpa"), the
    limit stress ("limit_mpa"), the dimensionless margin, and the
    boolean verdict "ok" (True when margin >= 1.0, that is, the cracked
    structure still carries the limit load). Raises ValueError when any
    input is not strictly positive."""
    if sigma_limit_mpa <= 0:
        raise ValueError(
            "limit stress must be > 0, got %r" % (sigma_limit_mpa,)
        )
    sigma_res = residual_strength(kc_mpa_sqrtm, beta, a_m)
    margin = sigma_res / sigma_limit_mpa
    return {
        "residual_mpa": sigma_res,
        "limit_mpa": sigma_limit_mpa,
        "margin": margin,
        "ok": margin >= 1.0,
    }


def crack_ok(kc_mpa_sqrtm, beta, a_m, sigma_applied_mpa):
    """Verdict on the applied stress intensity factor against Kc.

    K_I = beta * sigma * sqrt(pi * a); returns a dict with the applied
    stress intensity factor ("k_i_mpa_sqrtm"), the fracture toughness
    ("kc_mpa_sqrtm"), and the boolean verdict "ok" (True when
    K_I <= Kc, that is, the crack does not fracture at the applied
    stress). Raises ValueError when any input is not strictly
    positive."""
    if kc_mpa_sqrtm <= 0:
        raise ValueError(
            "fracture toughness must be > 0, got %r" % (kc_mpa_sqrtm,)
        )
    if beta <= 0:
        raise ValueError("geometry factor must be > 0, got %r" % (beta,))
    if a_m <= 0:
        raise ValueError("crack length must be > 0, got %r" % (a_m,))
    if sigma_applied_mpa <= 0:
        raise ValueError(
            "applied stress must be > 0, got %r" % (sigma_applied_mpa,)
        )
    k_i = beta * sigma_applied_mpa * math.sqrt(math.pi * a_m)
    return {
        "k_i_mpa_sqrtm": k_i,
        "kc_mpa_sqrtm": kc_mpa_sqrtm,
        "ok": k_i <= kc_mpa_sqrtm,
    }
