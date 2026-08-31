#!/usr/bin/env python3
"""Descent performance (fixed-wing), SI units.

Contract: docs/harness-contract.md gate 3 - descent gradient from the
path angle, descent angle from the gradient, rate of descent from the
groundspeed and the gradient, glide range from the aerodynamic
efficiency and the height to lose, best glide speed from the wing
loading, top of descent distance and segment time for a
constant-gradient step-down, and descent fuel from the average fuel
flow and the segment time. All functions raise ValueError on invalid
inputs. Units are SI: forces in newtons (N), speeds in m/s, angles in
degrees, height in meters (m), time in seconds (s), fuel in
kilograms (kg).
"""

import math


def descent_gradient(angle_deg):
    """Descent gradient from the path angle.

    gradient = tan(gamma), dimensionless; percent = gradient * 100.
    Units: gamma in degrees; gradient unitless (a 3 deg path gives
    0.0524, about 318 ft per nautical mile).
    Raises ValueError if the angle is not in (0, 90) degrees.
    """
    if not 0.0 < angle_deg < 90.0:
        raise ValueError("descent path angle must be in (0, 90) degrees")
    return math.tan(math.radians(angle_deg))


def descent_angle_from_gradient(gradient):
    """Descent angle from the gradient.

    gamma = atan(gradient) in degrees, the inverse of
    descent_gradient.
    Units: gradient dimensionless; gamma in degrees.
    Raises ValueError if the gradient is <= 0 (level or climbing
    flight has no descent angle).
    """
    if gradient <= 0:
        raise ValueError("descent gradient must be positive")
    return math.degrees(math.atan(gradient))


def rate_of_descent(groundspeed, gradient):
    """Rate of descent from groundspeed and gradient.

    RoD = groundspeed * gradient in m/s, for a constant-gradient
    path (V/sin(gamma) equals groundspeed * tan(gamma) on small
    angles; the gradient form is exact for the path slope).
    Units: groundspeed in m/s; gradient dimensionless; RoD in m/s.
    Raises ValueError if groundspeed <= 0 or gradient <= 0.
    """
    if groundspeed <= 0:
        raise ValueError("groundspeed must be positive (m/s)")
    if gradient <= 0:
        raise ValueError("descent gradient must be positive")
    return groundspeed * gradient


def glide_range(glide_ratio, height_to_lose):
    """Glide range from the glide ratio and the height to lose.

    range = E * height_to_lose in m, the horizontal distance covered
    per unit height lost in a glide; E = L/D (aerodynamic
    efficiency) in steady gliding flight.
    Units: glide ratio dimensionless; height in m; range in m.
    Raises ValueError if glide_ratio <= 0 or height_to_lose <= 0.
    """
    if glide_ratio <= 0:
        raise ValueError("glide ratio must be positive")
    if height_to_lose <= 0:
        raise ValueError("height to lose must be positive (m)")
    return glide_ratio * height_to_lose


def best_glide_speed(weight, air_density, wing_area, cl_ld_max):
    """Best glide speed from the wing loading.

    v = sqrt(2 * W / (rho * S * CL_ld_max)) in m/s, the speed at
    which the glide ratio is maximum, where CL_ld_max is the lift
    coefficient at maximum L/D.
    Units: W in N (mass * g0); rho in kg/m3; S in m2; v in m/s.
    Raises ValueError if any input is <= 0.
    """
    if weight <= 0:
        raise ValueError("weight must be positive (N)")
    if air_density <= 0:
        raise ValueError("air density must be positive (kg/m3)")
    if wing_area <= 0:
        raise ValueError("wing area must be positive (m2)")
    if cl_ld_max <= 0:
        raise ValueError("lift coefficient at max L/D must be positive")
    return math.sqrt(2.0 * weight / (air_density * wing_area * cl_ld_max))


def top_of_descent_distance(height_to_lose, gradient):
    """Top of descent distance for a constant-gradient descent.

    d = height_to_lose / gradient in m, the horizontal distance at
    which the step-down descent must start to reach the target
    height on a constant-gradient path.
    Units: height in m; gradient dimensionless; d in m.
    Raises ValueError if height_to_lose <= 0 or gradient <= 0.
    """
    if height_to_lose <= 0:
        raise ValueError("height to lose must be positive (m)")
    if gradient <= 0:
        raise ValueError("descent gradient must be positive")
    return height_to_lose / gradient


def descent_time(height_to_lose, rate_of_descent_value):
    """Time for a descent segment at a constant rate of descent.

    t = height_to_lose / RoD in seconds.
    Units: height in m; RoD in m/s; t in s.
    Raises ValueError if height_to_lose <= 0 or RoD <= 0.
    """
    if height_to_lose <= 0:
        raise ValueError("height to lose must be positive (m)")
    if rate_of_descent_value <= 0:
        raise ValueError("rate of descent must be positive (m/s)")
    return height_to_lose / rate_of_descent_value


def descent_fuel(fuel_flow_avg, descent_time_value):
    """Fuel burned in a descent segment.

    m_fuel = fuel_flow * t in kg, from the average fuel flow over
    the segment (idle or flight-idle thrust flow).
    Units: fuel flow in kg/s; t in s; m_fuel in kg.
    Raises ValueError if fuel_flow <= 0 or time <= 0.
    """
    if fuel_flow_avg <= 0:
        raise ValueError("average fuel flow must be positive (kg/s)")
    if descent_time_value <= 0:
        raise ValueError("descent time must be positive (s)")
    return fuel_flow_avg * descent_time_value
