"""Class-II fuel system group weight regression (Torenbeek method, paraphrased).

Pure stdlib power-law and additive arithmetic. Inputs are SI (kg,
dimensionless counts); the regression runs in the published lb / US
gallon closed form and converts at the boundary with fixed constants.
"""

KG_TO_LB = 1.0 / 0.45359237
LB_TO_KG = 0.45359237

FUEL_SYSTEM_COUNT_K = 80.0
FUEL_SYSTEM_VOLUME_K = 15.0
FUEL_SYSTEM_E_NT = 0.5
FUEL_SYSTEM_E_V = 1.0 / 3.0
FUEL_SPECIFIC_WEIGHT = 6.55


def _require_positive_fuel_weight(value):
    """Raise ValueError unless value is a positive real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("total fuel weight must be a number, got %r" % (value,))
    if value <= 0:
        raise ValueError("total fuel weight must be positive, got %s" % (value,))


def _require_count(value, label):
    """Raise ValueError unless value is a whole number at least 1."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %s" % (label, value))
    if value != int(value):
        raise ValueError("%s must be a whole number, got %s" % (label, value))


def fuel_system_count_allowance_kg(n_tanks, n_engines):
    """Fixed count allowance term in kg, linear in the tank and engine count sum."""
    _require_count(n_tanks, "number of separate fuel tanks")
    _require_count(n_engines, "number of engines")
    w_a_lb = FUEL_SYSTEM_COUNT_K * (n_tanks + n_engines - 1)
    return w_a_lb * LB_TO_KG


def fuel_system_volume_term_kg(total_fuel_kg, n_tanks):
    """Volume-scaled tankage term in kg, sublinear in tank count and fuel quantity."""
    _require_positive_fuel_weight(total_fuel_kg)
    _require_count(n_tanks, "number of separate fuel tanks")
    total_fuel_lb = total_fuel_kg * KG_TO_LB
    fuel_gallons = total_fuel_lb / FUEL_SPECIFIC_WEIGHT
    w_v_lb = (
        FUEL_SYSTEM_VOLUME_K
        * n_tanks ** FUEL_SYSTEM_E_NT
        * fuel_gallons ** FUEL_SYSTEM_E_V
    )
    return w_v_lb * LB_TO_KG


def fuel_system_group_weight(total_fuel_kg, n_tanks, n_engines):
    """Fuel system group mass in kg, the sum of the count allowance and volume terms."""
    _require_positive_fuel_weight(total_fuel_kg)
    _require_count(n_tanks, "number of separate fuel tanks")
    _require_count(n_engines, "number of engines")
    if n_tanks < n_engines:
        raise ValueError(
            "number of separate fuel tanks must be at least the number of "
            "engines, got tanks %s and engines %s" % (n_tanks, n_engines)
        )
    w_a = fuel_system_count_allowance_kg(n_tanks, n_engines)
    w_v = fuel_system_volume_term_kg(total_fuel_kg, n_tanks)
    return w_a + w_v


def fuel_system_group_fraction(fuel_system_group_kg, reference_weight_kg):
    """Fuel system group mass as a fraction of a reference weight (fuel weight or MTOW)."""
    _require_positive_fuel_weight(reference_weight_kg)
    if isinstance(fuel_system_group_kg, bool) or not isinstance(
        fuel_system_group_kg, (int, float)
    ):
        raise ValueError(
            "fuel system group mass must be a number, got %r" % (fuel_system_group_kg,)
        )
    if fuel_system_group_kg < 0:
        raise ValueError(
            "fuel system group mass must be non-negative, got %s"
            % (fuel_system_group_kg,)
        )
    return fuel_system_group_kg / reference_weight_kg
