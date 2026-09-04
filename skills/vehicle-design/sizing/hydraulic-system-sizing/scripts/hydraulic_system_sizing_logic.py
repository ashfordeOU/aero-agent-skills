"""Aircraft hydraulic power system sizing (pure stdlib).

Sizes the hydraulic power system from flight-control and utility
actuation demand: actuator flow from piston area and rod speed, pump
flow from the worst-case simultaneous demand group plus leakage, pump
power from system pressure and flow over efficiency, the emergency
accumulator gas volume from the adiabatic gas law between charged and
depleted pressures given the usable volume, and the reservoir volume
from leakage make-up over a hold time with margin.

Units: flow in L/min and m3/s, pressures entered in psi and converted
internally to Pa, volumes in L. The accumulator gas-law closure is
evaluated in SI (p in Pa, V in m3) so the p1 * V1^n = p2 * V2^n
magnitude matches the standard hand calculation.

This module does not size control surface geometry or hinge moments,
landing gear strut loads, or the accumulator shell wall stress; those
belong to other leaves.
"""

# Module constants (documented aircraft hydraulic typicals).
LPM_PER_M3S = 60000.0          # L/min per m3/s.
PSI_PA = 6894.757              # Pa per psi.
GAS_ADIABATIC_DEFAULT = 1.4    # Nitrogen adiabatic exponent, n.
DEFAULT_LEAKAGE_LPM = 15.0     # System leakage make-up, L/min.
DEFAULT_RESERVOIR_HOLD_MIN = 2.0   # Leakage make-up hold, minutes.
DEFAULT_RESERVOIR_MARGIN = 1.2     # Reservoir volume margin factor.

_SI = "SI units, no numpy"


def _check_positive(value, name):
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def actuator_flow(piston_area_m2, rod_speed_m_s):
    """Flow of one actuator: piston area times rod speed.

    Returns dict {flow_m3s, flow_lpm}. ValueErrors on non-positive
    piston area or rod speed.
    """
    _check_positive(piston_area_m2, "piston_area_m2")
    _check_positive(rod_speed_m_s, "rod_speed_m_s")
    flow_m3s = piston_area_m2 * rod_speed_m_s
    return {
        "flow_m3s": flow_m3s,
        "flow_lpm": flow_m3s * LPM_PER_M3S,
    }


def simultaneous_demand(actuator_flow_lpm, n_simultaneous):
    """Worst-case simultaneous actuator demand: n times the per-actuator flow.

    Returns the demand in L/min. ValueErrors on non-positive flow or a
    non-positive simultaneity count (at least one actuator is always
    moving in the worst case).
    """
    _check_positive(actuator_flow_lpm, "actuator_flow_lpm")
    _check_positive(n_simultaneous, "n_simultaneous")
    return n_simultaneous * actuator_flow_lpm


def pump_flow(actuator_flow_lpm, n_actuators, n_simultaneous,
              leakage_lpm=DEFAULT_LEAKAGE_LPM):
    """Pump flow: simultaneous demand plus system leakage.

    Returns dict {simultaneous_lpm, pump_flow_lpm, pump_flow_m3s}.
    ValueErrors when n_simultaneous exceeds n_actuators, counts or flow
    are non-positive, or leakage is negative (zero leakage is allowed).
    """
    if n_simultaneous > n_actuators:
        raise ValueError(
            "n_simultaneous %r exceeds n_actuators %r"
            % (n_simultaneous, n_actuators))
    _check_positive(n_actuators, "n_actuators")
    if leakage_lpm < 0:
        raise ValueError("leakage_lpm must be non-negative, got %r"
                         % leakage_lpm)
    demand = simultaneous_demand(actuator_flow_lpm, n_simultaneous)
    pump_lpm = demand + leakage_lpm
    return {
        "simultaneous_lpm": demand,
        "pump_flow_lpm": pump_lpm,
        "pump_flow_m3s": pump_lpm / LPM_PER_M3S,
    }


def pump_power(system_pressure_psi, pump_flow_m3s, efficiency):
    """Hydraulic pump drive power: p_pa * Q / eta.

    Returns dict {pressure_pa, pressure_mpa, power_w, power_kw}.
    ValueErrors on non-positive pressure or flow and on efficiency
    outside (0, 1].
    """
    _check_positive(system_pressure_psi, "system_pressure_psi")
    _check_positive(pump_flow_m3s, "pump_flow_m3s")
    if efficiency <= 0 or efficiency > 1:
        raise ValueError("efficiency must be in (0, 1], got %r"
                         % efficiency)
    pressure_pa = system_pressure_psi * PSI_PA
    power_w = pressure_pa * pump_flow_m3s / efficiency
    return {
        "pressure_pa": pressure_pa,
        "pressure_mpa": pressure_pa / 1.0e6,
        "power_w": power_w,
        "power_kw": power_w / 1000.0,
    }


def accumulator_volumes(charged_pressure_psi, depleted_pressure_psi,
                        usable_volume_l, n_gas=GAS_ADIABATIC_DEFAULT):
    """Emergency accumulator gas volumes from the adiabatic gas law.

    Solves p1 * V1^n = p2 * V2^n with V2 - V1 = usable volume between
    the charged and the depleted pressure. Closed form: ratio =
    (p1/p2)^(1/n), V1 = usable / (ratio - 1), V2 = V1 + usable.

    Returns dict {charged_gas_volume_l, depleted_gas_volume_l,
    closure_check}, where closure_check is the absolute difference of
    the two p * V^n sides (near zero on every input pair). ValueErrors
    on non-positive pressures, usable volume or n_gas, and when the
    depleted pressure is not below the charged pressure.
    """
    _check_positive(charged_pressure_psi, "charged_pressure_psi")
    _check_positive(depleted_pressure_psi, "depleted_pressure_psi")
    _check_positive(usable_volume_l, "usable_volume_l")
    _check_positive(n_gas, "n_gas")
    if depleted_pressure_psi >= charged_pressure_psi:
        raise ValueError(
            "depleted_pressure_psi %r must be below charged_pressure_psi %r"
            % (depleted_pressure_psi, charged_pressure_psi))
    ratio = (charged_pressure_psi / depleted_pressure_psi) ** (1.0 / n_gas)
    v1 = usable_volume_l / (ratio - 1.0)
    v2 = v1 + usable_volume_l
    # Closure sides in Pa * m^(3n): pressures converted internally to Pa
    # and volumes to m3, so the reported magnitude matches the SI
    # hand calculation of p1 * V1^n = p2 * V2^n.
    p1_pa = charged_pressure_psi * PSI_PA
    p2_pa = depleted_pressure_psi * PSI_PA
    lhs = p1_pa * ((v1 / 1000.0) ** n_gas)
    rhs = p2_pa * ((v2 / 1000.0) ** n_gas)
    return {
        "charged_gas_volume_l": v1,
        "depleted_gas_volume_l": v2,
        "closure_check": abs(lhs - rhs),
    }


def reservoir_volume(leakage_lpm, hold_minutes=DEFAULT_RESERVOIR_HOLD_MIN,
                     margin=DEFAULT_RESERVOIR_MARGIN):
    """Reservoir volume: leakage make-up over the hold time with margin.

    Returns leakage_lpm * hold_minutes * margin in L. ValueErrors on
    non-positive leakage or hold time and on margin below 1 (the
    reservoir must hold at least the unmargined make-up volume).
    """
    _check_positive(leakage_lpm, "leakage_lpm")
    _check_positive(hold_minutes, "hold_minutes")
    if margin < 1:
        raise ValueError("margin must be >= 1, got %r" % margin)
    return leakage_lpm * hold_minutes * margin


def hydraulic_system_summary(piston_area_m2, rod_speed_m_s, n_actuators,
                             n_simultaneous, system_pressure_psi,
                             efficiency, charged_pressure_psi,
                             depleted_pressure_psi, usable_volume_l,
                             leakage_lpm=DEFAULT_LEAKAGE_LPM,
                             n_gas=GAS_ADIABATIC_DEFAULT,
                             hold_minutes=DEFAULT_RESERVOIR_HOLD_MIN,
                             margin=DEFAULT_RESERVOIR_MARGIN):
    """Full hydraulic system sizing summary dict.

    Chains actuator_flow, pump_flow, pump_power, accumulator_volumes and
    reservoir_volume on one parameter set and returns every output key:
    flow_m3s, flow_lpm, simultaneous_lpm, pump_flow_lpm, pump_flow_m3s,
    pressure_pa, pressure_mpa, power_w, power_kw,
    charged_gas_volume_l, depleted_gas_volume_l, closure_check,
    reservoir_volume_l.
    """
    act = actuator_flow(piston_area_m2, rod_speed_m_s)
    pump = pump_flow(act["flow_lpm"], n_actuators, n_simultaneous,
                     leakage_lpm)
    power = pump_power(system_pressure_psi, pump["pump_flow_m3s"],
                       efficiency)
    acc = accumulator_volumes(charged_pressure_psi, depleted_pressure_psi,
                              usable_volume_l, n_gas)
    out = dict(act)
    out.update(pump)
    out.update(power)
    out.update(acc)
    out["reservoir_volume_l"] = reservoir_volume(
        leakage_lpm, hold_minutes, margin)
    return out
