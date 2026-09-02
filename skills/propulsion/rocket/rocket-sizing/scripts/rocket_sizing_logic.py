#!/usr/bin/env python3
"""Rocket sizing logic: rocket equation delta-v, mass ratio,
propellant mass, and staging delta-v (common propulsion methodology).

Common-knowledge summary (standards-map.yaml, ecss: free ESA download,
reference-only): ECSS space-systems standards frame launch-vehicle
engineering context. The rocket equation itself is standard propulsion
methodology: delta-v = g0 * Isp * ln(m0 / mf). Units: specific impulse
in seconds, masses in kg, delta-v in m/s, g0 = 9.80665 m/s^2.
"""

import math


def rocket_equation_delta_v(isp_s, m0_kg, mf_kg, g0=9.80665):
    """Delta-v from the ideal rocket equation, g0 * Isp * ln(m0 / mf).

    Raises ValueError when Isp is not positive, when the initial or
    final mass is not positive, or when the final mass is not below
    the initial mass.
    """
    if isp_s <= 0:
        raise ValueError("specific impulse must be > 0, got %r" % (isp_s,))
    if m0_kg <= 0:
        raise ValueError("initial mass must be > 0, got %r" % (m0_kg,))
    if mf_kg <= 0:
        raise ValueError("final mass must be > 0, got %r" % (mf_kg,))
    if mf_kg >= m0_kg:
        raise ValueError(
            "final mass must be < initial mass, got %r >= %r" % (mf_kg, m0_kg)
        )
    return g0 * isp_s * math.log(m0_kg / mf_kg)


def mass_ratio_from_delta_v(delta_v, isp_s, g0=9.80665):
    """Mass ratio m0/mf required for a delta-v at a given Isp.

    Raises ValueError for a negative delta-v or a non-positive Isp.
    """
    if delta_v < 0:
        raise ValueError("delta-v must be >= 0, got %r" % (delta_v,))
    if isp_s <= 0:
        raise ValueError("specific impulse must be > 0, got %r" % (isp_s,))
    return math.exp(delta_v / (g0 * isp_s))


def propellant_mass(m0_kg, mf_kg):
    """Propellant mass burned, m0 - mf.

    Raises ValueError when the initial or final mass is not positive,
    or when the final mass is not below the initial mass.
    """
    if m0_kg <= 0:
        raise ValueError("initial mass must be > 0, got %r" % (m0_kg,))
    if mf_kg <= 0:
        raise ValueError("final mass must be > 0, got %r" % (mf_kg,))
    if mf_kg >= m0_kg:
        raise ValueError(
            "final mass must be < initial mass, got %r >= %r" % (mf_kg, m0_kg)
        )
    return m0_kg - mf_kg


def total_stage_delta_v(stage_delta_vs):
    """Total delta-v across the stages of a multistage vehicle.

    Raises ValueError for an empty stage list or a negative stage
    delta-v.
    """
    if not stage_delta_vs:
        raise ValueError("stage delta-v list must not be empty")
    total = 0.0
    for dv in stage_delta_vs:
        if dv < 0:
            raise ValueError("stage delta-v must be >= 0, got %r" % (dv,))
        total += dv
    return total
