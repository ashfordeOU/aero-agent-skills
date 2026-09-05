#!/usr/bin/env python3
"""Isentropic flow relations for a perfect gas (pure stdlib, math only).

Converts a Mach number into the isentropic total to static ratios
T0/T, p0/p and rho0/rho of a compressible flow at gamma 1.4, recovers
the Mach number that produces a given area ratio A/A* on either branch
of the area-Mach relation by deterministic bisection, rebuilds total
conditions from a static state and Mach number, and computes the choked
mass flow a passage passes at its sonic throat through the mass flow
parameter.

The module works on the standard isentropic relations for a calorically
perfect gas (NACA-TR-824 methodology, paraphrased summary only). All
inputs are SI (pascal, kelvin, m2) except the unitless Mach number and
area ratio. Non-physical inputs raise ValueError. No RNG anywhere, so
identical inputs return identical bits.

Worked anchors (air, gamma 1.4, R 287.0): at mach 2.0 the ratios are
T0/T = 1.8, p0/p = 7.8244490669, rho0/rho = 4.3469161483 and the area
ratio is A/A* = 1.6875 exactly.
"""

import math

# Module constants (air as the perfect gas, spec values).
GAMMA = 1.4
R = 287.0
MACH_TOL = 1e-12
SUB_LO = 0.05
SUB_HI = 0.99
SUP_LO = 1.01
SUP_HI = 20.0
_MAX_BISECT_ITERS = 200


def total_static_ratios(mach):
    """Return the isentropic total to static ratios at a Mach number.

    dict with keys t0_over_t, p0_over_p and rho0_over_rho where
    t0_over_t = 1 + 0.5 * (GAMMA - 1) * mach**2 and the pressure and
    density ratios follow from the isentropic exponents GAMMA/(GAMMA-1)
    and 1/(GAMMA-1). All three ratios equal 1.0 at mach 0.0. Raises
    ValueError when mach is negative (no negative Mach number).
    """
    if mach < 0.0:
        raise ValueError("mach must be >= 0.0 (no negative Mach number)")
    t0_over_t = 1.0 + 0.5 * (GAMMA - 1.0) * mach * mach
    p0_over_p = t0_over_t ** (GAMMA / (GAMMA - 1.0))
    rho0_over_rho = t0_over_t ** (1.0 / (GAMMA - 1.0))
    return {
        "t0_over_t": t0_over_t,
        "p0_over_p": p0_over_p,
        "rho0_over_rho": rho0_over_rho,
    }


def area_ratio(mach):
    """Return the isentropic area ratio A/A* for a Mach number.

    A/A* = (1/M) * ((2/(GAMMA+1)) * (1 + 0.5*(GAMMA-1)*M^2)) **
    ((GAMMA+1)/(2*(GAMMA-1))) with A* the sonic throat area. The ratio
    is monotone decreasing on the subsonic branch, monotone increasing
    on the supersonic branch and has its minimum 1.0 exactly at mach
    1.0. Raises ValueError when mach <= 0 (no zero or negative Mach
    number in the area-Mach relation).
    """
    if mach <= 0.0:
        raise ValueError("mach must be > 0.0 (area-Mach relation needs M > 0)")
    base = (2.0 / (GAMMA + 1.0)) * (1.0 + 0.5 * (GAMMA - 1.0) * mach * mach)
    exponent = (GAMMA + 1.0) / (2.0 * (GAMMA - 1.0))
    return (1.0 / mach) * base ** exponent


def mach_from_area_ratio(aa, subsonic=True):
    """Recover the Mach number that produces area ratio A/A* = aa.

    Deterministic bisection of f(M) = area_ratio(M) - aa over a fixed
    bracket: [SUB_LO, SUB_HI] = [0.05, 0.99] for the subsonic (low
    branch) root and [SUP_LO, SUP_HI] = [1.01, 20.0] for the supersonic
    (high branch) root, halving until the bracket width falls below
    MACH_TOL = 1e-12 (capped at 200 iterations, no RNG) and returning
    the bracket midpoint. Edge and domain rules, in order:

    - aa < 1.0 raises ValueError (the sonic-throat floor, no physical
      area ratio below 1.0).
    - aa == 1.0 returns 1.0 exactly on either branch.
    - A subsonic aa below area_ratio(SUB_HI) re-brackets on [SUB_HI,
      1.0]; a supersonic aa below area_ratio(SUP_LO) re-brackets on
      [1.0, SUP_LO], keeping the near-sonic roots inside a sign-change
      bracket.
    - A subsonic aa at or above area_ratio(SUB_LO) = 11.591443867187
      raises ValueError (root below the 0.05 bracket floor, documented
      domain limit).
    - A supersonic aa above area_ratio(SUP_HI) = 15377.343750000022
      raises ValueError (root above the 20.0 bracket ceiling,
      documented domain limit).
    """
    if aa < 1.0:
        raise ValueError("A/A* must be >= 1.0 (sonic throat floor at mach 1.0)")
    if aa == 1.0:
        return 1.0
    if subsonic:
        near_sonic = area_ratio(SUB_HI)  # ~1.0000856, root just below 1.0
        floor = area_ratio(SUB_LO)  # 11.591443867187 at M = 0.05
        if aa < near_sonic:
            lo, hi = SUB_HI, 1.0
        elif aa >= floor:
            raise ValueError(
                "A/A* above 11.591443867187 has no subsonic root above "
                "the 0.05 bracket floor"
            )
        else:
            lo, hi = SUB_LO, SUB_HI
    else:
        near_sonic = area_ratio(SUP_LO)  # ~1.0000782, root just above 1.0
        ceiling = area_ratio(SUP_HI)  # 15377.343750000022 at M = 20.0
        if aa < near_sonic:
            lo, hi = 1.0, SUP_LO
        elif aa > ceiling:
            raise ValueError(
                "A/A* above 15377.343750000022 has no supersonic root "
                "below the 20.0 bracket ceiling"
            )
        else:
            lo, hi = SUP_LO, SUP_HI
    f_lo = area_ratio(lo) - aa
    for _ in range(_MAX_BISECT_ITERS):
        if hi - lo < MACH_TOL:
            break
        mid = 0.5 * (lo + hi)
        f_mid = area_ratio(mid) - aa
        if (f_mid < 0.0) == (f_lo < 0.0):
            lo = mid  # root lies above mid, keep the f_lo sign side
        else:
            hi = mid
    return 0.5 * (lo + hi)


def static_to_total(p_static, t_static, mach):
    """Rebuild total conditions from a static state and Mach number.

    dict with keys p0 and t0 where p0 = p_static * p0_over_p and t0 =
    t_static * t0_over_t from the same closed isentropic forms used by
    total_static_ratios, so the round trip with total_static_ratios is
    exact to floating point. Raises ValueError when p_static <= 0,
    t_static <= 0 or mach < 0.
    """
    if p_static <= 0.0:
        raise ValueError("p_static must be > 0.0")
    if t_static <= 0.0:
        raise ValueError("t_static must be > 0.0")
    ratios = total_static_ratios(mach)  # raises on mach < 0
    return {
        "p0": p_static * ratios["p0_over_p"],
        "t0": t_static * ratios["t0_over_t"],
    }


def choked_mass_flow(p0, t0, area_star):
    """Return the choked mass flow mdot in kg/s at a sonic throat.

    mdot = MFP * p0 * area_star / sqrt(t0) with the mass flow parameter
    MFP = sqrt(GAMMA / R) * (2 / (GAMMA + 1)) ** ((GAMMA + 1) / (2 *
    (GAMMA - 1))) = 0.0404184199 kg sqrt(K) / (Pa s), for p0 in Pa, t0
    in K and area_star in m2 (the standard choked flow relation for a
    sonic throat, name and paraphrase only). Raises ValueError when
    p0 <= 0, t0 <= 0 or area_star <= 0.
    """
    if p0 <= 0.0:
        raise ValueError("p0 must be > 0.0 (total pressure)")
    if t0 <= 0.0:
        raise ValueError("t0 must be > 0.0 (total temperature)")
    if area_star <= 0.0:
        raise ValueError("area_star must be > 0.0 (sonic throat area)")
    mfp = math.sqrt(GAMMA / R) * (2.0 / (GAMMA + 1.0)) ** (
        (GAMMA + 1.0) / (2.0 * (GAMMA - 1.0))
    )
    return mfp * p0 * area_star / math.sqrt(t0)
