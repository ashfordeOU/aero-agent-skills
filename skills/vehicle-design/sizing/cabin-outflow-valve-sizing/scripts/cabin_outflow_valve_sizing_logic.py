"""Cabin outflow and pressure-relief valve effective area sizing (pure stdlib).

Conceptual sizing of the cabin outflow valve and pressure-relief valve from
the choked-flow mass-flux relation:

    G = p * sqrt(gamma / (R * T)) * (2 / (gamma + 1)) ** ((gamma + 1) /
        (2 * (gamma - 1)))

where G is the choked mass flux in kg/(m2 s), p the upstream total pressure
in Pa and T the upstream temperature in K.  The effective area follows as
A = m_dot / G and the equivalent diameter as D = sqrt(4 * A / pi).

Choked flow only: the pressure ratio p_amb / p_cab must be below the
critical ratio CRITICAL_RATIO = (2/(gamma+1))**(gamma/(gamma-1)) ~= 0.528.
All inputs are SI (Pa, K, kg/s, m).  Module constants encode the ISA
anchors and the 8.9 psi (61363 Pa) differential pressure clamp.
"""

import math

# Module constants (ISA / configuration anchors).
GAMMA_AIR = 1.4
R_AIR = 287.0  # J/(kg K)
T_CABIN_DEFAULT = 288.0  # K, cabin temperature at the sizing point
P_AMB_39000FT = 19677.0  # Pa, ISA ambient at 39,000 ft (cruise anchor)
P_AMB_50000FT = 11597.0  # Pa, ISA ambient at 50,000 ft (relief anchor)
DP_CLAMP_DEFAULT = 61363.0  # Pa, 8.9 psi differential pressure clamp
CRITICAL_RATIO = (2.0 / (GAMMA_AIR + 1.0)) ** (GAMMA_AIR / (GAMMA_AIR - 1.0))
FLUX_FACTOR = (2.0 / (GAMMA_AIR + 1.0)) ** (
    (GAMMA_AIR + 1.0) / (2.0 * (GAMMA_AIR - 1.0))
)
# FLUX_FACTOR is 0.578704 for gamma 1.4 (choked-flow closed-form factor).


def choked_mass_flux(p_cab_pa, t_cabin_k=T_CABIN_DEFAULT):
    """Choked-flow mass flux G in kg/(m2 s) at upstream pressure p and
    temperature t.

    G = p * sqrt(gamma / (R * t)) * FLUX_FACTOR.  Raises ValueError for
    non-positive pressure or temperature.
    """
    if p_cab_pa <= 0.0:
        raise ValueError("p_cab must be positive")
    if t_cabin_k <= 0.0:
        raise ValueError("t_cabin must be positive")
    return p_cab_pa * math.sqrt(GAMMA_AIR / (R_AIR * t_cabin_k)) * FLUX_FACTOR


def is_choked(p_cab_pa, p_amb_pa):
    """True when the pressure ratio p_amb / p_cab is below the critical
    ratio (choked-flow threshold, strict: 0.528 -> False)."""
    if p_cab_pa <= 0.0:
        raise ValueError("p_cab must be positive")
    if p_amb_pa < 0.0:
        raise ValueError("p_amb must be non-negative")
    return (p_amb_pa / p_cab_pa) < CRITICAL_RATIO


def valve_area(m_dot_kg_s, p_cab_pa, t_cabin_k=T_CABIN_DEFAULT):
    """Effective area m2 and equivalent diameter m for a choked valve
    passing m_dot at upstream pressure p and temperature t.

    A = m_dot / G and D = sqrt(4 * A / pi).  Raises ValueError for
    non-positive mass flow, pressure or temperature.
    """
    if m_dot_kg_s <= 0.0:
        raise ValueError("m_dot must be positive")
    flux = choked_mass_flux(p_cab_pa, t_cabin_k)
    area_m2 = m_dot_kg_s / flux
    diameter_m = math.sqrt(4.0 * area_m2 / math.pi)
    return {"area_m2": area_m2, "diameter_m": diameter_m}


def _fit_verdict(diameter_m, max_valve_diameter_m):
    """PASS when the equivalent diameter fits the nominal limit."""
    if max_valve_diameter_m <= 0.0:
        raise ValueError("max_valve_diameter must be positive")
    return "PASS" if diameter_m <= max_valve_diameter_m else "FAIL"


def outflow_valve_sizing(
    m_pack_kg_s,
    p_cab_pa,
    p_amb_pa,
    max_valve_diameter_m,
    t_cabin_k=T_CABIN_DEFAULT,
):
    """Outflow valve effective area that passes the governing pack inflow
    at the cruise cabin pressure.

    Returns a dict with choked (bool), mass_flux_kg_m2s, area_m2,
    diameter_m and fit_verdict (PASS when diameter <= the nominal limit).
    Raises ValueError when the flow is not choked, or on any non-physical
    input.
    """
    if m_pack_kg_s <= 0.0:
        raise ValueError("m_pack must be positive")
    choked = is_choked(p_cab_pa, p_amb_pa)
    if not choked:
        raise ValueError("outflow flow is not choked at this pressure ratio")
    area = valve_area(m_pack_kg_s, p_cab_pa, t_cabin_k)
    return {
        "choked": True,
        "mass_flux_kg_m2s": choked_mass_flux(p_cab_pa, t_cabin_k),
        "area_m2": area["area_m2"],
        "diameter_m": area["diameter_m"],
        "fit_verdict": _fit_verdict(area["diameter_m"], max_valve_diameter_m),
    }


def relief_valve_sizing(
    m_pack_kg_s,
    p_amb_pa,
    dp_clamp_pa=DP_CLAMP_DEFAULT,
    max_valve_diameter_m=None,
    t_cabin_k=T_CABIN_DEFAULT,
):
    """Pressure-relief valve effective area that dumps the same pack flow
    at the differential pressure clamp ceiling.

    The relief upstream pressure is p_cab = p_amb + dp_clamp and the choked
    check compares p_amb / p_cab against the critical ratio.  Returns a
    dict with choked (bool), mass_flux_kg_m2s, area_m2, diameter_m and
    fit_verdict.  Raises ValueError when the flow is not choked at the
    clamp ceiling or on any non-physical input.
    """
    if m_pack_kg_s <= 0.0:
        raise ValueError("m_pack must be positive")
    if dp_clamp_pa <= 0.0:
        raise ValueError("dp_clamp must be positive")
    if max_valve_diameter_m is None:
        raise ValueError("max_valve_diameter is required")
    p_cab_pa = p_amb_pa + dp_clamp_pa
    choked = is_choked(p_cab_pa, p_amb_pa)
    if not choked:
        raise ValueError("relief flow is not choked at the clamp ceiling")
    area = valve_area(m_pack_kg_s, p_cab_pa, t_cabin_k)
    return {
        "choked": True,
        "mass_flux_kg_m2s": choked_mass_flux(p_cab_pa, t_cabin_k),
        "area_m2": area["area_m2"],
        "diameter_m": area["diameter_m"],
        "fit_verdict": _fit_verdict(area["diameter_m"], max_valve_diameter_m),
    }
