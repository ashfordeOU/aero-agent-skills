"""APU fuel burn sizing at a fixed electrical and bleed load (pure stdlib).

The auxiliary power unit (APU) is a small shaft and bleed powerplant
that produces no propulsive force. At a fixed operating point it must
carry two loads at once:
the generator electrical output, converted back to the generator shaft
power through the generator efficiency, and the bleed air mass flow,
priced as the pumping-power equivalent of an adiabatic load compressor
at the stated pressure ratio. The two are summed into a total
equivalent shaft load, and the fuel flow follows from the APU thermal
efficiency and the fuel lower heating value.

The electrical load rollup and generator sizing stay in the sibling
aircraft-electrical-load-analysis leaf (the generator kW is an input
here, never recomputed); the main-engine fuel flow question stays in
engine-sizing. This module only prices the APU shaft and bleed burden
into a fuel burn.
"""

CP_AIR = 1005.0          # J/kg K, constant-pressure specific heat of air
GAMMA_AIR = 1.4          # air specific heat ratio
ETA_GEN_DEFAULT = 0.85   # generator efficiency
ETA_COMP_DEFAULT = 0.75  # APU load compressor efficiency
ETA_TH_DEFAULT = 0.18    # APU thermal efficiency at the load point
LHV_DEFAULT = 43.2e6     # J/kg, jet fuel lower heating value
T_INLET_DEFAULT = 288.0  # K, compressor inlet temperature


def _check_efficiency(eta, name):
    """Raise ValueError unless eta lies in (0, 1]."""
    if eta <= 0 or eta > 1:
        raise ValueError("%s must be in (0, 1], got %r" % (name, eta))


def generator_shaft_power(p_elec_w, eta_gen=ETA_GEN_DEFAULT):
    """Convert the generator electrical output to the shaft power in W.

    The generator converts shaft power to electrical power at the
    efficiency eta_gen, so the required shaft power is p_elec / eta_gen.
    Raises ValueError on a negative electrical load or an efficiency
    outside (0, 1].
    """
    if p_elec_w < 0:
        raise ValueError("electrical load must be non-negative, got %r" % (p_elec_w,))
    _check_efficiency(eta_gen, "generator efficiency")
    return p_elec_w / eta_gen


def bleed_pumping_power(m_bleed_kg_s, pressure_ratio, t_inlet_k=T_INLET_DEFAULT,
                        eta_comp=ETA_COMP_DEFAULT):
    """Price the bleed mass flow as the load compressor pumping power in W.

    Adiabatic compression work per kg of bleed is cp * T_in *
    (PR^((gamma-1)/gamma) - 1); dividing by the compressor efficiency
    and multiplying by the bleed mass flow gives the shaft power the APU
    must deliver to hold the bleed at the stated absolute total-pressure
    ratio PR. Raises ValueError on a non-positive bleed flow, a pressure
    ratio at or below 1, a non-positive inlet temperature, or a
    compressor efficiency outside (0, 1].
    """
    if m_bleed_kg_s <= 0:
        raise ValueError("bleed mass flow must be positive, got %r" % (m_bleed_kg_s,))
    if pressure_ratio <= 1:
        raise ValueError("pressure ratio must exceed 1, got %r" % (pressure_ratio,))
    if t_inlet_k <= 0:
        raise ValueError("inlet temperature must be positive, got %r" % (t_inlet_k,))
    _check_efficiency(eta_comp, "compressor efficiency")
    ratio_term = pressure_ratio ** ((GAMMA_AIR - 1) / GAMMA_AIR) - 1.0
    work_per_kg = CP_AIR * t_inlet_k * ratio_term
    return work_per_kg * m_bleed_kg_s / eta_comp


def total_shaft_load(p_elec_w, m_bleed_kg_s, pressure_ratio,
                     eta_gen=ETA_GEN_DEFAULT, eta_comp=ETA_COMP_DEFAULT,
                     t_inlet_k=T_INLET_DEFAULT):
    """Sum the generator shaft and bleed pumping loads into one dict.

    Returns {"generator_shaft_w", "bleed_pumping_w", "total_shaft_w"}
    with the total equal to the sum of the two parts. ValueErrors from
    the two load functions propagate for non-physical inputs.
    """
    generator_w = generator_shaft_power(p_elec_w, eta_gen)
    bleed_w = bleed_pumping_power(m_bleed_kg_s, pressure_ratio, t_inlet_k, eta_comp)
    return {
        "generator_shaft_w": generator_w,
        "bleed_pumping_w": bleed_w,
        "total_shaft_w": generator_w + bleed_w,
    }


def apu_fuel_burn(total_shaft_w, eta_th=ETA_TH_DEFAULT, lhv_j_kg=LHV_DEFAULT):
    """Convert the total equivalent shaft load into a fuel flow.

    Fuel flow is the shaft power divided by (eta_th * LHV), the heat
    that must be released each second at the thermal efficiency, so the
    fuel mass leaves the combustor at that rate. Returns
    {"fuel_kg_s", "fuel_kg_h"} with kg/h exactly 3600 times kg/s.
    Raises ValueError on a non-positive shaft load, a thermal efficiency
    outside (0, 1], or a non-positive lower heating value.
    """
    if total_shaft_w <= 0:
        raise ValueError("total shaft load must be positive, got %r" % (total_shaft_w,))
    _check_efficiency(eta_th, "thermal efficiency")
    if lhv_j_kg <= 0:
        raise ValueError("fuel lower heating value must be positive, got %r" % (lhv_j_kg,))
    fuel_kg_s = total_shaft_w / (eta_th * lhv_j_kg)
    return {"fuel_kg_s": fuel_kg_s, "fuel_kg_h": fuel_kg_s * 3600.0}


def apu_summary(p_elec_w, m_bleed_kg_s, pressure_ratio, eta_gen=ETA_GEN_DEFAULT,
                eta_comp=ETA_COMP_DEFAULT, eta_th=ETA_TH_DEFAULT):
    """One-call summary of the APU fuel burn at the fixed load point.

    Returns {"generator_shaft_w", "bleed_pumping_w", "total_shaft_w",
    "fuel_kg_s", "fuel_kg_h"} at the default compressor inlet
    temperature of 288 K. ValueErrors from the load and burn functions
    propagate for non-physical inputs.
    """
    loads = total_shaft_load(p_elec_w, m_bleed_kg_s, pressure_ratio,
                             eta_gen, eta_comp, T_INLET_DEFAULT)
    fuel = apu_fuel_burn(loads["total_shaft_w"], eta_th)
    return {
        "generator_shaft_w": loads["generator_shaft_w"],
        "bleed_pumping_w": loads["bleed_pumping_w"],
        "total_shaft_w": loads["total_shaft_w"],
        "fuel_kg_s": fuel["fuel_kg_s"],
        "fuel_kg_h": fuel["fuel_kg_h"],
    }
