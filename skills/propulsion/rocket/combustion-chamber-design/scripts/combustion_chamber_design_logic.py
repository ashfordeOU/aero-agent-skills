"""Rocket combustion chamber design logic (AeroSkills propulsion).

Pure functions, stdlib only. Real engineering math for the chamber
upstream of the nozzle throat: characteristic velocity c-star, thrust
coefficient Cf, contraction ratio, chamber volume from L-star, and
vacuum specific impulse. Invalid inputs raise ValueError.

Units: Pc in Pa, At and Ac in m^2, mdot in kg/s, F in N, T in K, Mw in
kg/kmol, lengths in m, angles none, c-star in m/s, Isp in s.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2
UNIVERSAL_GAS_CONSTANT = 8314.462  # J/(kmol K)


def characteristic_velocity(pc, throat_area, mass_flow):
    """Delivered characteristic velocity c* = Pc * At / mdot in m/s.

    This is the defining, measured relation for the chamber upstream of
    the throat.
    """
    if pc <= 0 or throat_area <= 0 or mass_flow <= 0:
        raise ValueError("pc, throat_area and mass_flow must be positive")
    return pc * throat_area / mass_flow


def theoretical_cstar(chamber_temp, molecular_weight, gamma):
    """Ideal c* from gas properties in m/s.

    c* = sqrt(gamma * R * Tc) / (gamma * sqrt((2/(gamma+1))**((gamma+1)/(gamma-1))))
    with R = UNIVERSAL_GAS_CONSTANT / molecular_weight. Depends on the
    gas only, not on the chamber pressure.
    """
    if chamber_temp <= 0 or molecular_weight <= 0:
        raise ValueError("chamber_temp and molecular_weight must be positive")
    if not 1.0 < gamma <= 5.0 / 3.0:
        raise ValueError("gamma must be in (1, 5/3]")
    r = UNIVERSAL_GAS_CONSTANT / molecular_weight
    denom = gamma * math.sqrt((2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0)))
    return math.sqrt(gamma * r * chamber_temp) / denom


def thrust_coefficient(thrust, pc, throat_area):
    """Thrust coefficient Cf = F / (Pc * At), dimensionless.

    Roughly 1.4-1.6 at sea level and 1.8-2.0 in vacuum depending on the
    expansion of the nozzle downstream of the throat.
    """
    if thrust <= 0 or pc <= 0 or throat_area <= 0:
        raise ValueError("thrust, pc and throat_area must be positive")
    return thrust / (pc * throat_area)


def thrust_from_cf(cf, pc, throat_area):
    """Thrust F = Cf * Pc * At in N; inverse of thrust_coefficient."""
    if cf <= 0 or pc <= 0 or throat_area <= 0:
        raise ValueError("cf, pc and throat_area must be positive")
    return cf * pc * throat_area


def throat_area_from_flow(mass_flow, cstar, pc):
    """Required throat area At = mdot * c* / Pc in m^2.

    This is the sizing interface handed to the nozzle downstream of the
    throat.
    """
    if mass_flow <= 0 or cstar <= 0 or pc <= 0:
        raise ValueError("mass_flow, cstar and pc must be positive")
    return mass_flow * cstar / pc


def contraction_ratio(chamber_area, throat_area):
    """Chamber contraction ratio epsilon_c = Ac / At.

    The chamber must converge into the throat, so chamber_area must
    strictly exceed throat_area; typical values are 2 to 5 for liquid
    engines.
    """
    if chamber_area <= 0 or throat_area <= 0:
        raise ValueError("chamber_area and throat_area must be positive")
    if chamber_area <= throat_area:
        raise ValueError(
            "chamber_area must exceed throat_area for a converging chamber"
        )
    return chamber_area / throat_area


def chamber_volume(lstar, throat_area):
    """Chamber volume Vc = L-star * At in m^3.

    L-star is the characteristic chamber length in m (typical 0.5-1.5 m
    for liquid propellants); it sets the residence time for complete
    combustion.
    """
    if lstar <= 0 or throat_area <= 0:
        raise ValueError("lstar and throat_area must be positive")
    return lstar * throat_area


def nozzle_throat_radius(throat_area):
    """Circular throat radius r = sqrt(At / pi) in m."""
    if throat_area <= 0:
        raise ValueError("throat_area must be positive")
    return math.sqrt(throat_area / math.pi)


def vacuum_specific_impulse(thrust, mass_flow):
    """Vacuum specific impulse Isp = F / (mdot * g0) in seconds."""
    if thrust <= 0 or mass_flow <= 0:
        raise ValueError("thrust and mass_flow must be positive")
    return thrust / (mass_flow * G0)
