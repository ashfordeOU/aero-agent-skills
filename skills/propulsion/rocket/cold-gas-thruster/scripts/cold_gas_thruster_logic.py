"""Cold gas thruster sizing logic (pure Python stdlib).

Size and assess a cold gas reaction control thruster for spacecraft
attitude control: choked nozzle mass flow from plenum pressure and
temperature, thrust from mass flow and specific impulse, tank gas mass
from plenum volume and pressure, isothermal blowdown time constant and
pressure history, operating time to a minimum usable pressure, and
total impulse between the initial and final pressures.

All inputs are SI: pascals, cubic meters, kelvin, meters, seconds.
Deterministic, offline, no external dependencies.

Standards context: ECSS spacecraft propulsion engineering, reference
only; the relations here are standard engineering methodology.
"""

import math

G0 = 9.80665          # standard gravity, m/s^2
GAMMA_N2 = 1.4        # ratio of specific heats for nitrogen
R_N2 = 296.8          # specific gas constant for nitrogen, J/(kg K)


def _cf_const(gamma, gas_const):
    """Return the choked-flow factor for a gas.

    sqrt(gamma / R * (2 / (gamma + 1)) ** ((gamma + 1) / (gamma - 1))).
    """
    return math.sqrt(
        gamma / gas_const
        * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0))
    )


# Choked-flow factor for nitrogen computed from GAMMA_N2 and R_N2.
CF_CONST = _cf_const(GAMMA_N2, R_N2)


def choked_mass_flow(pressure, temperature, throat_area,
                     gamma=GAMMA_N2, gas_const=R_N2):
    """Return the choked mass flow m_dot in kg/s through the throat.

    m_dot = pressure * throat_area / sqrt(temperature) * sqrt(gamma / R
    * (2 / (gamma + 1)) ** ((gamma + 1) / (gamma - 1))).
    Raises ValueError on non-positive pressure, temperature or area.
    """
    if pressure <= 0.0:
        raise ValueError("pressure must be positive")
    if temperature <= 0.0:
        raise ValueError("temperature must be positive")
    if throat_area <= 0.0:
        raise ValueError("throat_area must be positive")
    factor = _cf_const(gamma, gas_const)
    return pressure * throat_area / math.sqrt(temperature) * factor


def thrust(mass_flow, isp):
    """Return the thrust F in N from F = mass_flow * isp * G0.

    Raises ValueError on negative mass flow or non-positive isp.
    """
    if mass_flow < 0.0:
        raise ValueError("mass_flow must be non-negative")
    if isp <= 0.0:
        raise ValueError("isp must be positive")
    return mass_flow * isp * G0


def tank_gas_mass(pressure, volume, temperature, gas_const=R_N2):
    """Return the gas mass in kg in the plenum tank from the ideal gas law.

    m = pressure * volume / (gas_const * temperature).
    Raises ValueError on non-positive pressure, volume or temperature.
    """
    if pressure <= 0.0:
        raise ValueError("pressure must be positive")
    if volume <= 0.0:
        raise ValueError("volume must be positive")
    if temperature <= 0.0:
        raise ValueError("temperature must be positive")
    return pressure * volume / (gas_const * temperature)


def blowdown_time_constant(tank_mass, mass_flow0):
    """Return the isothermal blowdown time constant tau in s.

    tau = tank_mass / mass_flow0.
    Raises ValueError on non-positive tank mass or mass flow.
    """
    if tank_mass <= 0.0:
        raise ValueError("tank_mass must be positive")
    if mass_flow0 <= 0.0:
        raise ValueError("mass_flow0 must be positive")
    return tank_mass / mass_flow0


def pressure_at_time(p0, t, tau):
    """Return the plenum pressure in Pa at time t under isothermal blowdown.

    p = p0 * exp(-t / tau). Raises ValueError on non-positive tau or
    negative time t.
    """
    if tau <= 0.0:
        raise ValueError("tau must be positive")
    if t < 0.0:
        raise ValueError("t must be non-negative")
    return p0 * math.exp(-t / tau)


def operating_time(p0, p_min, tau):
    """Return the operating time in s to reach the minimum pressure.

    t = tau * ln(p0 / p_min). Raises ValueError when p_min is not in
    (0, p0).
    """
    if p0 <= 0.0:
        raise ValueError("p0 must be positive")
    if p_min <= 0.0:
        raise ValueError("p_min must be positive")
    if p_min >= p0:
        raise ValueError("p_min must be below p0")
    return tau * math.log(p0 / p_min)


def total_impulse(isp, tank_mass0, tank_mass_final):
    """Return the total impulse I in Ns over the blowdown.

    I = isp * G0 * (tank_mass0 - tank_mass_final). Raises ValueError
    when the final mass exceeds the initial mass or isp is not positive.
    """
    if isp <= 0.0:
        raise ValueError("isp must be positive")
    if tank_mass_final > tank_mass0:
        raise ValueError("tank_mass_final must not exceed tank_mass0")
    return isp * G0 * (tank_mass0 - tank_mass_final)


def size_thruster(plenum_pressure, plenum_volume, temperature,
                  throat_diameter, isp, p_min, t_query=30.0):
    """Chain the cold gas thruster sizing model into one result dict.

    Returns {throat_area, mass_flow0, thrust_N, tank_mass_kg,
    time_constant_s, pressure_at_tquery, operating_time_s,
    total_impulse_Ns, mass_at_pmin}. Inputs are SI. ValueErrors from
    the underlying checks propagate.
    """
    if throat_diameter <= 0.0:
        raise ValueError("throat_diameter must be positive")
    if p_min <= 0.0:
        raise ValueError("p_min must be positive")
    if p_min >= plenum_pressure:
        raise ValueError("p_min must be below plenum_pressure")
    if t_query < 0.0:
        raise ValueError("t_query must be non-negative")
    throat_area = math.pi * throat_diameter ** 2 / 4.0
    mass_flow0 = choked_mass_flow(
        plenum_pressure, temperature, throat_area)
    thrust_N = thrust(mass_flow0, isp)
    tank_mass_kg = tank_gas_mass(plenum_pressure, plenum_volume,
                                 temperature)
    time_constant_s = blowdown_time_constant(tank_mass_kg, mass_flow0)
    pressure_at_tquery = pressure_at_time(
        plenum_pressure, t_query, time_constant_s)
    operating_time_s = operating_time(
        plenum_pressure, p_min, time_constant_s)
    mass_at_pmin = tank_gas_mass(p_min, plenum_volume, temperature)
    total_impulse_Ns = total_impulse(isp, tank_mass_kg, mass_at_pmin)
    return {
        "throat_area": throat_area,
        "mass_flow0": mass_flow0,
        "thrust_N": thrust_N,
        "tank_mass_kg": tank_mass_kg,
        "time_constant_s": time_constant_s,
        "pressure_at_tquery": pressure_at_tquery,
        "operating_time_s": operating_time_s,
        "total_impulse_Ns": total_impulse_Ns,
        "mass_at_pmin": mass_at_pmin,
    }
