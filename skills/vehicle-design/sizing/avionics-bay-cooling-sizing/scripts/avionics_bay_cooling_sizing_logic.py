"""Avionics bay cooling airflow sizing for aircraft equipment bays.

Pure stdlib module implementing the leaf contract for
vehicle-design/sizing/avionics-bay-cooling-sizing: rolling up the bay
heat load from the LRU heat dissipations, sizing the bay cooling mass
flow from the allowable cooling air temperature rise so the bay
exhaust temperature stays at or below the LRU inlet-air temperature
limit, converting the mass flow to the volumetric flow and to cubic
feet per minute, and checking each LRU case temperature against its
case limit from the dissipated power and the case-to-air conductance.

Conventions: LRU dissipations in W; temperatures in deg C; the bay
airflow enters at the supply temperature and leaves at the exhaust
temperature; the exhaust temperature is sized to equal the LRU
inlet-air temperature limit (maximum cooling benefit without
exceeding the LRU inlet limit). All public functions raise ValueError
on non-physical inputs. No RNG, no network, deterministic.
"""

# --- Module constants -------------------------------------------------------
AIR_CP = 1005.0             # dry air specific heat, J/(kg K)
DEFAULT_AIR_DENSITY = 1.2   # near-sea-level air density, kg/m3
CFM_PER_M3S = 2118.88       # cubic feet per minute per cubic meter per second
DEFAULT_CASE_CONDUCTANCE_W_K = 12.0   # default LRU case-to-air conductance

_ABS_ZERO_C = -273.15


def bay_heat_load(lru_dissipations_w):
    """Roll up the avionics bay heat load from the LRU dissipations.

    Accepts a mapping {lru label: power W} or a sequence of powers W
    (index order preserved). Returns {total_w, per_lru_w} where
    total_w is the sum of the LRU powers and per_lru_w mirrors the
    input shape (dict for mapping input, list for sequence input).

    Raises ValueError on an empty input or any negative power.
    """
    if lru_dissipations_w is None:
        raise ValueError("LRU dissipation list must not be empty")
    try:
        items = list(lru_dissipations_w.items())
        per_lru = dict(items)
    except AttributeError:
        items = list(enumerate(lru_dissipations_w))
        per_lru = [p for _, p in items]
    if not items:
        raise ValueError("LRU dissipation list must not be empty")
    for label, power in items:
        if power < 0:
            raise ValueError(
                "negative LRU dissipation %r W for %r is non-physical"
                % (power, label))
    total = float(sum(power for _, power in items))
    return {"total_w": total, "per_lru_w": per_lru}


def cooling_mass_flow(total_heat_w, supply_temp_c, exhaust_limit_c,
                      cp=AIR_CP):
    """Size the bay cooling mass flow from the allowable air temperature rise.

    m_dot = Q / (cp * (T_limit - T_supply)) with the exhaust sized to
    equal the LRU inlet-air temperature limit. Returns
    {mass_flow_kg_s, exhaust_temp_c} where exhaust_temp_c equals the
    exhaust limit. Zero heat gives a zero mass flow.

    Raises ValueError when heat is negative or the temperature
    difference (limit minus supply) is not positive.
    """
    if total_heat_w < 0:
        raise ValueError("negative bay heat load %r W is non-physical"
                         % total_heat_w)
    delta_t = exhaust_limit_c - supply_temp_c
    if delta_t <= 0:
        raise ValueError(
            "exhaust limit %r C must exceed supply %r C for cooling flow"
            % (exhaust_limit_c, supply_temp_c))
    if total_heat_w == 0:
        flow = 0.0
    else:
        flow = total_heat_w / (cp * delta_t)
    return {"mass_flow_kg_s": flow, "exhaust_temp_c": exhaust_limit_c}


def volumetric_flow(mass_flow_kg_s, density=DEFAULT_AIR_DENSITY):
    """Convert the cooling mass flow to volumetric flow and CFM.

    flow_m3_s = m_dot / density; flow_cfm = flow_m3_s * 2118.88.
    Returns {flow_m3_s, flow_cfm}.

    Raises ValueError when the mass flow is negative or the density is
    not positive.
    """
    if mass_flow_kg_s < 0:
        raise ValueError("negative mass flow %r kg/s is non-physical"
                         % mass_flow_kg_s)
    if density <= 0:
        raise ValueError("density %r kg/m3 must be positive" % density)
    flow_m3_s = mass_flow_kg_s / density
    return {"flow_m3_s": flow_m3_s,
            "flow_cfm": flow_m3_s * CFM_PER_M3S}


def lru_case_temperature(power_w, conductance_w_k, inlet_air_temp_c):
    """LRU case temperature from dissipated power and case-to-air conductance.

    T_case = T_inlet + P / (h A), where h A is the case-to-air
    conductance in W/K. Returns {case_temp_c, rise_k}.

    Raises ValueError when the power is negative or the conductance is
    not positive.
    """
    if power_w < 0:
        raise ValueError("negative LRU dissipation %r W is non-physical"
                         % power_w)
    if conductance_w_k <= 0:
        raise ValueError(
            "case-to-air conductance %r W/K must be positive"
            % conductance_w_k)
    rise = power_w / conductance_w_k
    return {"case_temp_c": inlet_air_temp_c + rise, "rise_k": rise}


def case_verdict(case_temp_c, case_limit_c):
    """Verdict for one LRU case temperature against its case limit.

    PASS when case_temp_c <= case_limit_c else FAIL. margin_k is
    case_limit_c minus case_temp_c (positive for PASS, negative for
    FAIL, zero on an exact equality). The case temperature may be any
    finite value; the limit may be any finite value above absolute
    zero.

    Raises ValueError when the case limit sits below absolute zero.
    """
    if case_limit_c < _ABS_ZERO_C:
        raise ValueError(
            "case limit %r C below absolute zero is non-physical"
            % case_limit_c)
    margin = case_limit_c - case_temp_c
    verdict = "PASS" if case_temp_c <= case_limit_c else "FAIL"
    return {"verdict": verdict, "margin_k": margin}


def bay_cooling_summary(lru_dissipations_w, supply_temp_c,
                        exhaust_limit_c, lru_case_limits_c,
                        density=DEFAULT_AIR_DENSITY,
                        conductance_w_k=DEFAULT_CASE_CONDUCTANCE_W_K):
    """Complete avionics bay cooling summary for a bay of LRUs.

    Inputs: the LRU dissipations (sequence of W, index order aligned
    with lru_case_limits_c), the cooling supply temperature C, the LRU
    inlet-air exhaust limit C, the per-LRU case limits C (one per
    LRU), the air density and the shared case-to-air conductance W/K.

    Returns {total_w, mass_flow_kg_s, flow_m3_s, flow_cfm,
    exhaust_temp_c, case_temps_c, case_verdicts, bay_verdict} where
    case_temps_c and case_verdicts map each 0-based LRU index to its
    case temperature and PASS/FAIL verdict, and bay_verdict is FAIL
    when any LRU case exceeds its limit or the mass flow is zero with
    positive heat, else PASS.

    Raises ValueError when the LRU lists are empty, negative, of
    mismatched length, or when the exhaust limit does not exceed the
    supply temperature with positive heat.
    """
    heat = bay_heat_load(lru_dissipations_w)
    total_w = heat["total_w"]
    per_lru = heat["per_lru_w"]
    powers = list(per_lru.values()) if isinstance(per_lru, dict) \
        else list(per_lru)
    if len(lru_case_limits_c) != len(powers):
        raise ValueError(
            "need one case limit per LRU: got %d limits for %d LRUs"
            % (len(lru_case_limits_c), len(powers)))
    flow = cooling_mass_flow(total_w, supply_temp_c, exhaust_limit_c)
    volume = volumetric_flow(flow["mass_flow_kg_s"], density)
    case_temps = {}
    verdicts = {}
    for i, (power, limit) in enumerate(zip(powers, lru_case_limits_c)):
        case = lru_case_temperature(power, conductance_w_k,
                                    supply_temp_c)
        case_temps[i] = case["case_temp_c"]
        verdicts[i] = case_verdict(case["case_temp_c"], limit)["verdict"]
    any_fail = any(v == "FAIL" for v in verdicts.values())
    flowless_with_heat = total_w > 0 and flow["mass_flow_kg_s"] <= 0
    bay_verdict = "FAIL" if (any_fail or flowless_with_heat) else "PASS"
    return {
        "total_w": total_w,
        "mass_flow_kg_s": flow["mass_flow_kg_s"],
        "flow_m3_s": volume["flow_m3_s"],
        "flow_cfm": volume["flow_cfm"],
        "exhaust_temp_c": flow["exhaust_temp_c"],
        "case_temps_c": case_temps,
        "case_verdicts": verdicts,
        "bay_verdict": bay_verdict,
    }
