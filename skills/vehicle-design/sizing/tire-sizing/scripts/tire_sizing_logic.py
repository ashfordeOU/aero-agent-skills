#!/usr/bin/env python3
"""Tire sizing logic for landing gear (class-I conceptual design).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): landing gear tire selection at the conceptual level starts
from the static load per tire, which is the gear load share of the
takeoff weight divided by the number of tires on that gear. The tire
diameter and width are estimated with power law fits of the form
dimension = a * load**b, where the coefficients and exponents are
representative class-I fit values (diameter exponent around 0.32,
width exponent around 0.36); the final tire comes from a catalog
check, not from the fit alone. The footprint contact area is the load
per tire divided by the inflation pressure, and the rolling radius is
half the tire diameter. The required number of tires is the gear load
total divided by the maximum load capacity per tire, rounded up.

Units: mass in kg, load in pounds for the fit inputs (the fits are
pound-inch curve fits), pressure in psi, dimensions in inches (25.4 mm
per inch). Invalid inputs raise ValueError throughout.
"""

import math

LB_PER_KG = 2.2046226218487757
MM_PER_IN = 25.4


def kg_to_lb(mass_kg):
    """Convert a mass in kg to pounds. Raises ValueError if not positive."""
    if mass_kg <= 0:
        raise ValueError("mass must be positive, got %r" % (mass_kg,))
    return mass_kg * LB_PER_KG


def static_load_per_tire(mtow_kg, gear_fraction, n_tires):
    """Static load per tire in kg on one gear.

    Returns mtow_kg * gear_fraction / n_tires. gear_fraction is the
    share of the takeoff weight carried by that gear (0 to 1), and
    n_tires is the number of tires on that gear. Raises ValueError if
    the takeoff weight is not positive, the fraction is outside (0, 1],
    or the tire count is not a positive integer.
    """
    if mtow_kg <= 0:
        raise ValueError("takeoff weight must be positive, got %r" % (mtow_kg,))
    if not (0.0 < gear_fraction <= 1.0):
        raise ValueError(
            "gear fraction must be in (0, 1], got %r" % (gear_fraction,)
        )
    if not isinstance(n_tires, int) or n_tires < 1:
        raise ValueError(
            "tire count must be a positive integer, got %r" % (n_tires,)
        )
    return mtow_kg * gear_fraction / n_tires


def tire_diameter_inches(load_lb, coeff=1.63, exponent=0.315):
    """Estimated tire diameter in inches from the load per tire in pounds.

    Representative class-I power law fit: diameter = coeff * load**exponent.
    Raises ValueError if the load or the coefficient is not positive.
    """
    if load_lb <= 0:
        raise ValueError("load per tire must be positive, got %r" % (load_lb,))
    if coeff <= 0:
        raise ValueError("fit coefficient must be positive, got %r" % (coeff,))
    return coeff * load_lb ** exponent


def tire_width_inches(load_lb, coeff=0.40, exponent=0.36):
    """Estimated tire width in inches from the load per tire in pounds.

    Representative class-I power law fit: width = coeff * load**exponent.
    Raises ValueError if the load or the coefficient is not positive.
    """
    if load_lb <= 0:
        raise ValueError("load per tire must be positive, got %r" % (load_lb,))
    if coeff <= 0:
        raise ValueError("fit coefficient must be positive, got %r" % (coeff,))
    return coeff * load_lb ** exponent


def footprint_area_sqin(load_lb, pressure_psi):
    """Tire footprint contact area in square inches.

    Returns load_lb / pressure_psi, the contact area that carries the
    static load at the inflation pressure. Raises ValueError if either
    input is not positive.
    """
    if load_lb <= 0:
        raise ValueError("load per tire must be positive, got %r" % (load_lb,))
    if pressure_psi <= 0:
        raise ValueError(
            "inflation pressure must be positive, got %r" % (pressure_psi,)
        )
    return load_lb / pressure_psi


def rolling_radius_inches(diameter_in):
    """Rolling radius in inches, half the tire diameter.

    Raises ValueError if the diameter is not positive.
    """
    if diameter_in <= 0:
        raise ValueError(
            "tire diameter must be positive, got %r" % (diameter_in,)
        )
    return diameter_in / 2.0


def required_number_of_tires(total_gear_load_lb, max_load_per_tire_lb):
    """Required number of tires on a gear, rounded up.

    Returns ceil(total_gear_load_lb / max_load_per_tire_lb). Raises
    ValueError if either input is not positive.
    """
    if total_gear_load_lb <= 0:
        raise ValueError(
            "gear load total must be positive, got %r" % (total_gear_load_lb,)
        )
    if max_load_per_tire_lb <= 0:
        raise ValueError(
            "max load per tire must be positive, got %r" % (max_load_per_tire_lb,)
        )
    return int(math.ceil(total_gear_load_lb / max_load_per_tire_lb))
