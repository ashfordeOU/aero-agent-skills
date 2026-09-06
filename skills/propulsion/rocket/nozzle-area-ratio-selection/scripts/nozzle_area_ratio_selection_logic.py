"""Nozzle area ratio selection logic (propulsion/rocket/nozzle-area-ratio-selection).

Select the rocket nozzle expansion ratio for a design altitude by solving the
inverse isentropic problem Pe(eps) = Pa(h_design): find the matched expansion
ratio eps* whose ideal exit static pressure equals the ambient pressure at the
design altitude, on the monotone supersonic branch of the area-Mach relation
(exit Mach root by bisection, expansion ratio root by bisection over the
monotone decreasing Pe(eps)). SI units throughout (Pa, m, K, kg/s, m/s, s).

Model (documented simplifications):
- Isentropic area-Mach relation A/A* on the supersonic branch M >= 1 is
  strictly increasing in M, so the inverse exit Mach root is a clean bisection
  on [1, M_hi] with M_hi doubled until the implied area exceeds the target.
- Exit static pressure Pe(eps) = P0 * (1 + (gamma-1)/2 * M^2)^(-gamma/(gamma-1))
  is strictly decreasing in eps from the throat-plane ceiling Pe(1) toward 0,
  so the matched selection is a bisection over eps on that monotone branch.
  A matched supersonic expansion exists only for 0 < pa < Pe(1).
- The ISA-76 three-layer ambient model (0-32000 m) supplies Pa(h_design):
  troposphere with the 0.0065 K/m lapse to 11 km, isothermal stratosphere at
  216.65 K from 11 to 20 km, and the +0.001 K/m lapse layer from 20 to 32 km.
- Delivered specific impulse at a chosen eps and ambient follows the ideal
  rocket relation Isp = (mdot * ve + (Pe - pa) * eps * At) / (mdot * g0) with
  the choked mass flow and the isentropic exit velocity; the throat area
  cancels exactly, so the isp triple is an area ratio property.
- The attached-flow guard is a verdict-only minimum-eps check: attached iff
  Pe(eps) >= K_SEP * pa at the operating ambient with K_SEP = 0.4, the
  documented rocket-nozzle-flow-separation criterion constant used here as a
  boolean guard. No separation station solve and no separation altitude
  output.

Pure Python standard library only (math); deterministic; no network or
external processes. Non-physical inputs raise ValueError. Gamma and the
specific gas constant R are caller-supplied (representative hot combustion
products); the module constants are documented below.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2 (sibling rocket convention)
K_SEP_DEFAULT = 0.4  # wall-separation criterion constant, guard-only usage

# ISA-76 ambient model constants (three layers, 0-32000 m).
ISA_P0 = 101325.0  # sea-level pressure, Pa
ISA_T0 = 288.15  # sea-level temperature, K
ISA_L1 = 0.0065  # troposphere lapse rate, K/m (0-11 km)
ISA_H1 = 11000.0  # tropopause altitude, m
ISA_H2 = 20000.0  # stratosphere upper boundary, m
ISA_H3 = 32000.0  # model ceiling, m
ISA_R = 287.053  # specific gas constant of dry air, J/(kg K)
ISA_T_TROPOPAUSE = 216.65  # tropopause temperature, K
ISA_L2 = 0.001  # upper-layer lapse rate, K/m (20-32 km)
_ISA_G_OVER_R_L1 = G0 / (ISA_R * ISA_L1)
_ISA_G_OVER_R_L2 = G0 / (ISA_R * ISA_L2)

_MACH_BISECTION_ITERATIONS = 400
_EPS_BISECTION_ITERATIONS = 300


def _area_from_mach(m, gamma):
    """Return the isentropic area ratio A/A* at Mach number m (supersonic branch).

    A/A* = (1/M) * ((2/(gamma+1)) * (1 + ((gamma-1)/2) * M^2))^((gamma+1)/(2*(gamma-1))).
    At M = 1 the ratio is exactly 1 (the throat) and it grows monotonically on
    the supersonic branch.
    """
    return (1.0 / m) * (
        (2.0 / (gamma + 1.0)) * (1.0 + 0.5 * (gamma - 1.0) * m * m)
    ) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))


def _throat_plane_ceiling(p0, gamma):
    """Return the throat-plane exit pressure ceiling Pe(1), Pa.

    Pe(1) = P0 * (2/(gamma+1))^(gamma/(gamma-1)) bounds the selection domain:
    a matched supersonic expansion exists only for an ambient strictly below it.
    """
    return p0 * (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))


def ambient_pressure_at_altitude(h_m):
    """Return the ISA-76 ambient pressure (Pa) at geometric altitude h_m (m).

    Troposphere (0-11 km): T = 288.15 - 0.0065*h, p = 101325 * (T/288.15)
    ^(G0/(ISA_R*0.0065)). Isothermal stratosphere (11-20 km): T = 216.65 K and
    p = p(11000) * exp(-G0*(h - 11000)/(ISA_R*216.65)). Upper layer
    (20-32 km): T = 216.65 + 0.001*(h - 20000) and p = p(20000) *
    (T/216.65)^(-G0/(ISA_R*0.001)).
    """
    if h_m < 0.0 or h_m > ISA_H3:
        raise ValueError("altitude h_m must be within the ISA-76 model band 0 to 32000 m")
    if h_m <= ISA_H1:
        temperature = ISA_T0 - ISA_L1 * h_m
        return ISA_P0 * (temperature / ISA_T0) ** _ISA_G_OVER_R_L1
    p_at_tropopause = ISA_P0 * (
        (ISA_T0 - ISA_L1 * ISA_H1) / ISA_T0
    ) ** _ISA_G_OVER_R_L1
    if h_m <= ISA_H2:
        return p_at_tropopause * math.exp(
            -G0 * (h_m - ISA_H1) / (ISA_R * ISA_T_TROPOPAUSE)
        )
    p_at_20km = p_at_tropopause * math.exp(
        -G0 * (ISA_H2 - ISA_H1) / (ISA_R * ISA_T_TROPOPAUSE)
    )
    temperature = ISA_T_TROPOPAUSE + ISA_L2 * (h_m - ISA_H2)
    return p_at_20km * (temperature / ISA_T_TROPOPAUSE) ** (-_ISA_G_OVER_R_L2)


def exit_mach_from_area_ratio(area_ratio, gamma):
    """Return the supersonic-branch exit Mach number for the area ratio A/A*.

    Bisection over [1, M_hi] with M_hi doubled until the implied area exceeds
    the target (400 iterations, float-noise closure) on the strictly increasing
    supersonic branch of the area-Mach relation.
    """
    if area_ratio <= 1.0:
        raise ValueError("area ratio must exceed 1 (supersonic branch only)")
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must exceed 1")
    low = 1.0
    high = 2.0
    while _area_from_mach(high, gamma) < area_ratio:
        high *= 2.0
    for _ in range(_MACH_BISECTION_ITERATIONS):
        mid = 0.5 * (low + high)
        if _area_from_mach(mid, gamma) < area_ratio:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def exit_static_pressure(area_ratio, p0, gamma):
    """Return the ideal exit static pressure Pe (Pa) at the area ratio.

    Pe(eps) = p0 * (1 + ((gamma-1)/2) * M^2)^(-gamma/(gamma-1)) with M the
    supersonic-branch root; Pe is strictly decreasing in eps from the
    throat-plane ceiling toward 0.
    """
    if area_ratio <= 1.0:
        raise ValueError("area ratio must exceed 1 (supersonic branch only)")
    if p0 <= 0.0:
        raise ValueError("chamber pressure p0 must be positive")
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must exceed 1")
    mach = exit_mach_from_area_ratio(area_ratio, gamma)
    return p0 * (1.0 + 0.5 * (gamma - 1.0) * mach * mach) ** (-gamma / (gamma - 1.0))


def expansion_matched_area_ratio(p0, gamma, pa):
    """Return the matched expansion ratio eps* with Pe(eps*) = pa (the selection solve).

    Bisection over eps (300 iterations) on the monotone decreasing Pe(eps),
    with the upper bracket doubled until Pe falls at or below pa. At
    Pe(eps*) = pa the pressure term (Pe - pa) * Ae vanishes by construction.
    """
    if p0 <= 0.0:
        raise ValueError("chamber pressure p0 must be positive")
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must exceed 1")
    if pa <= 0.0:
        raise ValueError("ambient pressure pa must be positive (vacuum has no finite matched ratio)")
    ceiling = _throat_plane_ceiling(p0, gamma)
    if pa >= ceiling:
        raise ValueError(
            "ambient pressure pa at or above the throat-plane ceiling Pe(1): "
            "no supersonic matched expansion exists"
        )
    low = 1.0
    high = 2.0
    while exit_static_pressure(high, p0, gamma) > pa:
        high *= 2.0
    for _ in range(_EPS_BISECTION_ITERATIONS):
        mid = 0.5 * (low + high)
        if exit_static_pressure(mid, p0, gamma) > pa:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def design_altitude_area_ratio(p0, gamma, h_design_m):
    """Return the expansion ratio matched to the ambient at the design altitude.

    expansion_matched_area_ratio(p0, gamma, ambient_pressure_at_altitude(h_design_m)).
    """
    pa = ambient_pressure_at_altitude(h_design_m)
    return expansion_matched_area_ratio(p0, gamma, pa)


def exit_velocity(area_ratio, p0, t0, gamma, r_gas):
    """Return the energy-equation exit velocity ve (m/s) at the area ratio.

    ve = sqrt(2*gamma/(gamma-1) * R * T0 * (1 - (Pe/P0)^((gamma-1)/gamma))); the
    fully expanded ceiling at Pe = 0 is sqrt(2*gamma/(gamma-1) * R * T0).
    """
    if area_ratio <= 1.0:
        raise ValueError("area ratio must exceed 1 (supersonic branch only)")
    if p0 <= 0.0 or t0 <= 0.0 or r_gas <= 0.0:
        raise ValueError("chamber pressure, temperature and gas constant must be positive")
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must exceed 1")
    pe = exit_static_pressure(area_ratio, p0, gamma)
    return math.sqrt(
        (2.0 * gamma / (gamma - 1.0))
        * r_gas
        * t0
        * (1.0 - (pe / p0) ** ((gamma - 1.0) / gamma))
    )


def choked_mass_flow(throat_area_m2, p0, t0, gamma, r_gas):
    """Return the choked mass flow mdot (kg/s) through the throat area At (m^2).

    mdot = (P0 * At / sqrt(T0)) * sqrt(gamma/R) * (2/(gamma+1))^((gamma+1)/(2*(gamma-1))),
    the choked-flow relation reproduced here only to normalize the isp triple.
    """
    if throat_area_m2 <= 0.0 or p0 <= 0.0 or t0 <= 0.0 or r_gas <= 0.0:
        raise ValueError("throat area, chamber pressure, temperature and gas constant must be positive")
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must exceed 1")
    return (
        (p0 * throat_area_m2 / math.sqrt(t0))
        * math.sqrt(gamma / r_gas)
        * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
    )


def delivered_isp(area_ratio, p0, t0, gamma, r_gas, pa, throat_area_m2, g0=G0):
    """Return the delivered specific impulse Isp (s) at the area ratio and ambient.

    Isp = (mdot * ve + (Pe - pa) * area_ratio * throat_area_m2) / (mdot * g0).
    The sea-level, vacuum and design-altitude values are the same call with
    pa = 101325.0, pa = 0.0 and pa = ambient_pressure_at_altitude(h_design).
    The throat area cancels exactly, so the isp is an area ratio property.
    """
    if area_ratio <= 1.0:
        raise ValueError("area ratio must exceed 1 (supersonic branch only)")
    if p0 <= 0.0 or t0 <= 0.0 or r_gas <= 0.0 or throat_area_m2 <= 0.0:
        raise ValueError("chamber pressure, temperature, gas constant and throat area must be positive")
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must exceed 1")
    if pa < 0.0:
        raise ValueError("ambient pressure pa must be non-negative (pa = 0 vacuum allowed)")
    if g0 <= 0.0:
        raise ValueError("standard gravity g0 must be positive")
    mdot = choked_mass_flow(throat_area_m2, p0, t0, gamma, r_gas)
    ve = exit_velocity(area_ratio, p0, t0, gamma, r_gas)
    pe = exit_static_pressure(area_ratio, p0, gamma)
    return (mdot * ve + (pe - pa) * area_ratio * throat_area_m2) / (mdot * g0)


def attached_flow_guard(area_ratio, p0, gamma, pa, k_sep=K_SEP_DEFAULT):
    """Return True iff the wall flow stays attached: Pe(eps) >= k_sep * pa.

    Verdict-only minimum-eps guard on the chosen ratio at the operating ambient
    pa. Evaluated directly from this module's Pe(eps) with no separation
    station solve and no separation altitude output; when it returns False
    the wall flow would separate there and rocket-nozzle-flow-separation
    takes over.
    """
    if pa <= 0.0:
        raise ValueError("ambient pressure pa must be positive")
    if k_sep <= 0.0 or k_sep >= 1.0:
        raise ValueError("guard constant k_sep must lie strictly between 0 and 1")
    pe = exit_static_pressure(area_ratio, p0, gamma)
    return pe >= k_sep * pa
