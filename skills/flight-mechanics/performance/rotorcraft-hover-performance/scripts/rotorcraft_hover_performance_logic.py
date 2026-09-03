"""Rotorcraft hover performance from momentum theory.

Pure stdlib implementation of the standard momentum-theory hover model
for a rotorcraft rotor: ideal induced velocity through the rotor disk,
ideal hover power, profile power from the average section drag model,
total hover power with an induced-power factor or through the figure of
merit, the figure of merit itself, and the disk loading.

The model is momentum theory only: uniform inflow over the disk, no
ground effect, no recirculation, no forward flight. Geometry (radius,
solidity, blade drag coefficient, tip speed) is an input; this module
does not size the rotor.

All functions return floats in SI units. Non-physical inputs raise
ValueError. Deterministic: no randomness anywhere.
"""

import math

# Module constants (SI).
G0 = 9.80665          # standard sea-level gravitational acceleration, m/s^2
RHO_SL = 1.225        # sea-level air density, kg/m^3 (default only)
K_DEFAULT = 1.15      # default induced power factor (losses in the wake)
PI = math.pi


def disk_area(radius):
    """Rotor disk area A = PI * radius**2 in m^2. Radius must be > 0."""
    if radius <= 0:
        raise ValueError("radius must be positive")
    return PI * radius ** 2


def induced_velocity(thrust, area, rho=RHO_SL):
    """Ideal induced velocity v_i = sqrt(thrust / (2 * rho * area)) in m/s.

    Momentum theory for hover: the rotor accelerates the air through the
    disk so that the induced velocity at the disk plane is half the far
    wake velocity, giving T = 2 * rho * A * v_i**2.
    """
    if thrust <= 0:
        raise ValueError("thrust must be positive")
    if area <= 0:
        raise ValueError("area must be positive")
    if rho <= 0:
        raise ValueError("rho must be positive")
    return math.sqrt(thrust / (2.0 * rho * area))


def ideal_power(thrust, induced_velocity):
    """Ideal hover power P_ideal = thrust * v_i in W."""
    if thrust < 0:
        raise ValueError("thrust must be non-negative")
    if induced_velocity < 0:
        raise ValueError("induced_velocity must be non-negative")
    return thrust * induced_velocity


def profile_power(rho, area, solidity, drag_coefficient, tip_speed):
    """Profile power P_profile = (1/8) * rho * sigma * Cd0 * A * Vtip**3 in W.

    Average section drag model: the blade elements sweep the disk area at
    the tip speed and the section drag is captured through the solidity
    sigma and the mean drag coefficient Cd0.
    """
    if rho <= 0:
        raise ValueError("rho must be positive")
    if area <= 0:
        raise ValueError("area must be positive")
    if solidity <= 0:
        raise ValueError("solidity must be positive")
    if drag_coefficient <= 0:
        raise ValueError("drag_coefficient must be positive")
    if tip_speed <= 0:
        raise ValueError("tip_speed must be positive")
    return (1.0 / 8.0) * rho * solidity * drag_coefficient * area * tip_speed ** 3


def total_power(ideal_power, induced_velocity, thrust, profile_power,
                k=K_DEFAULT):
    """Total hover power P_total = k * thrust * v_i + P_profile in W.

    The induced power factor k scales the ideal induced power (thrust
    times induced velocity) to account for wake losses, tip losses and
    non-uniform inflow.
    """
    if ideal_power < 0:
        raise ValueError("ideal_power must be non-negative")
    if profile_power < 0:
        raise ValueError("profile_power must be non-negative")
    if k <= 0:
        raise ValueError("k must be positive")
    return k * thrust * induced_velocity + profile_power


def power_from_figure_of_merit(ideal_power, figure_of_merit):
    """Total hover power implied by an ideal power and a figure of merit.

    P_total = P_ideal / FM. The figure of merit must lie in (0, 1].
    """
    if ideal_power < 0:
        raise ValueError("ideal_power must be non-negative")
    if figure_of_merit <= 0:
        raise ValueError("figure_of_merit must be positive")
    if figure_of_merit > 1.0:
        raise ValueError("figure_of_merit cannot exceed 1.0")
    return ideal_power / figure_of_merit


def figure_of_merit(ideal_power, total_power):
    """Figure of merit FM = P_ideal / P_total (dimensionless).

    The fraction of the total hover power that appears as useful induced
    power; real rotors sit well below 1 because of profile and induced
    losses.
    """
    if ideal_power < 0:
        raise ValueError("ideal_power must be non-negative")
    if total_power <= 0:
        raise ValueError("total_power must be positive")
    if ideal_power > total_power:
        raise ValueError("ideal_power cannot exceed total_power")
    return ideal_power / total_power


def disk_loading(thrust, area):
    """Disk loading DL = thrust / area in Pa."""
    if thrust < 0:
        raise ValueError("thrust must be non-negative")
    if area <= 0:
        raise ValueError("area must be positive")
    return thrust / area


def hover_performance(weight_kg, radius, rho=RHO_SL, solidity=0.08,
                      drag_coefficient=0.012, tip_speed=220.0, k=K_DEFAULT):
    """Convenience chain for one hover operating point.

    Returns a dict with keys: thrust_N, area_m2, induced_velocity,
    ideal_power_W, profile_power_W, total_power_W, figure_of_merit,
    disk_loading_Pa. Thrust is the rotorcraft weight (weight_kg * G0)
    in hover. ValueErrors from the primitives propagate.
    """
    thrust = weight_kg * G0
    area = disk_area(radius)
    v_i = induced_velocity(thrust, area, rho)
    p_ideal = ideal_power(thrust, v_i)
    p_profile = profile_power(rho, area, solidity, drag_coefficient,
                              tip_speed)
    p_total = total_power(p_ideal, v_i, thrust, p_profile, k)
    return {
        "thrust_N": thrust,
        "area_m2": area,
        "induced_velocity": v_i,
        "ideal_power_W": p_ideal,
        "profile_power_W": p_profile,
        "total_power_W": p_total,
        "figure_of_merit": figure_of_merit(p_ideal, p_total),
        "disk_loading_Pa": disk_loading(thrust, area),
    }
