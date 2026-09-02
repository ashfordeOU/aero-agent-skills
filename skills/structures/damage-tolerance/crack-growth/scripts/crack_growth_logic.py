#!/usr/bin/env python3
"""Fatigue crack growth logic, linear-elastic fracture mechanics (paraphrase,
common knowledge).

UNITS CONVENTION (single convention, used everywhere in this module):
  sigma   in MPa (megapascals)
  a       in meters
  K, dK   in MPa*sqrt(m)  (mega-pascal times square-root meter)
  C       in (m/cycle) * (MPa*sqrt(m))^-m   Paris coefficient
  m       dimensionless Paris exponent
  da/dN   in m/cycle

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): FAR-25.571 damage tolerance practice requires
residual strength evaluation of damage-tolerant structure with cracks
growing under repeated loads. The mode I stress intensity factor
K = Y * sigma * sqrt(pi * a) scales the crack-tip stress field; the
Paris law da/dN = C * dK**m gives the crack growth rate per cycle
with material constants C and m fitted from da/dN testing. Crack
growth life runs from the initial detectable crack size to the
critical size at which residual strength falls below limit load.
"""

import math


def stress_intensity(sigma_mpa, a_m, y=1.12):
    """Mode I stress intensity factor K = Y * sigma * sqrt(pi * a).

    sigma in MPa, a in meters; returns K in MPa*sqrt(m). Raises
    ValueError when sigma, the crack length, or the geometry factor
    is not strictly positive."""
    if sigma_mpa <= 0:
        raise ValueError("stress must be > 0, got %r" % (sigma_mpa,))
    if a_m <= 0:
        raise ValueError("crack length must be > 0, got %r" % (a_m,))
    if y <= 0:
        raise ValueError("geometry factor must be > 0, got %r" % (y,))
    return y * sigma_mpa * math.sqrt(math.pi * a_m)


def paris_dadN(c, m, dk_mpa):
    """Paris law crack growth rate da/dN = C * dK**m.

    C in (m/cycle)*(MPa*sqrt(m))^-m, dK in MPa*sqrt(m); returns
    da/dN in m/cycle. Raises ValueError when C or the stress
    intensity range is not strictly positive."""
    if c <= 0:
        raise ValueError("Paris coefficient C must be > 0, got %r" % (c,))
    if dk_mpa <= 0:
        raise ValueError("stress intensity range must be > 0, got %r" % (dk_mpa,))
    return c * dk_mpa ** m


def crack_growth_per_cycle(c, m, dk_mpa, cycles):
    """Crack extension over a cycle block at constant da/dN.

    C in (m/cycle)*(MPa*sqrt(m))^-m, dK in MPa*sqrt(m); returns
    meters. Raises ValueError when C or dK is not strictly
    positive, or when cycles is negative."""
    if c <= 0:
        raise ValueError("Paris coefficient C must be > 0, got %r" % (c,))
    if dk_mpa <= 0:
        raise ValueError("stress intensity range must be > 0, got %r" % (dk_mpa,))
    if cycles < 0:
        raise ValueError("cycles must be >= 0, got %r" % (cycles,))
    return cycles * c * dk_mpa ** m


def cycles_to_grow(c, m, dk_mpa, a0_m, a_critical_m):
    """Cycles to grow the crack from a0 to a_critical (constant-amplitude
    approximation with a fixed stress intensity range).

    C in (m/cycle)*(MPa*sqrt(m))^-m, dK in MPa*sqrt(m), crack sizes
    in meters; returns cycles. Raises ValueError when C or dK is not
    strictly positive, or when the critical crack length does not
    exceed the initial crack length."""
    if c <= 0:
        raise ValueError("Paris coefficient C must be > 0, got %r" % (c,))
    if dk_mpa <= 0:
        raise ValueError("stress intensity range must be > 0, got %r" % (dk_mpa,))
    if a_critical_m <= a0_m:
        raise ValueError(
            "critical crack length must exceed initial crack length, "
            "got a0=%r, a_critical=%r" % (a0_m, a_critical_m)
        )
    return (a_critical_m - a0_m) / (c * dk_mpa ** m)
