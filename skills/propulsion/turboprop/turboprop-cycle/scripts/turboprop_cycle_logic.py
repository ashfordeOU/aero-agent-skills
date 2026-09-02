#!/usr/bin/env python3
"""Turboprop cycle and propeller performance logic.

A turboprop extracts most of the gas generator power as shaft power and
drives a propeller; a small residual jet thrust remains from the
exhaust. The propeller converts shaft power into thrust with a
propeller (Froude) efficiency that depends on the flight velocity and
the slipstream velocity. This module computes the cycle-side and
propeller-side performance:

- propeller (Froude) efficiency eta_p = 2 / (1 + vj / vf) from flight
  velocity vf and slipstream velocity vj
- thrust from shaft power at cruise: T = eta_p * P / V
- static thrust (zero flight speed) from the actuator-disk relation
  T0 = (2 * rho * A * P^2)^(1/3) with disk area A = pi/4 * D^2
- equivalent shaft power ESP = P + Tj * V / eta_p, crediting the
  residual jet thrust Tj at the propeller efficiency
- advance ratio J = V / (n * D), power coefficient
  Cp = P / (rho * n^3 * D^5), and thrust coefficient
  Ct = T / (rho * n^2 * D^4), with n = rpm / 60 in rev/s
- specific fuel consumption on shaft power SFC = mf / P in kg/(kW h)
- overall efficiency eta_o = eta_th * eta_p * eta_m

SI units throughout: velocity in m/s, power in W, thrust in N,
diameter in m, rpm in rev/min, density in kg/m^3, fuel flow in kg/s.

FAR-33 is referenced, not reproduced; the propeller and actuator-disk
relations are common propulsion methodology summarized per
standards-map.yaml.

Functions raise ValueError on non-physical inputs (non-positive
velocities, diameters, densities, speeds, or powers; efficiency outside
(0, 1]) instead of returning nonsense or dividing by zero.
"""

import math


def propeller_efficiency(flight_velocity, slipstream_velocity):
    """Return the propeller (Froude) efficiency from flight velocity vf
    and slipstream velocity vj.

    eta_p = 2 / (1 + vj / vf). The propeller accelerates the air from
    the free-stream velocity vf to the slipstream velocity vj, and the
    ideal efficiency is the useful thrust power over the total power:
    eta_p = 2 * vf / (vf + vj). When vj = vf there is no acceleration
    and eta_p = 1; when vj = 2*vf the efficiency falls to 2/3.

    Raises ValueError for a non-positive flight velocity, a slipstream
    velocity below the flight velocity, or a slipstream velocity of
    zero.
    """
    if flight_velocity <= 0:
        raise ValueError("flight velocity must be > 0, got %r" % (flight_velocity,))
    if slipstream_velocity < flight_velocity:
        raise ValueError(
            "slipstream velocity must be >= flight velocity, got %r"
            % (slipstream_velocity,)
        )
    if slipstream_velocity <= 0:
        raise ValueError(
            "slipstream velocity must be > 0, got %r" % (slipstream_velocity,)
        )
    return 2.0 / (1.0 + slipstream_velocity / flight_velocity)


def thrust_from_shaft_power(shaft_power, flight_velocity, propeller_efficiency):
    """Return the thrust in N produced by shaft power P at flight
    velocity V with propeller efficiency eta_p.

    T = eta_p * P / V. The propeller converts the shaft power into
    useful thrust power T * V with the propeller efficiency.

    Raises ValueError for a negative shaft power, a non-positive flight
    velocity, or an efficiency outside (0, 1].
    """
    if shaft_power < 0:
        raise ValueError("shaft power must be >= 0, got %r" % (shaft_power,))
    if flight_velocity <= 0:
        raise ValueError("flight velocity must be > 0, got %r" % (flight_velocity,))
    if not (0 < propeller_efficiency <= 1):
        raise ValueError(
            "propeller efficiency must be in (0, 1], got %r" % (propeller_efficiency,)
        )
    return propeller_efficiency * shaft_power / flight_velocity


def propeller_disk_area(diameter):
    """Return the propeller disk area A = pi/4 * D^2 in m^2.

    Raises ValueError for a non-positive diameter.
    """
    if diameter <= 0:
        raise ValueError("diameter must be > 0, got %r" % (diameter,))
    return math.pi / 4.0 * diameter * diameter


def static_thrust(shaft_power, air_density, diameter):
    """Return the static thrust in N at zero flight speed.

    Actuator-disk momentum theory gives T0 = (2 * rho * A * P^2)^(1/3)
    with A the propeller disk area. At zero speed the propeller does
    useful thrust power of zero, so the whole power goes into the
    induced velocity and the static thrust is the cube root of the
    power squared.

    Raises ValueError for a negative shaft power, a non-positive air
    density, or a non-positive diameter.
    """
    if shaft_power < 0:
        raise ValueError("shaft power must be >= 0, got %r" % (shaft_power,))
    if air_density <= 0:
        raise ValueError("air density must be > 0, got %r" % (air_density,))
    if diameter <= 0:
        raise ValueError("diameter must be > 0, got %r" % (diameter,))
    area = propeller_disk_area(diameter)
    return (2.0 * air_density * area * shaft_power * shaft_power) ** (1.0 / 3.0)


def equivalent_shaft_power(
    shaft_power, jet_thrust, flight_velocity, propeller_efficiency
):
    """Return the equivalent shaft power ESP in W.

    ESP = P + Tj * V / eta_p credits the residual jet thrust Tj by the
    shaft power that would produce the same thrust at the propeller
    efficiency. The turboprop exhaust still carries a small jet thrust,
    so the equivalent shaft power compares the whole powerplant with a
    pure propeller drive.

    Raises ValueError for a negative shaft power, a negative jet
    thrust, a non-positive flight velocity, or an efficiency outside
    (0, 1].
    """
    if shaft_power < 0:
        raise ValueError("shaft power must be >= 0, got %r" % (shaft_power,))
    if jet_thrust < 0:
        raise ValueError("jet thrust must be >= 0, got %r" % (jet_thrust,))
    if flight_velocity <= 0:
        raise ValueError("flight velocity must be > 0, got %r" % (flight_velocity,))
    if not (0 < propeller_efficiency <= 1):
        raise ValueError(
            "propeller efficiency must be in (0, 1], got %r" % (propeller_efficiency,)
        )
    return shaft_power + jet_thrust * flight_velocity / propeller_efficiency


def specific_fuel_consumption(fuel_mass_flow, shaft_power):
    """Return the specific fuel consumption on shaft power in kg/(kW h).

    SFC = mf * 3600 * 1000 / P with mf in kg/s and P in W, converting
    to fuel per kilowatt-hour of shaft power.

    Raises ValueError for a negative fuel flow or a non-positive shaft
    power.
    """
    if fuel_mass_flow < 0:
        raise ValueError("fuel mass flow must be >= 0, got %r" % (fuel_mass_flow,))
    if shaft_power <= 0:
        raise ValueError("shaft power must be > 0, got %r" % (shaft_power,))
    return fuel_mass_flow * 3600.0 * 1000.0 / shaft_power


def advance_ratio(flight_velocity, rpm, diameter):
    """Return the propeller advance ratio J = V / (n * D).

    n = rpm / 60 is the rotation speed in rev/s and D the propeller
    diameter. The advance ratio measures how far the propeller advances
    per revolution in terms of diameters.

    Raises ValueError for a negative flight velocity, a non-positive
    rpm, or a non-positive diameter.
    """
    if flight_velocity < 0:
        raise ValueError("flight velocity must be >= 0, got %r" % (flight_velocity,))
    if rpm <= 0:
        raise ValueError("rpm must be > 0, got %r" % (rpm,))
    if diameter <= 0:
        raise ValueError("diameter must be > 0, got %r" % (diameter,))
    n = rpm / 60.0
    return flight_velocity / (n * diameter)


def power_coefficient(shaft_power, air_density, rpm, diameter):
    """Return the propeller power coefficient Cp = P / (rho * n^3 * D^5).

    n = rpm / 60 in rev/s. The power coefficient is the dimensionless
    form of the shaft power absorbed by the propeller.

    Raises ValueError for a negative shaft power, a non-positive air
    density, rpm, or diameter.
    """
    if shaft_power < 0:
        raise ValueError("shaft power must be >= 0, got %r" % (shaft_power,))
    if air_density <= 0:
        raise ValueError("air density must be > 0, got %r" % (air_density,))
    if rpm <= 0:
        raise ValueError("rpm must be > 0, got %r" % (rpm,))
    if diameter <= 0:
        raise ValueError("diameter must be > 0, got %r" % (diameter,))
    n = rpm / 60.0
    return shaft_power / (air_density * n ** 3 * diameter ** 5)


def thrust_coefficient(thrust, air_density, rpm, diameter):
    """Return the propeller thrust coefficient Ct = T / (rho * n^2 * D^4).

    n = rpm / 60 in rev/s. The thrust coefficient is the dimensionless
    form of the propeller thrust.

    Raises ValueError for a negative thrust, a non-positive air
    density, rpm, or diameter.
    """
    if thrust < 0:
        raise ValueError("thrust must be >= 0, got %r" % (thrust,))
    if air_density <= 0:
        raise ValueError("air density must be > 0, got %r" % (air_density,))
    if rpm <= 0:
        raise ValueError("rpm must be > 0, got %r" % (rpm,))
    if diameter <= 0:
        raise ValueError("diameter must be > 0, got %r" % (diameter,))
    n = rpm / 60.0
    return thrust / (air_density * n ** 2 * diameter ** 4)


def overall_efficiency(thermal_efficiency, propeller_efficiency, mechanical_efficiency=1.0):
    """Return the overall turboprop efficiency eta_o.

    eta_o = eta_th * eta_p * eta_m: the thermal efficiency of the gas
    generator cycle times the propeller efficiency times the
    mechanical efficiency of the shaft and gearbox transmission.

    Raises ValueError for any efficiency outside (0, 1].
    """
    if not (0 < thermal_efficiency <= 1):
        raise ValueError(
            "thermal efficiency must be in (0, 1], got %r" % (thermal_efficiency,)
        )
    if not (0 < propeller_efficiency <= 1):
        raise ValueError(
            "propeller efficiency must be in (0, 1], got %r" % (propeller_efficiency,)
        )
    if not (0 < mechanical_efficiency <= 1):
        raise ValueError(
            "mechanical efficiency must be in (0, 1], got %r" % (mechanical_efficiency,)
        )
    return thermal_efficiency * propeller_efficiency * mechanical_efficiency
