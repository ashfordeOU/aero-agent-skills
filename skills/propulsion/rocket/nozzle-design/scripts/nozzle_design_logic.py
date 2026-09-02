#!/usr/bin/env python3
"""Nozzle design logic: isentropic compressible flow for a rocket nozzle.

Common-knowledge summary (standards-map.yaml, ecss: free ESA download,
reference-only): ECSS space-systems standards frame rocket propulsion
engineering context. The isentropic area-Mach relation, the choked
mass flow through the throat, and the ideal thrust with the pressure
term are standard compressible flow methodology.

Units (ONE pressure convention, all SI base): every pressure in Pa
(chamber P0, exit static Pe, ambient Pa), temperature T0 in K, gas
constant R in J/kg/K, gamma dimensionless, areas in m^2 (throat and
exit), mass flow in kg/s, velocity in m/s, thrust in N.
"""

import math

R_SPECIFIC_AIR = 287.0  # J/kg/K
GAMMA_AIR = 1.4  # dimensionless


def _area_ratio_at_mach(m, gamma):
    """Isentropic area-Mach relation A/A* evaluated at Mach number m."""
    return (
        (1.0 / m)
        * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
        * (1.0 + (gamma - 1.0) / 2.0 * m * m) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
    )


def exit_mach_from_area_ratio(area_ratio, gamma=GAMMA_AIR):
    """Supersonic exit Mach number for a nozzle area ratio A/A*.

    Solves A/A* = (1/M) * ((2/(gamma+1)) * (1 + (gamma-1)/2 * M^2)) ^
    ((gamma+1)/(2*(gamma-1))) for the M > 1 root by bisection on the
    monotonic supersonic branch of the isentropic area-Mach relation.

    Raises ValueError when area_ratio <= 1 (the sonic throat) or when
    gamma <= 1.
    """
    if area_ratio <= 1:
        raise ValueError(
            "area ratio must be > 1 (supersonic branch), got %r" % (area_ratio,)
        )
    if gamma <= 1:
        raise ValueError("gamma must be > 1, got %r" % (gamma,))
    lo = 1.0
    hi = 1.0
    while _area_ratio_at_mach(hi, gamma) < area_ratio:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _area_ratio_at_mach(mid, gamma) < area_ratio:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def mass_flow(p0_pa, t0_k, a_throat_m2, gamma=GAMMA_AIR, r_j_kgk=R_SPECIFIC_AIR):
    """Choked mass flow through the nozzle throat, in kg/s.

    mdot = P0 * A_throat * sqrt(gamma/(R*T0)) * (2/(gamma+1)) ^
    ((gamma+1)/(2*(gamma-1))).

    Raises ValueError when P0, T0, A_throat, gamma - 1, or R is not
    positive.
    """
    if p0_pa <= 0:
        raise ValueError("chamber pressure must be > 0, got %r" % (p0_pa,))
    if t0_k <= 0:
        raise ValueError("chamber temperature must be > 0, got %r" % (t0_k,))
    if a_throat_m2 <= 0:
        raise ValueError("throat area must be > 0, got %r" % (a_throat_m2,))
    if gamma <= 1:
        raise ValueError("gamma must be > 1, got %r" % (gamma,))
    if r_j_kgk <= 0:
        raise ValueError("gas constant must be > 0, got %r" % (r_j_kgk,))
    return (
        p0_pa
        * a_throat_m2
        * math.sqrt(gamma / (r_j_kgk * t0_k))
        * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
    )


def exit_velocity(p0_pa, t0_k, pe_pa, gamma=GAMMA_AIR, r_j_kgk=R_SPECIFIC_AIR):
    """Ideal isentropic exit velocity, in m/s.

    ve = sqrt(2*gamma*R*T0/(gamma-1) * (1 - (Pe/P0)^((gamma-1)/gamma))).

    Raises ValueError when P0, T0, or Pe is not positive, when Pe
    exceeds P0, when gamma <= 1, or when R <= 0.
    """
    if p0_pa <= 0:
        raise ValueError("chamber pressure must be > 0, got %r" % (p0_pa,))
    if t0_k <= 0:
        raise ValueError("chamber temperature must be > 0, got %r" % (t0_k,))
    if pe_pa <= 0:
        raise ValueError("exit pressure must be > 0, got %r" % (pe_pa,))
    if pe_pa > p0_pa:
        raise ValueError(
            "exit pressure cannot exceed chamber pressure, got %r > %r" % (pe_pa, p0_pa)
        )
    if gamma <= 1:
        raise ValueError("gamma must be > 1, got %r" % (gamma,))
    if r_j_kgk <= 0:
        raise ValueError("gas constant must be > 0, got %r" % (r_j_kgk,))
    return math.sqrt(
        (2.0 * gamma * r_j_kgk * t0_k / (gamma - 1.0))
        * (1.0 - (pe_pa / p0_pa) ** ((gamma - 1.0) / gamma))
    )


def ideal_thrust(mdot_kgs, ve_ms, pe_pa, pa_pa, ae_m2):
    """Ideal nozzle thrust, in N: F = mdot*ve + (Pe - Pa)*Ae.

    The pressure term (Pe - Pa)*Ae is positive for an underexpanded
    nozzle (Pe > Pa) and negative for an overexpanded nozzle (Pe < Pa).

    Raises ValueError when mdot or ve is negative, when Pe or Pa is not
    positive, or when Ae is negative.
    """
    if mdot_kgs < 0:
        raise ValueError("mass flow must be >= 0, got %r" % (mdot_kgs,))
    if ve_ms < 0:
        raise ValueError("exit velocity must be >= 0, got %r" % (ve_ms,))
    if pe_pa <= 0:
        raise ValueError("exit pressure must be > 0, got %r" % (pe_pa,))
    if pa_pa <= 0:
        raise ValueError("ambient pressure must be > 0, got %r" % (pa_pa,))
    if ae_m2 < 0:
        raise ValueError("exit area must be >= 0, got %r" % (ae_m2,))
    return mdot_kgs * ve_ms + (pe_pa - pa_pa) * ae_m2


def optimum_expansion(p0_pa, pe_pa, pa_pa):
    """Expansion verdict of the nozzle against the ambient pressure.

    Returns "over" when Pe < Pa (overexpanded, pressure term negative),
    "under" when Pe > Pa (underexpanded, pressure term positive), and
    "optimum" when Pe == Pa (matched expansion).

    Raises ValueError when P0, Pe, or Pa is not positive, or when Pe
    exceeds the chamber pressure P0.
    """
    if p0_pa <= 0:
        raise ValueError("chamber pressure must be > 0, got %r" % (p0_pa,))
    if pe_pa <= 0:
        raise ValueError("exit pressure must be > 0, got %r" % (pe_pa,))
    if pa_pa <= 0:
        raise ValueError("ambient pressure must be > 0, got %r" % (pa_pa,))
    if pe_pa > p0_pa:
        raise ValueError(
            "exit pressure cannot exceed chamber pressure, got %r > %r" % (pe_pa, p0_pa)
        )
    if pe_pa < pa_pa:
        return "over"
    if pe_pa > pa_pa:
        return "under"
    return "optimum"
