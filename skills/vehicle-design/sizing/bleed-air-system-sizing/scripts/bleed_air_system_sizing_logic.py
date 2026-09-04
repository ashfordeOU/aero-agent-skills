#!/usr/bin/env python3
"""Bleed air system sizing for transport aircraft pneumatic systems.

Pure Python 3, stdlib only, SI units throughout. Sizes the aircraft
pneumatic bleed distribution system downstream of the engine offtakes
at the conceptual level:

  - total bleed offtake mass flow from the fixed consumer demands (ECS
    pack flows, wing anti-ice flow, pressurization trim flow), split
    evenly across the two engines
  - bleed thermal budget the precooler and conditioning system must
    reject between the bleed supply temperature and the consumer
    supply temperature: q = m * CP_AIR * (T_bleed - T_supply)
  - per-engine bleed duct diameter from compressible pipe flow at a
    fixed design Mach number: rho = p / (R_AIR * T),
    a = sqrt(GAMMA_AIR * R_AIR * T), V = M * a, A = m / (rho * V),
    D = sqrt(4 * A / pi)
  - system summary rolling all of the above up with a fit verdict
    against a nominal duct diameter limit

The ECS pack flows, the wing anti-ice flow and the pressurization trim
flow are FIXED INPUTS: the consumer demand values computed by the
sibling environmental-control and ice-protection leaves are inputs
here, never recomputed.

All functions validate their inputs and raise ValueError on physically
invalid values (negative mass flows, non-positive mass, temperature or
pressure, Mach number outside (0, 1), bleed temperature at or below
the supply temperature).
"""

import math

# Module constants (fixed design parameters of the installation).
CP_AIR = 1005.0           # air specific heat at constant pressure, J/(kg K)
R_AIR = 287.0             # air gas constant, J/(kg K)
GAMMA_AIR = 1.4           # air ratio of specific heats
M_DUCT = 0.30             # design duct Mach number, fixed
T_SUPPLY_DEFAULT = 288.0  # consumer supply temperature, K (sea level day)
P_DUCT_DEFAULT = 350000.0  # nominal bleed duct static pressure, Pa
N_ENGINES = 2             # engines sharing the bleed offtake


def _require_non_negative(value, name):
    """Reject negative inputs (zero is physical for some flows)."""
    if value < 0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))


def _require_positive(value, name):
    """Reject non-positive inputs (mass, temperature, pressure)."""
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def total_bleed_offtake(pack_flows_kg_s, anti_ice_kg_s, trim_kg_s):
    """Roll up the total bleed offtake from the fixed consumer demands.

    pack_flows_kg_s: iterable of per-pack ECS bleed flow demands in
    kg/s (one entry per pack; the values are inputs computed by the
    environmental-control sizing leaf, not recomputed here).
    anti_ice_kg_s: wing anti-ice bleed flow demand in kg/s (input from
    the ice-protection sizing leaf).
    trim_kg_s: pressurization trim bleed flow demand in kg/s.

    Returns dict {total_kg_s, per_engine_kg_s} with per_engine_kg_s =
    total / N_ENGINES. Raises ValueError on any negative flow.
    """
    total = 0.0
    for flow in pack_flows_kg_s:
        _require_non_negative(flow, "pack flow")
        total += flow
    _require_non_negative(anti_ice_kg_s, "anti_ice_kg_s")
    _require_non_negative(trim_kg_s, "trim_kg_s")
    total += anti_ice_kg_s + trim_kg_s
    return {"total_kg_s": total, "per_engine_kg_s": total / N_ENGINES}


def bleed_thermal_budget(mass_kg_s, t_bleed_k, t_supply_k=T_SUPPLY_DEFAULT):
    """Thermal budget the precooler must reject for a bleed mass flow.

    q = m * CP_AIR * (T_bleed - T_supply), the sensible heat removed
    in cooling the bleed from the engine offtake total temperature to
    the consumer supply temperature.

    mass_kg_s: bleed mass flow in kg/s (per engine or total).
    t_bleed_k: engine bleed offtake total temperature in K.
    t_supply_k: consumer supply temperature in K.

    Returns dict {q_w, mass_kg_s, t_bleed_k, t_supply_k}. Raises
    ValueError when mass is non-positive or t_bleed <= t_supply.
    """
    _require_positive(mass_kg_s, "mass_kg_s")
    if t_bleed_k <= t_supply_k:
        raise ValueError(
            "t_bleed_k must exceed t_supply_k, got %r <= %r"
            % (t_bleed_k, t_supply_k))
    q = mass_kg_s * CP_AIR * (t_bleed_k - t_supply_k)
    return {"q_w": q, "mass_kg_s": mass_kg_s,
            "t_bleed_k": t_bleed_k, "t_supply_k": t_supply_k}


def bleed_duct_diameter(mass_kg_s, t_bleed_k, p_duct_pa=P_DUCT_DEFAULT,
                        mach=M_DUCT):
    """Size a bleed duct from compressible pipe flow at fixed Mach.

    Density and sonic speed come from the bleed state at the duct:
    rho = p / (R_AIR * T), a = sqrt(GAMMA_AIR * R_AIR * T); the duct
    velocity is V = mach * a, the flow area A = m / (rho * V) and the
    diameter D = sqrt(4 * A / pi).

    mass_kg_s: bleed mass flow through the duct in kg/s (per engine).
    t_bleed_k: bleed temperature in the duct in K.
    p_duct_pa: duct static pressure in Pa.
    mach: design duct Mach number, fixed 0.30 unless overridden.

    Returns dict {area_m2, diameter_m, velocity_m_s, density_kg_m3}.
    Raises ValueError when mass, temperature or pressure are
    non-positive or mach is outside (0, 1).
    """
    _require_positive(mass_kg_s, "mass_kg_s")
    _require_positive(t_bleed_k, "t_bleed_k")
    _require_positive(p_duct_pa, "p_duct_pa")
    if not (0.0 < mach < 1.0):
        raise ValueError("mach must be in (0, 1), got %r" % (mach,))
    density = p_duct_pa / (R_AIR * t_bleed_k)
    sonic = math.sqrt(GAMMA_AIR * R_AIR * t_bleed_k)
    velocity = mach * sonic
    area = mass_kg_s / (density * velocity)
    diameter = math.sqrt(4.0 * area / math.pi)
    return {"area_m2": area, "diameter_m": diameter,
            "velocity_m_s": velocity, "density_kg_m3": density}


def bleed_system_summary(pack_flows_kg_s, anti_ice_kg_s, trim_kg_s,
                         t_bleed_k, max_duct_diameter_m,
                         t_supply_k=T_SUPPLY_DEFAULT,
                         p_duct_pa=P_DUCT_DEFAULT, mach=M_DUCT):
    """Full bleed system sizing rollup with the duct fit verdict.

    Runs the offtake rollup, per-engine and total thermal budgets and
    the per-engine duct sizing, then judges the duct diameter against
    the nominal limit: verdict PASS when diameter <= max_duct_diameter_m
    else FAIL.

    max_duct_diameter_m: nominal duct diameter limit in m (the largest
    duct the installation can accommodate).

    Returns dict with keys total_offtake_kg_s, per_engine_offtake_kg_s,
    per_engine_thermal_budget_w, total_thermal_budget_w, duct_area_m2,
    duct_diameter_m, duct_velocity_m_s, duct_density_kg_m3,
    max_duct_diameter_m, duct_fit_verdict. Raises ValueError on the
    non-physical inputs listed for the three component functions and on
    a non-positive duct diameter limit.
    """
    _require_positive(max_duct_diameter_m, "max_duct_diameter_m")
    offtake = total_bleed_offtake(pack_flows_kg_s, anti_ice_kg_s, trim_kg_s)
    per_engine = offtake["per_engine_kg_s"]
    per_engine_budget = bleed_thermal_budget(per_engine, t_bleed_k,
                                             t_supply_k)["q_w"]
    total_budget = bleed_thermal_budget(offtake["total_kg_s"], t_bleed_k,
                                        t_supply_k)["q_w"]
    duct = bleed_duct_diameter(per_engine, t_bleed_k, p_duct_pa, mach)
    verdict = "PASS" if duct["diameter_m"] <= max_duct_diameter_m else "FAIL"
    return {
        "total_offtake_kg_s": offtake["total_kg_s"],
        "per_engine_offtake_kg_s": per_engine,
        "per_engine_thermal_budget_w": per_engine_budget,
        "total_thermal_budget_w": total_budget,
        "duct_area_m2": duct["area_m2"],
        "duct_diameter_m": duct["diameter_m"],
        "duct_velocity_m_s": duct["velocity_m_s"],
        "duct_density_kg_m3": duct["density_kg_m3"],
        "max_duct_diameter_m": max_duct_diameter_m,
        "duct_fit_verdict": verdict,
    }
