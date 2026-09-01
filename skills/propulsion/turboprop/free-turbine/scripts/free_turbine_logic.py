#!/usr/bin/env python3
"""Free-turbine (power turbine) turboprop / turboshaft logic.

A free-turbine layout has two mechanically independent shafts: the gas
generator (compressor plus its turbine) and the power turbine, which is
connected to the gas generator only aerodynamically through the exhaust
stream. The power turbine converts the gas generator exhaust enthalpy
drop into shaft power and drives the propeller (turboprop) or rotor
(turboshaft) through a reduction gearbox.

Quantities (SI units throughout):
- gas generator exhaust mass flow m_dot in kg/s
- specific heat cp in J/(kg K)
- power-turbine inlet (gas generator exhaust) temperature t05 in K
- power-turbine exit temperature t06 in K
- power-turbine expansion ratio pr = p5/p6, dimensionless (p5 inlet
  static pressure, p6 exit static pressure)
- polytropic efficiency eta_pt, dimensionless in (0, 1]
- gamma, dimensionless (air-standard 1.4)
- shaft power P in W
- power-turbine speed rpm (shaft revolutions per minute)
- shaft torque Q in N m
- blade speed u in m/s from mean diameter and speed
- propeller speed n_prop in rpm; gear ratio G = rpm / n_prop
- fuel flow mf in kg/s; sfc in kg/(kW h)
- flow function FF = m_dot*sqrt(t05)/p5 in kg sqrt(K) / Pa, the
  swallowing capacity that must match the gas generator exhaust state

The power-turbine exit temperature follows the expansion:
t06 = t05 * (1 - eta_pt*(1 - pr**((1-gamma)/gamma))), and the shaft
power is P = m_dot*cp*(t05 - t06).

FAR-33 is referenced, not reproduced; the free-turbine matching
relations are common turbomachinery methodology summarized per
standards-map.yaml.

Functions raise ValueError on non-physical inputs (non-positive mass
flow, temperature, speed, or power; expansion ratio <= 1; efficiency
outside (0, 1]) instead of returning nonsense or dividing by zero.
"""

import math


def power_turbine_exit_temperature(t05, pr, eta_pt, gamma=1.4):
    """Power-turbine exit temperature t06 in K from inlet temperature,
    expansion ratio, and polytropic efficiency.

    t06 = t05 * (1 - eta_pt*(1 - pr**((1-gamma)/gamma))). The expansion
    ratio pr must exceed 1 (pressure falls across the turbine) and the
    efficiency must lie in (0, 1].
    """
    if t05 <= 0:
        raise ValueError("t05 must be > 0, got %r" % (t05,))
    if pr <= 1:
        raise ValueError("pr must be > 1, got %r" % (pr,))
    if not (0 < eta_pt <= 1):
        raise ValueError("eta_pt must be in (0, 1], got %r" % (eta_pt,))
    return t05 * (1.0 - eta_pt * (1.0 - pr ** ((1.0 - gamma) / gamma)))


def power_turbine_power(m_dot, cp, t05, pr, eta_pt, gamma=1.4):
    """Shaft power P = m_dot*cp*(t05 - t06) in W extracted by the free
    turbine from the gas generator exhaust enthalpy drop."""
    if m_dot <= 0:
        raise ValueError("m_dot must be > 0, got %r" % (m_dot,))
    if cp <= 0:
        raise ValueError("cp must be > 0, got %r" % (cp,))
    t06 = power_turbine_exit_temperature(t05, pr, eta_pt, gamma)
    return m_dot * cp * (t05 - t06)


def shaft_torque(P, rpm):
    """Shaft torque Q = P/omega in N m at power-turbine speed rpm."""
    if P <= 0:
        raise ValueError("P must be > 0, got %r" % (P,))
    if rpm <= 0:
        raise ValueError("rpm must be > 0, got %r" % (rpm,))
    omega = 2.0 * math.pi * rpm / 60.0
    return P / omega


def blade_speed(diameter, rpm):
    """Blade speed u = pi*diameter*rpm/60 in m/s at the mean diameter."""
    if diameter <= 0:
        raise ValueError("diameter must be > 0, got %r" % (diameter,))
    if rpm <= 0:
        raise ValueError("rpm must be > 0, got %r" % (rpm,))
    return math.pi * diameter * rpm / 60.0


def gear_ratio(n_pt, n_prop):
    """Reduction gearbox ratio G = n_pt/n_prop, dimensionless.

    The free turbine runs fast for good blade aerodynamics; the
    propeller or rotor runs slow, so G is normally well above 1.
    """
    if n_pt <= 0:
        raise ValueError("n_pt must be > 0, got %r" % (n_pt,))
    if n_prop <= 0:
        raise ValueError("n_prop must be > 0, got %r" % (n_prop,))
    return n_pt / n_prop


def specific_fuel_consumption(mf, P):
    """SFC in kg/(kW h): fuel flow per unit shaft power, hourly basis."""
    if mf <= 0:
        raise ValueError("mf must be > 0, got %r" % (mf,))
    if P <= 0:
        raise ValueError("P must be > 0, got %r" % (P,))
    return mf * 3600.0 * 1000.0 / P


def flow_function(m_dot, t05, p5):
    """Power-turbine swallowing capacity FF = m_dot*sqrt(t05)/p5 in
    kg sqrt(K) / Pa.

    The free-turbine nozzle must swallow the gas generator exhaust at
    every operating point; the flow function is the corrected-flow
    compatibility parameter between the two spools.
    """
    if m_dot <= 0:
        raise ValueError("m_dot must be > 0, got %r" % (m_dot,))
    if t05 <= 0:
        raise ValueError("t05 must be > 0, got %r" % (t05,))
    if p5 <= 0:
        raise ValueError("p5 must be > 0, got %r" % (p5,))
    return m_dot * math.sqrt(t05) / p5


def free_turbine_assessment(m_dot, cp, t05, pr, eta_pt, rpm, diameter,
                            n_prop, mf, p5, gamma=1.4):
    """Full free-turbine matching assessment as a dict.

    Returns exit_temperature (K), shaft_power (W), torque (N m),
    blade_speed (m/s), gear_ratio (dimensionless), sfc (kg/(kW h)),
    and flow_function (kg sqrt(K)/Pa) for the given gas generator
    exhaust state and power-turbine speed selection.
    """
    t06 = power_turbine_exit_temperature(t05, pr, eta_pt, gamma)
    P = power_turbine_power(m_dot, cp, t05, pr, eta_pt, gamma)
    return {
        "exit_temperature": t06,
        "shaft_power": P,
        "torque": shaft_torque(P, rpm),
        "blade_speed": blade_speed(diameter, rpm),
        "gear_ratio": gear_ratio(rpm, n_prop),
        "sfc": specific_fuel_consumption(mf, P),
        "flow_function": flow_function(m_dot, t05, p5),
    }
