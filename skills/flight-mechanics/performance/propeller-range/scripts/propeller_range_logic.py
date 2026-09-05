"""Propeller and turboprop cruise range logic (pure stdlib, no RNG).

Implements the propeller branch of the Breguet range family: the cruise
range of a propeller or turboprop aircraft from the power specific fuel
consumption (PSFC) and the propeller efficiency,

    R = (eta_p / (c_p * g0)) * (L/D) * ln(m0 / m1),

with eta_p the propeller efficiency, c_p the PSFC in kg/(W s), g0 the
standard gravity, L/D the lift to drag ratio, m0 the initial mass and m1
the final mass. A pounds per horsepower hour PSFC is converted into SI
kilograms per watt second first, and a final mass can be derived from a
fuel fraction. The jet/TSFC side of the family, which never takes a
propeller efficiency, lives in the breguet-range leaf.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2

# One pound is 0.45359237 kg, one horsepower is 745.6999 W and one hour
# is 3600 s, so 1 lb/(hp h) = 0.45359237 / (745.6999 * 3600) kg/(W s).
LB_PER_HP_H_TO_KG_PER_W_S = 0.45359237 / (745.6999 * 3600.0)


def psfc_lb_per_hp_h_to_kg_per_w_s(value):
    """Convert a PSFC in lb/(hp h) into SI kg/(W s).

    Args:
        value: PSFC in pounds per horsepower hour, non-negative float.

    Returns:
        The same PSFC expressed in kg per watt second.

    Raises:
        ValueError: if value is negative (non-physical).
    """
    if value < 0.0:
        raise ValueError("psfc must be non-negative")
    return value * LB_PER_HP_H_TO_KG_PER_W_S


def final_mass_from_fuel_fraction(initial_mass, fuel_fraction):
    """Derive the final cruise mass from a fuel fraction, m1 = m0 * (1 - f).

    Args:
        initial_mass: takeoff or start-of-cruise mass m0 in kg.
        fuel_fraction: fuel burned fraction f of the initial mass.

    Returns:
        The final cruise mass m1 in kg.

    Raises:
        ValueError: if initial_mass is not positive or fuel_fraction is
        outside [0, 1) (a fraction of 1 or above leaves no vehicle mass).
    """
    if initial_mass <= 0.0:
        raise ValueError("initial_mass must be positive")
    if not (0.0 <= fuel_fraction < 1.0):
        raise ValueError("fuel_fraction must be in [0, 1)")
    return initial_mass * (1.0 - fuel_fraction)


def propeller_range(propeller_efficiency, psfc_kg_per_w_s, ld,
                    initial_mass, final_mass):
    """Compute the propeller Breguet cruise range R in meters.

    R = (eta_p / (c_p * g0)) * (L/D) * ln(m0 / m1).

    Args:
        propeller_efficiency: eta_p, the propeller efficiency in (0, 1].
        psfc_kg_per_w_s: c_p, power specific fuel consumption in kg/(W s).
        ld: L/D, the cruise lift to drag ratio.
        initial_mass: m0 in kg.
        final_mass: m1 in kg, below the initial mass.

    Returns:
        Cruise range in meters.

    Raises:
        ValueError: if propeller_efficiency is not in (0, 1], psfc or ld
        is not positive, or the masses are not positive with
        final_mass < initial_mass (the log ratio would otherwise be
        zero, negative or undefined).
    """
    if not (0.0 < propeller_efficiency <= 1.0):
        raise ValueError("propeller_efficiency must be in (0, 1]")
    if psfc_kg_per_w_s <= 0.0:
        raise ValueError("psfc_kg_per_w_s must be positive")
    if ld <= 0.0:
        raise ValueError("ld must be positive")
    if initial_mass <= 0.0:
        raise ValueError("initial_mass must be positive")
    if final_mass <= 0.0:
        raise ValueError("final_mass must be positive")
    if final_mass >= initial_mass:
        raise ValueError("final_mass must be below initial_mass")
    return ((propeller_efficiency / (psfc_kg_per_w_s * G0)) * ld
            * math.log(initial_mass / final_mass))


def propeller_range_km(propeller_efficiency, psfc_kg_per_w_s, ld,
                       initial_mass, final_mass):
    """Convenience form of propeller_range returning kilometers."""
    return propeller_range(propeller_efficiency, psfc_kg_per_w_s, ld,
                           initial_mass, final_mass) / 1000.0


def range_report(propeller_efficiency, psfc_kg_per_w_s, ld,
                 initial_mass, final_mass):
    """Package the propeller range as a report dict.

    Returns:
        Dict with exactly the keys range_m (meters) and range_km
        (kilometers), both derived from the same propeller_range call so
        the two figures always agree.
    """
    range_m = propeller_range(propeller_efficiency, psfc_kg_per_w_s, ld,
                              initial_mass, final_mass)
    return {"range_m": range_m, "range_km": range_m / 1000.0}
