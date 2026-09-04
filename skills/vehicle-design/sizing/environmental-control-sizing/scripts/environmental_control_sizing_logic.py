"""Environmental control system (ECS) sizing for transport aircraft.

Pure stdlib module implementing the leaf contract for
vehicle-design/sizing/environmental-control-sizing: cabin ventilation
fresh air flow, cabin heat load rollup, pack cooling airflow and the
cabin pressurization schedule (held design cabin altitude until the
design differential pressure binds, then constant-differential flight).

The atmosphere relations used internally are the standard two-layer ISA
(troposphere lapse 0.0065 K/m to 11 km, isothermal stratosphere at
216.65 K above). They are private helpers only; the public atmosphere
leaf is cross-cutting/units-atmos/isa-atmosphere. All public functions
raise ValueError on non-physical inputs.
"""

import math

# --- Module constants -------------------------------------------------------
P0 = 101325.0            # sea level pressure, Pa
L = 0.0065               # troposphere lapse rate, K/m
T0 = 288.15              # sea level temperature, K
G = 9.80665              # standard gravity, m/s^2
R = 287.05               # specific gas constant, J/(kg K)
H_TROP = 11000.0         # tropopause height, m
T_STRAT = 216.65         # stratosphere temperature, K

PSI = 6894.757           # Pa per psi
FT = 0.3048              # m per ft

DEFAULT_RATE_PER_OCCUPANT_KGMIN = 0.25   # ventilation rate per occupant
DEFAULT_CP = 1.005                       # air specific heat, kJ/(kg K)
DEFAULT_DT_SUPPLY_K = 20.0               # pack supply temperature rise, K
DEFAULT_CABIN_ALT_FT = 8000.0            # design cabin pressure altitude
DEFAULT_DP_MAX_PSI = 8.9                 # design differential pressure
DEFAULT_MARGIN = 1.1                     # cabin heat load design margin

# Tropopause pressure, Pa, from the troposphere relation at H_TROP.
_P_TROP = P0 * (1.0 - L * H_TROP / T0) ** (G / (L * R))


def _p_isa(h_m):
    """Two-layer ISA pressure at geometric altitude h_m (meters).

    Troposphere (h <= 11000 m): p = P0 (1 - L h / T0)^(G/(L R)).
    Stratosphere (h > 11000 m): isothermal continuation from the
    tropopause pressure with scale height R T_STRAT / G.
    """
    if h_m <= H_TROP:
        return P0 * (1.0 - L * h_m / T0) ** (G / (L * R))
    return _P_TROP * math.exp(-G * (h_m - H_TROP) / (R * T_STRAT))


def _h_isa_from_p(p_pa):
    """Exact inverse of the two-layer ISA: altitude (m) for pressure p_pa.

    Uses the troposphere branch for pressures at or above the tropopause
    pressure and the isothermal stratosphere branch below it.
    """
    if p_pa >= _P_TROP:
        return (T0 / L) * (1.0 - (p_pa / P0) ** (L * R / G))
    return H_TROP - (R * T_STRAT / G) * math.log(p_pa / _P_TROP)


def fresh_air_flow(occupants, rate_per_occupant=DEFAULT_RATE_PER_OCCUPANT_KGMIN):
    """Cabin ventilation fresh air flow from the occupant count.

    Returns {flow_kgmin, flow_kgs}. Raises ValueError for occupants <= 0
    or rate_per_occupant <= 0.
    """
    if occupants <= 0:
        raise ValueError("occupants must be positive")
    if rate_per_occupant <= 0:
        raise ValueError("rate_per_occupant must be positive")
    flow_kgmin = occupants * rate_per_occupant
    return {"flow_kgmin": flow_kgmin, "flow_kgs": flow_kgmin / 60.0}


def cabin_heat_load(occupants, q_occupant_kw, solar_kw, equipment_kw,
                    skin_kw, margin=DEFAULT_MARGIN):
    """Cabin heat load rollup with design margin.

    Returns {occupant_heat_kw, total_heat_kw, design_heat_kw} where
    design_heat_kw = total_heat_kw * margin. Raises ValueError for
    occupants <= 0, margin <= 1 or any negative heat input.
    """
    if occupants <= 0:
        raise ValueError("occupants must be positive")
    for name, value in (("q_occupant_kw", q_occupant_kw),
                        ("solar_kw", solar_kw),
                        ("equipment_kw", equipment_kw),
                        ("skin_kw", skin_kw)):
        if value < 0:
            raise ValueError("%s must be non-negative" % name)
    if margin <= 1:
        raise ValueError("margin must be greater than 1")
    occupant_heat_kw = occupants * q_occupant_kw
    total_heat_kw = occupant_heat_kw + solar_kw + equipment_kw + skin_kw
    return {"occupant_heat_kw": occupant_heat_kw,
            "total_heat_kw": total_heat_kw,
            "design_heat_kw": total_heat_kw * margin}


def pack_airflow(design_heat_kw, cp=DEFAULT_CP, dT_supply_k=DEFAULT_DT_SUPPLY_K,
                 fresh_flow_kgs=0.0):
    """Pack cooling airflow from heat load and supply temperature rise.

    cooling_flow_kgs = design_heat_kw / (cp * dT_supply_k); the pack
    flow is the governing maximum of the fresh ventilation flow and the
    cooling flow. Returns {cooling_flow_kgs, pack_flow_kgs,
    cooling_dominates}. Raises ValueError for design_heat_kw <= 0,
    cp <= 0, dT_supply_k <= 0 or fresh_flow_kgs < 0.
    """
    if design_heat_kw <= 0:
        raise ValueError("design_heat_kw must be positive")
    if cp <= 0:
        raise ValueError("cp must be positive")
    if dT_supply_k <= 0:
        raise ValueError("dT_supply_k must be positive")
    if fresh_flow_kgs < 0:
        raise ValueError("fresh_flow_kgs must be non-negative")
    cooling_flow_kgs = design_heat_kw / (cp * dT_supply_k)
    return {"cooling_flow_kgs": cooling_flow_kgs,
            "pack_flow_kgs": max(fresh_flow_kgs, cooling_flow_kgs),
            "cooling_dominates": cooling_flow_kgs >= fresh_flow_kgs}


def pressurization_schedule(cruise_alt_ft, cabin_alt_design_ft=DEFAULT_CABIN_ALT_FT,
                            dP_max_psi=DEFAULT_DP_MAX_PSI):
    """Cabin pressurization schedule at cruise altitude.

    Holds the cabin pressure altitude at the design value while the
    required differential pressure stays within dP_max_psi; above the
    crossing altitude the differential binds and the cabin pressure
    follows ambient plus the design differential, so the cabin altitude
    rises. Returns {cabin_pressure_pa, ambient_pressure_pa,
    differential_psi, differential_limited, cabin_altitude_ft,
    cabin_altitude_held}. Raises ValueError for cruise_alt_ft < 0,
    cabin_alt_design_ft < 0 or dP_max_psi <= 0.
    """
    if cruise_alt_ft < 0:
        raise ValueError("cruise_alt_ft must be non-negative")
    if cabin_alt_design_ft < 0:
        raise ValueError("cabin_alt_design_ft must be non-negative")
    if dP_max_psi <= 0:
        raise ValueError("dP_max_psi must be positive")
    ambient_pressure_pa = _p_isa(cruise_alt_ft * FT)
    cabin_pressure_pa = _p_isa(cabin_alt_design_ft * FT)
    differential_pa = cabin_pressure_pa - ambient_pressure_pa
    dP_max_pa = dP_max_psi * PSI
    if differential_pa <= dP_max_pa:
        cabin_altitude_ft = cabin_alt_design_ft
        cabin_altitude_held = True
        differential_limited = False
    else:
        cabin_pressure_pa = ambient_pressure_pa + dP_max_pa
        cabin_altitude_ft = _h_isa_from_p(cabin_pressure_pa) / FT
        cabin_altitude_held = False
        differential_limited = True
    return {"cabin_pressure_pa": cabin_pressure_pa,
            "ambient_pressure_pa": ambient_pressure_pa,
            "differential_psi": (cabin_pressure_pa - ambient_pressure_pa) / PSI,
            "differential_limited": differential_limited,
            "cabin_altitude_ft": cabin_altitude_ft,
            "cabin_altitude_held": cabin_altitude_held}


def ecs_summary(occupants, rate_per_occupant=DEFAULT_RATE_PER_OCCUPANT_KGMIN,
                q_occupant_kw=0.12, solar_kw=0.0, equipment_kw=0.0,
                skin_kw=0.0, cruise_alt_ft=DEFAULT_CABIN_ALT_FT,
                margin=DEFAULT_MARGIN, cp=DEFAULT_CP,
                dT_supply_k=DEFAULT_DT_SUPPLY_K,
                cabin_alt_design_ft=DEFAULT_CABIN_ALT_FT,
                dP_max_psi=DEFAULT_DP_MAX_PSI):
    """Full ECS sizing summary combining every module output.

    Merges the fresh air flow, cabin heat load, pack airflow and
    pressurization schedule result dicts into one flat summary.
    """
    fresh = fresh_air_flow(occupants, rate_per_occupant)
    heat = cabin_heat_load(occupants, q_occupant_kw, solar_kw,
                           equipment_kw, skin_kw, margin)
    pack = pack_airflow(heat["design_heat_kw"], cp, dT_supply_k,
                        fresh["flow_kgs"])
    press = pressurization_schedule(cruise_alt_ft, cabin_alt_design_ft,
                                    dP_max_psi)
    summary = dict(fresh)
    summary.update(heat)
    summary.update(pack)
    summary.update(press)
    return summary
