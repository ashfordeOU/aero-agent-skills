"""Rotorcraft vertical climb performance with axial momentum theory.

Pure-stdlib logic for the flight-mechanics/performance/
rotorcraft-vertical-climb-performance leaf. Models a rotor in steady
vertical climb: the climb-induced velocity from momentum theory, the
induced and profile components of the climb power required, the climb
power margin against the available shaft power, and the maximum
vertical rate of climb found by bisection on the climb power balance.

Climb only: climb rates below zero (descending flight) are rejected.
Uniform inflow, no ground effect. SI units throughout.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2
RHO_SL = 1.225  # sea-level air density, kg/m^3
K_DEFAULT = 1.15  # induced power factor (wake and tip losses)
PI = math.pi


def disk_area(radius):
    """A = PI * radius**2. ValueError if radius <= 0."""
    if radius <= 0:
        raise ValueError("rotor radius must be positive")
    return PI * radius ** 2


def hover_induced_velocity(thrust, area, rho=RHO_SL):
    """v_h = sqrt(thrust / (2 * rho * area)). ValueError on invalid inputs."""
    if thrust <= 0:
        raise ValueError("thrust must be positive")
    if area <= 0:
        raise ValueError("rotor disk area must be positive")
    if rho <= 0:
        raise ValueError("air density must be positive")
    return math.sqrt(thrust / (2.0 * rho * area))


def climb_induced_velocity(thrust, area, climb_rate, rho=RHO_SL):
    """v_i = -Vc/2 + sqrt((Vc/2)**2 + v_h**2) for a vertical climb.

    Momentum-theory result for climb; the induced velocity decreases as
    the climb rate grows. Descending flight (climb_rate < 0) is out of
    scope and raises ValueError.
    """
    if climb_rate < 0:
        raise ValueError("climb rate must be non-negative (descending "
                         "flight is out of scope)")
    if thrust <= 0:
        raise ValueError("thrust must be positive")
    if area <= 0:
        raise ValueError("rotor disk area must be positive")
    if rho <= 0:
        raise ValueError("air density must be positive")
    v_h = hover_induced_velocity(thrust, area, rho)
    half = climb_rate / 2.0
    return -half + math.sqrt(half * half + v_h * v_h)


def profile_power(rho, area, solidity, drag_coefficient, tip_speed):
    """P_profile = (1/8) * rho * solidity * Cd0 * area * Vtip**3.

    Average section drag model, identical in form to the hover sibling.
    ValueError if any argument is <= 0.
    """
    if rho <= 0:
        raise ValueError("air density must be positive")
    if area <= 0:
        raise ValueError("rotor disk area must be positive")
    if solidity <= 0:
        raise ValueError("rotor solidity must be positive")
    if drag_coefficient <= 0:
        raise ValueError("blade drag coefficient must be positive")
    if tip_speed <= 0:
        raise ValueError("tip speed must be positive")
    return (1.0 / 8.0) * rho * solidity * drag_coefficient * area * \
        tip_speed ** 3


def climb_power(thrust, climb_rate, induced_velocity, profile_power,
                k=K_DEFAULT):
    """P = k * thrust * (climb_rate + induced_velocity) + profile_power.

    Total rotor power required in a vertical climb: induced component
    through the induced-power factor k plus the profile component.
    """
    if climb_rate < 0:
        raise ValueError("climb rate must be non-negative")
    if induced_velocity < 0:
        raise ValueError("induced velocity must be non-negative")
    if profile_power < 0:
        raise ValueError("profile power must be non-negative")
    if k <= 0:
        raise ValueError("induced power factor must be positive")
    return k * thrust * (climb_rate + induced_velocity) + profile_power


def climb_power_margin(available_power, required_power):
    """margin = available_power - required_power. ValueError if negative."""
    if available_power < 0:
        raise ValueError("available power must be non-negative")
    if required_power < 0:
        raise ValueError("required power must be non-negative")
    return available_power - required_power


def max_vertical_climb_rate(thrust, area, rho, available_power,
                            profile_power, k=K_DEFAULT):
    """Maximum vertical rate of climb from the shaft power available.

    Solves climb_power(Vc) = available_power for Vc by bisection on
    [0, 200] m/s. Climb power is strictly increasing in Vc because
    d(climb_power)/dVc = k*T*(1 + d(v_i)/dVc) > 0 with d(v_i)/dVc in
    (-1/2, 0). ValueError if available_power cannot even sustain hover
    (k * thrust * v_h + profile_power). If the balance does not cross
    within the bracket (excess power beyond the upper bound), returns
    the upper bracket value 200.0 without raising.
    """
    if available_power < 0:
        raise ValueError("available power must be non-negative")
    v_h = hover_induced_velocity(thrust, area, rho)
    hover_power = climb_power(thrust, 0.0, v_h, profile_power, k)
    if available_power < hover_power:
        raise ValueError("available power below the hover power at "
                         "Vc = 0: a vertical climb cannot be sustained")

    def power_at(climb_rate):
        v_i = climb_induced_velocity(thrust, area, climb_rate, rho)
        return climb_power(thrust, climb_rate, v_i, profile_power, k)

    lo, hi = 0.0, 200.0
    if power_at(hi) <= available_power:
        # The available power exceeds the power required at the upper
        # bracket end: excess-power case, return the bracket bound.
        return hi
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if power_at(mid) < available_power:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def vertical_climb_performance(weight_kg, radius, rho=RHO_SL,
                               solidity=0.08, drag_coefficient=0.012,
                               tip_speed=220.0, k=K_DEFAULT,
                               climb_rate=5.0, available_power=None):
    """Convenience chain returning the vertical climb performance dict.

    Keys: thrust_N, area_m2, hover_induced_velocity,
    climb_induced_velocity, profile_power_W, climb_power_W,
    climb_power_margin_W (None when available_power is None),
    max_vertical_climb_rate (None when available_power is None).
    thrust = weight_kg * G0. ValueErrors propagate from the primitives.
    """
    thrust = weight_kg * G0
    area = disk_area(radius)
    v_h = hover_induced_velocity(thrust, area, rho)
    v_i = climb_induced_velocity(thrust, area, climb_rate, rho)
    p_profile = profile_power(rho, area, solidity, drag_coefficient,
                              tip_speed)
    p_climb = climb_power(thrust, climb_rate, v_i, p_profile, k)
    if available_power is None:
        margin = None
        max_vc = None
    else:
        margin = climb_power_margin(available_power, p_climb)
        max_vc = max_vertical_climb_rate(thrust, area, rho,
                                         available_power, p_profile, k)
    return {
        "thrust_N": thrust,
        "area_m2": area,
        "hover_induced_velocity": v_h,
        "climb_induced_velocity": v_i,
        "profile_power_W": p_profile,
        "climb_power_W": p_climb,
        "climb_power_margin_W": margin,
        "max_vertical_climb_rate": max_vc,
    }
