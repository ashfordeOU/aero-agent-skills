"""Rotorcraft range and endurance fuel closure.

Pure stdlib implementation that closes the fuel budget of a rotorcraft
into hover endurance and cruise range and endurance. Hover power comes
from the weight, the rotor disk area and the figure of merit through the
W^1.5 weight-scaling power law; the fuel burn is integrated over the
weight decay to a closed-form hover endurance. For cruise the module
takes an input power-required curve (computed by the forward-flight
sibling leaf), scales the power with the average weight to the 1.5
power, and produces the range and endurance over the fuel load at a
chosen speed together with the best-range and best-endurance speeds
picked off the curve.

All functions return floats in SI units: weight in N, power in W, rotor
radius in m, density in kg/m^3, fuel in kg, time in s, distance in m.
Non-physical inputs raise ValueError. Deterministic: no randomness
anywhere, stdlib only.
"""

import math

# Module constants (SI).
G0 = 9.80665          # standard gravitational acceleration, m/s^2
RHO_SL = 1.225        # sea-level air density, kg/m^3 (default only)
C_SPEC_DEFAULT = 1.0e-7  # default specific fuel consumption, kg/(s W), about 0.36 kg/kWh
FM_DEFAULT = 0.75     # default rotor figure of merit (hover power efficiency)
PI = math.pi


def disk_area(radius):
    """Rotor disk area A = PI * radius**2 in m^2. Radius must be > 0."""
    if radius <= 0:
        raise ValueError("radius must be positive")
    return PI * radius * radius


def hover_power_constant(radius, rho=RHO_SL, figure_of_merit=FM_DEFAULT):
    """Hover power law constant k_h = 1 / (FM * sqrt(2 * rho * A)) in SI.

    Combines the rotor disk area, the air density and the figure of
    merit into the single constant of the W^1.5 hover power law.
    """
    if radius <= 0:
        raise ValueError("radius must be positive")
    if rho <= 0:
        raise ValueError("density must be positive")
    if figure_of_merit <= 0 or figure_of_merit > 1:
        raise ValueError("figure of merit must be in (0, 1]")
    return 1.0 / (figure_of_merit * math.sqrt(2.0 * rho * disk_area(radius)))


def hover_power(weight_n, radius, rho=RHO_SL, figure_of_merit=FM_DEFAULT):
    """Hover power P = k_h * W^1.5 in W at a given rotorcraft weight."""
    if weight_n <= 0:
        raise ValueError("weight must be positive")
    k_h = hover_power_constant(radius, rho, figure_of_merit)
    return k_h * weight_n ** 1.5


def hover_endurance(weight_initial_n, fuel_mass_kg, radius, rho=RHO_SL,
                    figure_of_merit=FM_DEFAULT, c_specific=C_SPEC_DEFAULT,
                    g0=G0):
    """Hover endurance in s from the exact weight-decay integral.

    With the fuel burn rate dW/dt = -g0 * c * P and P = k_h * W^1.5 the
    integral closes to t = (2 / (g0 * c * k_h)) * (1/sqrt(W1) - 1/sqrt(W0))
    with W1 = W0 - g0 * fuel_mass_kg. Fuel mass must leave a positive
    final weight W1.
    """
    if weight_initial_n <= 0:
        raise ValueError("initial weight must be positive")
    if fuel_mass_kg < 0:
        raise ValueError("fuel mass must not be negative")
    if c_specific <= 0:
        raise ValueError("specific fuel consumption must be positive")
    w0 = weight_initial_n
    w1 = w0 - g0 * fuel_mass_kg
    if w1 <= 0:
        raise ValueError("fuel mass must leave a positive final weight")
    if fuel_mass_kg == 0.0:
        return 0.0
    k_h = hover_power_constant(radius, rho, figure_of_merit)
    return (2.0 / (g0 * c_specific * k_h)) * (1.0 / math.sqrt(w1) - 1.0 / math.sqrt(w0))


def fuel_flow(weight_n, radius, rho=RHO_SL, figure_of_merit=FM_DEFAULT,
              c_specific=C_SPEC_DEFAULT):
    """Fuel flow mdot = c_specific * P(weight) in kg/s at a given weight."""
    return c_specific * hover_power(weight_n, radius, rho, figure_of_merit)


def specific_range(v_ms, power_w, c_specific=C_SPEC_DEFAULT, g0=G0):
    """Specific range V / (g0 * c * P), metres of cruise range per kg of fuel."""
    if v_ms <= 0:
        raise ValueError("speed must be positive")
    if power_w <= 0:
        raise ValueError("power must be positive")
    if c_specific <= 0:
        raise ValueError("specific fuel consumption must be positive")
    return v_ms / (g0 * c_specific * power_w)


def _validate_power_curve(power_curve):
    """Reject empty curves and curves with non-positive (v, P) pairs."""
    if not power_curve:
        raise ValueError("power curve must not be empty")
    for v_ms, power_w in power_curve:
        if v_ms <= 0 or power_w <= 0:
            raise ValueError("power curve pairs must have positive speed and power")


def best_range_speed(power_curve):
    """Best-range speed v (m/s): maximizes specific_range over the curve."""
    _validate_power_curve(power_curve)
    return max(power_curve, key=lambda pair: specific_range(pair[0], pair[1]))[0]


def best_endurance_speed(power_curve):
    """Best-endurance speed v (m/s): minimizes power over the curve."""
    _validate_power_curve(power_curve)
    return min(power_curve, key=lambda pair: pair[1])[0]


def _average_power(power_at_ref_w, weight_initial_n, fuel_mass_kg,
                   weight_ref_n, g0):
    """Average cruise power P_avg = P_ref * (W_avg / W_ref)^1.5 in W.

    The average weight W_avg = (W0 + W1) / 2 carries the induced-
    dominated W^1.5 power scaling between the takeoff and burnout weights.
    """
    if power_at_ref_w <= 0:
        raise ValueError("reference power must be positive")
    if weight_ref_n <= 0:
        raise ValueError("reference weight must be positive")
    w0 = weight_initial_n
    w1 = w0 - g0 * fuel_mass_kg
    if w1 <= 0:
        raise ValueError("fuel mass must leave a positive final weight")
    w_avg = (w0 + w1) / 2.0
    return power_at_ref_w * (w_avg / weight_ref_n) ** 1.5


def cruise_range(v_ms, weight_initial_n, fuel_mass_kg, power_at_ref_w,
                 weight_ref_n, c_specific=C_SPEC_DEFAULT, g0=G0):
    """Cruise range R = V * (W0 - W1) / (g0 * c * P_avg) in m at speed V.

    The average-weight power scaling method carries the same fuel-
    closure structure as the fixed-wing cruise form but with the
    average-weight-scaled power required for the rotorcraft in place of
    a fixed lift-to-drag factor.
    """
    if v_ms <= 0:
        raise ValueError("speed must be positive")
    if weight_initial_n <= 0:
        raise ValueError("initial weight must be positive")
    if fuel_mass_kg < 0:
        raise ValueError("fuel mass must not be negative")
    if c_specific <= 0:
        raise ValueError("specific fuel consumption must be positive")
    p_avg = _average_power(power_at_ref_w, weight_initial_n, fuel_mass_kg,
                           weight_ref_n, g0)
    w0 = weight_initial_n
    w1 = w0 - g0 * fuel_mass_kg
    return v_ms * (w0 - w1) / (g0 * c_specific * p_avg)


def cruise_endurance(v_ms, weight_initial_n, fuel_mass_kg, power_at_ref_w,
                     weight_ref_n, c_specific=C_SPEC_DEFAULT, g0=G0):
    """Cruise endurance E = (W0 - W1) / (g0 * c * P_avg) in s.

    Same average-weight power scaling convention as cruise_range; the
    speed argument is validated but does not enter the fuel closure.
    """
    if v_ms <= 0:
        raise ValueError("speed must be positive")
    if weight_initial_n <= 0:
        raise ValueError("initial weight must be positive")
    if fuel_mass_kg < 0:
        raise ValueError("fuel mass must not be negative")
    if c_specific <= 0:
        raise ValueError("specific fuel consumption must be positive")
    p_avg = _average_power(power_at_ref_w, weight_initial_n, fuel_mass_kg,
                           weight_ref_n, g0)
    w0 = weight_initial_n
    w1 = w0 - g0 * fuel_mass_kg
    return (w0 - w1) / (g0 * c_specific * p_avg)
