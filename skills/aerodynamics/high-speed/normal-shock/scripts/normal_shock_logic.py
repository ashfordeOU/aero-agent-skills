#!/usr/bin/env python3
"""Normal shock relations for compressible flow (stdlib only).

All inputs are unitless: the upstream Mach number M1 and the specific
heat ratio gamma. All outputs are unitless ratios. The upstream flow
must be supersonic (M1 > 1) and gamma > 1; violations raise ValueError.
gamma defaults to 1.4 (air).

Textbook check at M1 = 2.0, gamma = 1.4 (Anderson, Modern Compressible
Flow, Table A.2): M2 = 0.5773503, p2/p1 = 4.5, T2/T1 = 1.6875,
rho2/rho1 = 2.6666667, p02/p01 = 0.720875.
"""

import math


def _validate(M1, gamma):
    """Reject nonphysical inputs: M1 must be supersonic, gamma > 1."""
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1 (specific heat ratio)")
    if M1 <= 1.0:
        raise ValueError("M1 must be > 1 (upstream flow must be supersonic)")


def downstream_mach(M1, gamma=1.4):
    """Downstream Mach number M2 across the normal shock (unitless).

    M2 = sqrt((1 + (gamma-1)/2 * M1^2) / (gamma * M1^2 - (gamma-1)/2)).
    M2 < 1 whenever M1 > 1: the shock decelerates the flow to subsonic.
    """
    _validate(M1, gamma)
    num = 1.0 + (gamma - 1.0) / 2.0 * M1 * M1
    den = gamma * M1 * M1 - (gamma - 1.0) / 2.0
    return math.sqrt(num / den)


def pressure_ratio(M1, gamma=1.4):
    """Static pressure ratio p2/p1 across the shock (unitless).

    p2/p1 = 1 + 2*gamma/(gamma+1) * (M1^2 - 1), always > 1 for M1 > 1.
    """
    _validate(M1, gamma)
    return 1.0 + 2.0 * gamma / (gamma + 1.0) * (M1 * M1 - 1.0)


def density_ratio(M1, gamma=1.4):
    """Density ratio rho2/rho1 across the shock (unitless).

    rho2/rho1 = ((gamma+1) * M1^2) / (2 + (gamma-1) * M1^2).
    """
    _validate(M1, gamma)
    return (gamma + 1.0) * M1 * M1 / (2.0 + (gamma - 1.0) * M1 * M1)


def temperature_ratio(M1, gamma=1.4):
    """Static temperature ratio T2/T1 across the shock (unitless).

    T2/T1 = pressure_ratio / density_ratio, from the ideal-gas
    relation p2/p1 = (rho2/rho1) * (T2/T1).
    """
    _validate(M1, gamma)
    return pressure_ratio(M1, gamma) / density_ratio(M1, gamma)


def stagnation_pressure_ratio(M1, gamma=1.4):
    """Stagnation (total) pressure ratio p02/p01 across the shock.

    Unitless and always < 1 for M1 > 1: the total pressure loss across
    a normal shock is the entropy gain of shock compression.
    p02/p01 = (p2/p1)^(1/(1-gamma)) * (rho2/rho1)^(gamma/(gamma-1)).
    """
    _validate(M1, gamma)
    p = pressure_ratio(M1, gamma)
    r = density_ratio(M1, gamma)
    return p ** (1.0 / (1.0 - gamma)) * r ** (gamma / (gamma - 1.0))


def shock_properties(M1, gamma=1.4):
    """All normal shock ratios at upstream Mach M1 (unitless).

    Returns the dict {m2, p2_p1, t2_t1, rho2_rho1, p02_p01}.
    """
    _validate(M1, gamma)
    return {
        "m2": downstream_mach(M1, gamma),
        "p2_p1": pressure_ratio(M1, gamma),
        "t2_t1": temperature_ratio(M1, gamma),
        "rho2_rho1": density_ratio(M1, gamma),
        "p02_p01": stagnation_pressure_ratio(M1, gamma),
    }
