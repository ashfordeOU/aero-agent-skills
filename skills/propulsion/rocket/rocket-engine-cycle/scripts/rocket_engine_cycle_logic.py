"""Rocket engine feed-system cycle analysis (rocket-engine-cycle leaf).

Pure stdlib, SI units. Simplified liquid-engine balance for pressure-fed
and pump-fed (gas-generator, staged-combustion, expander) cycles: mass
flow from thrust and specific impulse, oxidizer/fuel split, pump
discharge pressure, pump power, turbine drive power, power balance,
feed-tank mass penalty, and a selection verdict. All typical-value
constants are reference-only with the documented assumption.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2

# Propellant reference table, reference-only typical values.
# Entry tuple: (rho_ox, rho_fuel, r_m, isp_vac). Densities kg/m3, r_m
# mixture ratio, isp_vac in seconds. r_m None marks the monopropellant
# hydrazine: one propellant stream, no oxidizer/fuel split.
PROPELLANTS = {
    "LOX/RP-1": (1140.0, 820.0, 2.56, 300.0),
    "LOX/LH2": (1140.0, 71.0, 5.5, 430.0),
    "N2O4/MMH": (1450.0, 880.0, 1.9, 320.0),
    "hydrazine": (1010.0, 1010.0, None, 230.0),
}

CYCLES = ("pressure-fed", "gas-generator", "staged-combustion", "expander")

P_LOSSES_DEFAULT = 2.0e6        # injector plus line loss, Pa
ETA_PUMP_DEFAULT = 0.7          # pump efficiency, dimensionless
ETA_TURB_DEFAULT = 0.6          # turbine efficiency, dimensionless
PUMP_INLET_PRESSURE = 0.3e6     # low-pressure feed tank seen by the pump, Pa
GG_FRACTION_DEFAULT = 0.03      # propellant fraction burned in the gas generator
GG_PRESSURE_FRACTION = 0.8      # gas-generator pressure as a fraction of p_c
TURBINE_EXIT_PRESSURE = 0.2e6   # turbine exhaust pressure, Pa
GG_CP = 2000.0                  # gas-generator gas cp, J/(kg K), reference-only
GG_T_INLET = 1200.0             # gas-generator gas temperature, K, reference-only
GG_GAMMA = 1.2                  # gas-generator gas specific heat ratio
STAGED_INLET_FRACTION = 1.5     # preburner discharge, fraction of p_c
EXPANDER_MAX_P_C = 10.0e6       # documented expander chamber-pressure bound, Pa
PRESSURE_FED_MAX_P_C = 3.0e6    # documented pressure-fed chamber-pressure bound, Pa
EXPANDER_CP = 12000.0           # warm hydrogen gas cp, J/(kg K), reference-only
EXPANDER_T_INLET = 500.0        # cooling-jacket outlet temperature, K, reference-only
EXPANDER_GAMMA = 1.4            # warm hydrogen specific heat ratio
EXPANDER_EXIT_FRACTION = 0.85   # turbine exit as a fraction of p_c, simplified
RHO_WALL = 4430.0               # titanium tank wall density, kg/m3
SIGMA_WALL = 880.0e6            # titanium allowable stress, Pa
REFERENCE_BURN_TIME = 60.0      # s, propellant basis for the tank mass trade


def _require_finite(*values):
    for value in values:
        if value is None or not math.isfinite(value):
            raise ValueError("inputs must be finite, got {0!r}".format(value))


def _require_eta(eta, name):
    _require_finite(eta)
    if not (0.0 < eta <= 1.0):
        raise ValueError("{0} must lie in (0, 1], got {1}".format(name, eta))


def propellant_pair_properties(pair_name):
    """Return (rho_ox, rho_fuel, r_m, isp_vac) for a known pair."""
    try:
        return PROPELLANTS[pair_name]
    except (KeyError, TypeError):
        raise ValueError("unknown propellant pair: {0}".format(pair_name))


def mass_flow_split(f, isp, g0, r_m):
    """Return (mdot, mdot_ox, mdot_f) from thrust f and Isp.

    A monopropellant (r_m None) returns mdot_ox = mdot, mdot_f = 0.
    """
    _require_finite(f, isp, g0)
    if f <= 0.0:
        raise ValueError("thrust must be positive, got {0}".format(f))
    if isp <= 0.0:
        raise ValueError("specific impulse must be positive, got {0}".format(isp))
    if g0 <= 0.0:
        raise ValueError("standard gravity must be positive, got {0}".format(g0))
    if r_m is not None:
        _require_finite(r_m)
        if r_m <= 0.0:
            raise ValueError("mixture ratio must be positive, got {0}".format(r_m))
    mdot = f / (isp * g0)
    if r_m is None:
        return mdot, mdot, 0.0
    mdot_ox = mdot * r_m / (1.0 + r_m)
    mdot_f = mdot / (1.0 + r_m)
    return mdot, mdot_ox, mdot_f


def pump_discharge_pressure(p_c, p_losses):
    """Pump discharge pressure covers chamber pressure plus losses."""
    _require_finite(p_c, p_losses)
    if p_c <= 0.0:
        raise ValueError("chamber pressure must be positive, got {0}".format(p_c))
    if p_losses < 0.0:
        raise ValueError("pressure losses must not be negative, got {0}".format(p_losses))
    return p_c + p_losses


def pump_power(mdot_prop, p_discharge, p_inlet, rho_prop, eta_pump):
    """Hydraulic pump power: mdot * (p_discharge - p_inlet) / (rho * eta)."""
    _require_finite(mdot_prop, p_discharge, p_inlet, rho_prop)
    _require_eta(eta_pump, "pump efficiency")
    if mdot_prop <= 0.0:
        raise ValueError("mass flow must be positive, got {0}".format(mdot_prop))
    if p_discharge <= 0.0:
        raise ValueError("discharge pressure must be positive, got {0}".format(p_discharge))
    if p_inlet < 0.0:
        raise ValueError("inlet pressure must not be negative, got {0}".format(p_inlet))
    if p_discharge <= p_inlet:
        raise ValueError("discharge pressure must exceed inlet pressure")
    if rho_prop <= 0.0:
        raise ValueError("density must be positive, got {0}".format(rho_prop))
    return mdot_prop * (p_discharge - p_inlet) / (rho_prop * eta_pump)


def turbine_power(mdot_gas, cp, t_inlet, eta_turb, gamma, p_inlet, p_exit):
    """Turbine drive power from an isentropic expansion model.

    P = mdot_gas * cp * T_inlet * eta_turb * (1 - (p_exit/p_inlet)^((gamma-1)/gamma))
    """
    _require_finite(mdot_gas, cp, t_inlet, p_inlet, p_exit)
    _require_eta(eta_turb, "turbine efficiency")
    if mdot_gas <= 0.0:
        raise ValueError("drive gas mass flow must be positive, got {0}".format(mdot_gas))
    if cp <= 0.0:
        raise ValueError("gas cp must be positive, got {0}".format(cp))
    if t_inlet <= 0.0:
        raise ValueError("turbine inlet temperature must be positive, got {0}".format(t_inlet))
    if gamma <= 1.0:
        raise ValueError("specific heat ratio must exceed 1, got {0}".format(gamma))
    if p_inlet <= 0.0 or p_exit <= 0.0:
        raise ValueError("turbine pressures must be positive")
    if p_exit >= p_inlet:
        raise ValueError("turbine exit pressure must be below inlet pressure")
    pressure_ratio = (p_exit / p_inlet) ** ((gamma - 1.0) / gamma)
    return mdot_gas * cp * t_inlet * eta_turb * (1.0 - pressure_ratio)


def cycle_feasibility(cycle, propellant, p_c):
    """Return (feasible, reason) for one cycle at chamber pressure p_c.

    Documented bounds: pressure-fed up to PRESSURE_FED_MAX_P_C, expander
    only for the LH2-fueled pair below EXPANDER_MAX_P_C. Gas-generator
    and staged-combustion are feasible across the range for bipropellant
    pairs. Unknown cycle or propellant raises ValueError.
    """
    if cycle not in CYCLES:
        raise ValueError("unknown engine cycle: {0}".format(cycle))
    _require_finite(p_c)
    if p_c <= 0.0:
        raise ValueError("chamber pressure must be positive, got {0}".format(p_c))
    rho_ox, rho_fuel, r_m, isp_vac = propellant_pair_properties(propellant)
    if cycle == "pressure-fed":
        if p_c <= PRESSURE_FED_MAX_P_C:
            return True, "chamber pressure within the pressure-fed bound"
        return False, ("chamber pressure above the {0:.0f} MPa pressure-fed bound, "
                       "tank mass penalty heavy".format(PRESSURE_FED_MAX_P_C / 1.0e6))
    if cycle == "expander":
        if propellant != "LOX/LH2":
            return False, ("expander drive needs the high heat-capacity LH2 fuel; "
                           "{0} does not qualify".format(propellant))
        if p_c > EXPANDER_MAX_P_C:
            return False, ("chamber pressure above the {0:.0f} MPa expander "
                           "bound".format(EXPANDER_MAX_P_C / 1.0e6))
        return True, "LH2 fuel heated in the cooling jacket drives the turbine"
    if r_m is None:
        return False, ("{0} needs an oxidizer/fuel pair; monopropellant has no "
                       "turbine drive gas split".format(cycle))
    return True, "turbine drive gas carried at part or full chamber pressure"


def mixture_bulk_density(rho_ox, rho_fuel, r_m):
    """Bulk density of the propellant pair, kg/m3."""
    _require_finite(rho_ox, rho_fuel)
    if rho_ox <= 0.0 or rho_fuel <= 0.0:
        raise ValueError("densities must be positive")
    if r_m is None:
        return rho_ox
    return (1.0 + r_m) / (r_m / rho_ox + 1.0 / rho_fuel)


def pressure_fed_tank_mass(p_tank, propellant_volume):
    """Thin-wall feed-tank mass, kg: p_tank * V * rho_wall / (2 * sigma)."""
    _require_finite(p_tank, propellant_volume)
    if p_tank <= 0.0:
        raise ValueError("tank pressure must be positive, got {0}".format(p_tank))
    if propellant_volume < 0.0:
        raise ValueError("propellant volume must not be negative")
    return p_tank * propellant_volume * RHO_WALL / (2.0 * SIGMA_WALL)


def engine_cycle_analysis(cycle, f, p_c, propellant, isp=None, p_losses=None,
                          eta_pump=None, eta_turb=None, gg_fraction=None,
                          p_tank_inlet=None, burn_time=None):
    """Full feed-cycle balance; returns the summary dict.

    Keys: cycle, propellant, feasible, reason, isp, mdot, mdot_ox,
    mdot_f, pump_discharge_pressure, pump_power_ox, pump_power_fuel,
    pump_power_total, turbine_power, power_balance, drive_mass_fraction,
    tank_pressure, tank_mass_penalty, verdict. Power balance is turbine
    power minus total pump power; pressure-fed sets machinery powers to
    zero and reports the feed-tank mass penalty instead.
    """
    if cycle not in CYCLES:
        raise ValueError("unknown engine cycle: {0}".format(cycle))
    _require_finite(f, p_c)
    if f <= 0.0:
        raise ValueError("thrust must be positive, got {0}".format(f))
    if p_c <= 0.0:
        raise ValueError("chamber pressure must be positive, got {0}".format(p_c))
    rho_ox, rho_fuel, r_m, isp_vac = propellant_pair_properties(propellant)
    isp_use = isp_vac if isp is None else isp
    _require_finite(isp_use)
    if isp_use <= 0.0:
        raise ValueError("specific impulse must be positive, got {0}".format(isp_use))
    p_losses = P_LOSSES_DEFAULT if p_losses is None else p_losses
    eta_pump = ETA_PUMP_DEFAULT if eta_pump is None else eta_pump
    eta_turb = ETA_TURB_DEFAULT if eta_turb is None else eta_turb
    gg_fraction = GG_FRACTION_DEFAULT if gg_fraction is None else gg_fraction
    p_tank_inlet = PUMP_INLET_PRESSURE if p_tank_inlet is None else p_tank_inlet
    burn_time = REFERENCE_BURN_TIME if burn_time is None else burn_time
    _require_eta(eta_pump, "pump efficiency")
    _require_eta(eta_turb, "turbine efficiency")
    _require_finite(p_losses, gg_fraction, p_tank_inlet, burn_time)
    if p_losses < 0.0:
        raise ValueError("pressure losses must not be negative")
    if not (0.0 < gg_fraction < 1.0):
        raise ValueError("gas-generator fraction must lie in (0, 1)")
    if p_tank_inlet < 0.0:
        raise ValueError("pump inlet pressure must not be negative")
    if burn_time <= 0.0:
        raise ValueError("burn time must be positive, got {0}".format(burn_time))

    mdot, mdot_ox, mdot_f = mass_flow_split(f, isp_use, G0, r_m)
    feasible, reason = cycle_feasibility(cycle, propellant, p_c)
    bulk_rho = mixture_bulk_density(rho_ox, rho_fuel, r_m)
    prop_volume = burn_time * mdot / bulk_rho

    pump_discharge = pump_discharge_pressure(p_c, p_losses)
    pump_ox = 0.0
    pump_fuel = 0.0
    pump_total = 0.0
    turb_power = 0.0
    drive_fraction = 0.0
    tank_pressure = 0.0

    if cycle == "pressure-fed":
        tank_pressure = p_c + p_losses
    elif cycle == "gas-generator":
        pump_ox = pump_power(mdot_ox, pump_discharge, p_tank_inlet, rho_ox, eta_pump)
        pump_fuel = pump_power(mdot_f, pump_discharge, p_tank_inlet, rho_fuel, eta_pump)
        pump_total = pump_ox + pump_fuel
        if feasible:
            mdot_gg = gg_fraction * mdot
            p_gg = GG_PRESSURE_FRACTION * p_c
            turb_power = turbine_power(mdot_gg, GG_CP, GG_T_INLET, eta_turb,
                                       GG_GAMMA, p_gg, TURBINE_EXIT_PRESSURE)
            drive_fraction = gg_fraction
        tank_pressure = p_tank_inlet
    elif cycle == "staged-combustion":
        pump_ox = pump_power(mdot_ox, pump_discharge, p_tank_inlet, rho_ox, eta_pump)
        pump_fuel = pump_power(mdot_f, pump_discharge, p_tank_inlet, rho_fuel, eta_pump)
        pump_total = pump_ox + pump_fuel
        if feasible:
            p_preburner = STAGED_INLET_FRACTION * p_c
            turb_power = turbine_power(mdot, GG_CP, GG_T_INLET, eta_turb,
                                       GG_GAMMA, p_preburner, TURBINE_EXIT_PRESSURE)
            drive_fraction = 1.0
        tank_pressure = p_tank_inlet
    elif cycle == "expander":
        pump_ox = pump_power(mdot_ox, pump_discharge, p_tank_inlet, rho_ox, eta_pump)
        pump_fuel = pump_power(mdot_f, pump_discharge, p_tank_inlet, rho_fuel, eta_pump)
        pump_total = pump_ox + pump_fuel
        if feasible:
            p_exit = EXPANDER_EXIT_FRACTION * p_c
            turb_power = turbine_power(mdot_f, EXPANDER_CP, EXPANDER_T_INLET,
                                       eta_turb, EXPANDER_GAMMA, p_c, p_exit)
            drive_fraction = mdot_f / mdot
        tank_pressure = p_tank_inlet

    tank_penalty = pressure_fed_tank_mass(tank_pressure, prop_volume)
    power_balance = turb_power - pump_total

    if cycle == "pressure-fed":
        if feasible:
            verdict = ("pressure-fed cycle feasible at p_c {0:.2f} MPa: tank pressure "
                       "{1:.2f} MPa, tank mass penalty {2:.1f} kg for the {3:.0f} s "
                       "burn basis; pump-fed trades pump machinery against this "
                       "tank".format(p_c / 1.0e6, tank_pressure / 1.0e6, tank_penalty,
                                     burn_time))
        else:
            verdict = ("pressure-fed cycle rejected at p_c {0:.2f} MPa: tank mass "
                       "penalty {1:.1f} kg is heavy against a low-pressure "
                       "pump-fed feed".format(p_c / 1.0e6, tank_penalty))
    elif not feasible:
        verdict = "cycle rejected: {0}".format(reason)
    elif power_balance >= 0.0:
        verdict = ("{0} cycle feasible: total pump power {1:.3f} MW, turbine power "
                   "{2:.3f} MW, surplus {3:.3f} MW, drive mass fraction "
                   "{4:.0%}".format(cycle, pump_total / 1.0e6, turb_power / 1.0e6,
                                    power_balance / 1.0e6, drive_fraction))
    else:
        verdict = ("{0} cycle feasible on the pressure bound but underpowered: "
                   "turbine power {1:.3f} MW against {2:.3f} MW of pump power, "
                   "deficit {3:.3f} MW".format(cycle, turb_power / 1.0e6,
                                               pump_total / 1.0e6,
                                               -power_balance / 1.0e6))

    return {
        "cycle": cycle,
        "propellant": propellant,
        "feasible": feasible,
        "reason": reason,
        "isp": isp_use,
        "mdot": mdot,
        "mdot_ox": mdot_ox,
        "mdot_f": mdot_f,
        "pump_discharge_pressure": pump_discharge,
        "pump_power_ox": pump_ox,
        "pump_power_fuel": pump_fuel,
        "pump_power_total": pump_total,
        "turbine_power": turb_power,
        "power_balance": power_balance,
        "drive_mass_fraction": drive_fraction,
        "tank_pressure": tank_pressure,
        "tank_mass_penalty": tank_penalty,
        "verdict": verdict,
    }
