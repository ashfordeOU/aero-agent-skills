#!/usr/bin/env python3
"""Supercritical airfoil design and analysis logic (paraphrase).

Common-knowledge summary (public-domain textbook content, e.g. Anderson,
Fundamentals of Aerodynamics; Mason, Configuration Aerodynamics; NACA
TR 824 reference-only per standards-map.yaml): a supercritical airfoil
delays drag divergence through a nearly flat upper surface that keeps
the local Mach number barely supersonic over a long region, so the
terminating shock at the rear of the supersonic pocket is weaker than on
a conventional section. Aft loading (camber and loading near the
trailing edge) recovers the lift lost by the flat top, at the price of a
more negative pitching moment. The Korn rule of thumb summarizes the
design trade: drag-divergence Mach M_DD = 0.95 - t/c - C_L/10 for a
supercritical section and M_DD = 0.90 - t/c - C_L/10 for a conventional
section, with t/c the thickness ratio and C_L the cruise lift
coefficient. Above drag divergence wave drag grows roughly with the cube
of (M - M_DD). The terminating shock strength is the static pressure
ratio across a normal shock at the local Mach ahead of it,
p2/p1 = 1 + 2*gamma/(gamma+1)*(M^2 - 1) with gamma = 1.4.
"""

import math

GAMMA = 1.4


def _check_tc(tc):
    if not (0.02 < tc < 0.30):
        raise ValueError("thickness ratio t/c must be in (0.02, 0.30), got %r" % (tc,))


def _check_cl(cl):
    if not (0.0 <= cl < 1.5):
        raise ValueError("cruise lift coefficient must be in [0, 1.5), got %r" % (cl,))


def _check_flight_mach(mach):
    if not (0.5 <= mach < 1.0):
        raise ValueError("flight Mach must be in [0.5, 1), got %r" % (mach,))


def terminating_shock_strength(mach_ahead):
    """Static pressure ratio p2/p1 across the terminating shock.

    Normal shock relation at the local Mach just ahead of the shock that
    closes the upper-surface supersonic pocket. A conventional section
    at M 0.8 accelerates the top surface to about M 1.3 (ratio about
    1.81); the flat top of a supercritical section holds it near M 1.15
    (ratio about 1.38). The weaker terminating shock is the
    wave-drag-reduction mechanism. Local Mach in (1, 2] keeps the result
    in the airfoil terminating-shock band.
    """
    if not (1.0 < mach_ahead <= 2.0):
        raise ValueError(
            "local Mach ahead of the terminating shock must be in (1, 2], got %r"
            % (mach_ahead,)
        )
    return 1.0 + 2.0 * GAMMA / (GAMMA + 1.0) * (mach_ahead ** 2 - 1.0)


def wave_drag_penalty(mach, mdd):
    """Relative wave-drag penalty index above drag divergence.

    Wave drag grows roughly with the cube of (M - M_DD); returns 0.0 at
    or below drag divergence and (M - M_DD)^3 above it. The result is a
    relative index, not an absolute drag coefficient (planform scaling
    is separate). Both inputs must be high-subsonic.
    """
    _check_flight_mach(mach)
    if not (0.5 < mdd < 1.0):
        raise ValueError("drag-divergence Mach must be in (0.5, 1), got %r" % (mdd,))
    excess = mach - mdd
    if excess <= 0.0:
        return 0.0
    return excess ** 3


def drag_divergence_mach(tc, cl, supercritical=True):
    """Drag-divergence Mach number from the Korn rule of thumb.

    M_DD = 0.95 - t/c - C_L/10 for a supercritical section and
    M_DD = 0.90 - t/c - C_L/10 for a conventional section. The 0.05
    offset is the wave-drag-reduction benefit of the flat upper surface
    and aft loading. Raises when the rule leaves the high-subsonic band
    (0.5, 0.95).
    """
    _check_tc(tc)
    _check_cl(cl)
    base = 0.95 if supercritical else 0.90
    mdd = base - tc - cl / 10.0
    if not (0.5 < mdd < 0.95):
        raise ValueError(
            "Korn rule gives drag-divergence Mach %r outside (0.5, 0.95); "
            "check the thickness ratio and cruise lift coefficient" % (mdd,)
        )
    return mdd


def max_thickness_ratio(mach, cl, supercritical=True):
    """Maximum thickness ratio t/c at a given drag-divergence Mach.

    Inverse Korn rule: t/c = base - M - C_L/10 with base 0.95
    (supercritical) or 0.90 (conventional). Raises when no positive
    thickness survives, i.e. the section cannot be built at that Mach.
    """
    _check_flight_mach(mach)
    _check_cl(cl)
    base = 0.95 if supercritical else 0.90
    tc = base - mach - cl / 10.0
    if tc <= 0.02:
        raise ValueError(
            "no viable thickness at M %r, C_L %r for a %s section "
            "(t/c would be %r)"
            % (mach, cl, "supercritical" if supercritical else "conventional", tc)
        )
    return tc


def max_cruise_lift_coefficient(mach, tc, supercritical=True):
    """Maximum cruise lift coefficient at a given Mach and thickness.

    Inverse Korn rule: C_L = 10 * (base - t/c - M) with base 0.95
    (supercritical) or 0.90 (conventional). Raises when the result is
    non-positive: the section hits drag divergence below the flight Mach
    and cannot carry cruise lift there.
    """
    _check_flight_mach(mach)
    _check_tc(tc)
    base = 0.95 if supercritical else 0.90
    cl = 10.0 * (base - tc - mach)
    if cl <= 0.0:
        raise ValueError(
            "no cruise lift at M %r with t/c %r on a %s section "
            "(C_L would be %r)"
            % (mach, tc, "supercritical" if supercritical else "conventional", cl)
        )
    return cl


def aft_loading_moment(supercritical=True):
    """Pitching moment coefficient C_m,ac produced by aft loading.

    Aft loading recovers the lift lost by the flat upper surface but
    shifts the center of pressure rearward, so the section pitching
    moment about the aerodynamic center is more negative: about -0.12
    for a typical supercritical section versus -0.06 for a conventional
    transport section (representative textbook values). The trim drag
    this creates is the price of the wave-drag reduction.
    """
    return -0.12 if supercritical else -0.06
