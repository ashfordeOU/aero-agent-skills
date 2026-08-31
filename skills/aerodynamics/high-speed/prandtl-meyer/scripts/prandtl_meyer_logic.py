#!/usr/bin/env python3
"""Prandtl-Meyer expansion relations for compressible flow (stdlib only).

The Prandtl-Meyer function nu(M) gives the total angle through which a
supersonic flow must turn away from itself to accelerate from Mach 1 to
Mach M, in radians:

  nu(M) = sqrt((gamma+1)/(gamma-1)) * atan(sqrt((gamma-1)/(gamma+1) *
          (M^2 - 1))) - atan(sqrt(M^2 - 1))

The function is undefined for subsonic Mach numbers: nu(M) is the angle
of an isentropic expansion fan, and only supersonic flow (M >= 1) has
one. M < 1 raises ValueError. gamma defaults to 1.4 (air).

The total turning angle of an expansion fan is the difference of the
Prandtl-Meyer function across the fan: delta = nu(M2) - nu(M1) for a
flow turning away from itself. mach_after_expansion inverts this with
bisection on nu(M) - (nu(M1) + delta) = 0.

Analytic check: nu(1.0) = 0.0 (the fan collapses to zero width at the
sonic point); nu(2.0) with gamma = 1.4 is 0.460414 rad, which is
26.3799 deg (Anderson, Modern Compressible Flow, Table A.5 gives
nu = 26.380 deg at M = 2.0).
"""

import math


def _validate(M, gamma):
    """Reject nonphysical inputs: M must be supersonic, gamma > 1."""
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1 (specific heat ratio)")
    if M < 1.0:
        raise ValueError("M must be >= 1 (Prandtl-Meyer function is undefined below Mach 1)")


def prandtl_meyer_function(M, gamma=1.4):
    """Prandtl-Meyer expansion angle nu(M) in radians (unitless input).

    nu(M) = sqrt((gamma+1)/(gamma-1)) * atan(sqrt((gamma-1)/(gamma+1) *
            (M^2 - 1))) - atan(sqrt(M^2 - 1)).
    nu(1.0) = 0.0 and nu grows monotonically with M: an expansion fan
    turns the flow away from itself and accelerates it.
    """
    _validate(M, gamma)
    term = math.sqrt((gamma - 1.0) / (gamma + 1.0) * (M * M - 1.0))
    return math.sqrt((gamma + 1.0) / (gamma - 1.0)) * math.atan(term) - math.atan(
        math.sqrt(M * M - 1.0)
    )


def flow_turn_angle(M1, M2, gamma=1.4):
    """Total turning angle nu(M2) - nu(M1) in radians (unitless).

    The angle through which a supersonic flow turns away from itself
    across an expansion fan between Mach numbers M1 and M2, both >= 1.
    Positive for M2 > M1 (expansion), negative for M2 < M1 (compression,
    which is not a Prandtl-Meyer fan).
    """
    _validate(M1, gamma)
    _validate(M2, gamma)
    return prandtl_meyer_function(M2, gamma) - prandtl_meyer_function(M1, gamma)


def mach_after_expansion(M1, turning_angle_deg, gamma=1.4, bracket=(1.0, 50.0)):
    """Downstream Mach number M2 after the flow turns by a given angle.

    Solves nu(M2) = nu(M1) + delta for M2 by bisection on the bracket
    [1, 50], where delta is turning_angle_deg converted to radians.
    The upstream flow must be supersonic (M1 >= 1) and the turning angle
    must be reachable within the bracket; both violations raise
    ValueError. Deterministic, offline, stdlib only.
    """
    _validate(M1, gamma)
    delta = math.radians(turning_angle_deg)
    target = prandtl_meyer_function(M1, gamma) + delta
    lo, hi = bracket
    if lo < 1.0:
        raise ValueError("lower bracket must be >= 1 (M is undefined below Mach 1)")
    if target > prandtl_meyer_function(hi, gamma):
        raise ValueError(
            "turning angle too large for the Mach bracket: nu(M2) would exceed nu(%g)"
            % hi
        )
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if prandtl_meyer_function(mid, gamma) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def expansion_pressure_ratio(M1, M2, gamma=1.4):
    """Static pressure ratio p2/p1 across the expansion fan (unitless).

    Isentropic relation p/p0 = (1 + (gamma-1)/2 * M^2)^(-gamma/(gamma-1))
    with the same stagnation pressure p0 before and after the fan:
    p2/p1 = pr(M2) / pr(M1), always < 1 for M2 > M1. Both Mach numbers
    must be >= 1.
    """
    _validate(M1, gamma)
    _validate(M2, gamma)

    def _p_over_p0(M):
        return (1.0 + (gamma - 1.0) / 2.0 * M * M) ** (-gamma / (gamma - 1.0))

    return _p_over_p0(M2) / _p_over_p0(M1)


def expansion_properties(M1, turning_angle_deg, gamma=1.4):
    """Downstream state after the expansion fan (unitless).

    Returns the dict {m2, turning_angle_deg, pressure_ratio_p2_p1} for
    the flow turning away from itself by turning_angle_deg.
    """
    m2 = mach_after_expansion(M1, turning_angle_deg, gamma)
    return {
        "m2": m2,
        "turning_angle_deg": turning_angle_deg,
        "pressure_ratio_p2_p1": expansion_pressure_ratio(M1, m2, gamma),
    }
