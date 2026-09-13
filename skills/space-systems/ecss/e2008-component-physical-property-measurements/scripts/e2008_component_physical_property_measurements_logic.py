#!/usr/bin/env python3
"""Thermal and mechanical property values to be determined for an array.

Anchor: ECSS-E-ST-20-08C clause 4.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar array is a stack of dissimilar materials bonded together and
flown through thousands of deep thermal cycles. Nothing about how it
behaves can be predicted from a part number, so the clause asks for the
physical property values of the materials and components to be
determined -- measured or otherwise established -- before the array is
analysed.

Properties grouped as thermal

    solar-absorptance                 fraction of the solar spectrum absorbed
    infrared-emittance                fraction radiated at array temperature
    thermal-conductivity              W/(m K)
    specific-heat                     J/(kg K)
    coefficient-of-thermal-expansion  1/K, negative for some laminates

Properties grouped as mechanical

    density                           kg/m3
    youngs-modulus                    Pa
    poissons-ratio                    dimensionless
    tensile-strength                  Pa

Which of these a given item needs depends on what the item does: an
optical coating is asked for its radiative pair and its expansion, a
structural facesheet for its full mechanical set. A value is only of
use over the temperature band it was determined across, so the band is
carried with it and compared against the mission band.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

THERMAL_PROPERTIES = (
    "solar-absorptance",
    "infrared-emittance",
    "thermal-conductivity",
    "specific-heat",
    "coefficient-of-thermal-expansion",
)

MECHANICAL_PROPERTIES = (
    "density",
    "youngs-modulus",
    "poissons-ratio",
    "tensile-strength",
)

ALL_PROPERTIES = THERMAL_PROPERTIES + MECHANICAL_PROPERTIES

PROPERTY_BOUNDS = {
    "solar-absorptance": (0.0, 1.0, "-"),
    "infrared-emittance": (0.0, 1.0, "-"),
    "thermal-conductivity": (1.0e-3, 3.0e3, "W/(m K)"),
    "specific-heat": (10.0, 5.0e3, "J/(kg K)"),
    "coefficient-of-thermal-expansion": (-5.0e-6, 3.0e-4, "1/K"),
    "density": (1.0, 2.5e4, "kg/m3"),
    "youngs-modulus": (1.0e3, 1.2e12, "Pa"),
    "poissons-ratio": (-1.0, 0.5, "-"),
    "tensile-strength": (1.0e3, 1.0e10, "Pa"),
}

REQUIRED_PROPERTIES_BY_CATEGORY = {
    "solar-cell": (
        "solar-absorptance",
        "infrared-emittance",
        "coefficient-of-thermal-expansion",
        "density",
        "youngs-modulus",
    ),
    "coverglass": (
        "solar-absorptance",
        "infrared-emittance",
        "coefficient-of-thermal-expansion",
        "density",
        "youngs-modulus",
        "poissons-ratio",
    ),
    "adhesive": (
        "thermal-conductivity",
        "specific-heat",
        "coefficient-of-thermal-expansion",
        "density",
        "youngs-modulus",
        "poissons-ratio",
        "tensile-strength",
    ),
    "substrate-facesheet": (
        "thermal-conductivity",
        "specific-heat",
        "coefficient-of-thermal-expansion",
        "density",
        "youngs-modulus",
        "poissons-ratio",
        "tensile-strength",
    ),
    "interconnect": (
        "thermal-conductivity",
        "coefficient-of-thermal-expansion",
        "density",
        "youngs-modulus",
        "tensile-strength",
    ),
    "optical-coating": (
        "solar-absorptance",
        "infrared-emittance",
        "coefficient-of-thermal-expansion",
    ),
}

COMPONENT_CATEGORIES = tuple(sorted(REQUIRED_PROPERTIES_BY_CATEGORY))

DETERMINED_VERDICT = "properties-determined"
OUTSTANDING_VERDICT = "properties-outstanding"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A determined band whose edge was written down in one unit and
    compared in another can land a few units in the last place inside
    or outside the mission band. The band is never widened; only the
    comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def property_group(property_name):
    """Whether a property is grouped as thermal or as mechanical."""
    if property_name in THERMAL_PROPERTIES:
        return "thermal"
    if property_name in MECHANICAL_PROPERTIES:
        return "mechanical"
    raise ValueError("unknown property %r" % (property_name,))


def property_unit(property_name):
    """Unit the property value is expected in."""
    _require_choice("property", property_name, ALL_PROPERTIES)
    return PROPERTY_BOUNDS[property_name][2]


def required_properties(category):
    """Property values that have to be determined for this item."""
    _require_choice("category", category, COMPONENT_CATEGORIES)
    return tuple(sorted(REQUIRED_PROPERTIES_BY_CATEGORY[category]))


def validate_property_value(property_name, value):
    """Check one determined value is a number inside its physical band."""
    _require_choice("property", property_name, ALL_PROPERTIES)
    if not _is_finite_number(value):
        raise ValueError(
            "%s must be a finite number, got %r" % (property_name, value)
        )
    low, high, unit = PROPERTY_BOUNDS[property_name]
    number = float(value)
    if number < low or number > high:
        raise ValueError(
            "%s value %g %s is outside the admissible band %g to %g"
            % (property_name, number, unit, low, high)
        )
    return number


def validate_dataset(category, declared):
    """Normalise a declared property set, rejecting anything unusable."""
    _require_choice("category", category, COMPONENT_CATEGORIES)
    if not isinstance(declared, dict):
        raise ValueError("declared properties must be a mapping, got %r" % (declared,))
    dataset = {}
    for name in sorted(declared):
        dataset[name] = validate_property_value(name, declared[name])
    return dataset


def missing_properties(category, declared):
    """Required property values this item has not had determined."""
    dataset = validate_dataset(category, declared)
    return tuple(
        name for name in required_properties(category) if name not in dataset
    )


def surplus_properties(category, declared):
    """Determined values this item does not require, kept for record."""
    dataset = validate_dataset(category, declared)
    required = set(required_properties(category))
    return tuple(sorted(name for name in dataset if name not in required))


def determination_completeness(category, declared):
    """Fraction of the required property values already determined."""
    required = required_properties(category)
    return (len(required) - len(missing_properties(category, declared))) / len(required)


def validate_temperature_band(name, band):
    """Normalise a kelvin band, rejecting an inverted or unphysical one."""
    if not isinstance(band, dict):
        raise ValueError("%s must be a mapping with minimum_k and maximum_k" % name)
    low = _require_positive("%s minimum_k" % name, band.get("minimum_k"))
    high = _require_positive("%s maximum_k" % name, band.get("maximum_k"))
    if not high > low:
        raise ValueError(
            "%s maximum_k %g must be above minimum_k %g" % (name, high, low)
        )
    return (low, high)


def temperature_coverage(determined_band, mission_band):
    """How far the determined band falls short of the mission band."""
    low_d, high_d = validate_temperature_band("determined band", determined_band)
    low_m, high_m = validate_temperature_band("mission band", mission_band)
    cold_shortfall = max(0.0, low_d - low_m)
    hot_shortfall = max(0.0, high_m - high_d)
    covered = _at_most(low_d, low_m) and _at_least(high_d, high_m)
    return {
        "covered": covered,
        "cold_shortfall_k": cold_shortfall,
        "hot_shortfall_k": hot_shortfall,
        "determined_span_k": high_d - low_d,
        "mission_span_k": high_m - low_m,
    }


def absorptance_to_emittance_ratio(solar_absorptance, infrared_emittance):
    """Radiative ratio that drives the array operating temperature."""
    alpha = validate_property_value("solar-absorptance", solar_absorptance)
    epsilon = validate_property_value("infrared-emittance", infrared_emittance)
    if epsilon <= 0.0:
        raise ValueError("infrared-emittance must be greater than zero to form a ratio")
    return alpha / epsilon


def thermal_diffusivity(thermal_conductivity, density, specific_heat):
    """Speed at which a temperature front crosses the material, m2/s."""
    k = validate_property_value("thermal-conductivity", thermal_conductivity)
    rho = validate_property_value("density", density)
    cp = validate_property_value("specific-heat", specific_heat)
    return k / (rho * cp)


def specific_stiffness(youngs_modulus, density):
    """Modulus carried per unit mass, the array structural figure of merit."""
    modulus = validate_property_value("youngs-modulus", youngs_modulus)
    rho = validate_property_value("density", density)
    return modulus / rho


def bonded_pair_thermal_stress(
    cte_a, cte_b, temperature_change_k, youngs_modulus, tensile_strength=None
):
    """Strain and stress a bonded pair sees over a temperature change."""
    alpha_a = validate_property_value("coefficient-of-thermal-expansion", cte_a)
    alpha_b = validate_property_value("coefficient-of-thermal-expansion", cte_b)
    if not _is_finite_number(temperature_change_k):
        raise ValueError(
            "temperature_change_k must be a finite number, got %r"
            % (temperature_change_k,)
        )
    modulus = validate_property_value("youngs-modulus", youngs_modulus)
    strain = (alpha_a - alpha_b) * float(temperature_change_k)
    stress = abs(strain) * modulus
    result = {
        "mismatch_strain": strain,
        "stress_pa": stress,
        "margin_of_safety": None,
        "adequate": None,
    }
    if tensile_strength is None:
        return result
    allowable = validate_property_value("tensile-strength", tensile_strength)
    if stress == 0.0:
        result["margin_of_safety"] = float("inf")
        result["adequate"] = True
        return result
    result["margin_of_safety"] = allowable / stress - 1.0
    result["adequate"] = _at_least(result["margin_of_safety"], 0.0)
    return result


def assess_property_dataset(case):
    """Full clause 4.2 check of the determined property values."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    category = _require_choice(
        "component_category", case.get("component_category"), COMPONENT_CATEGORIES
    )
    dataset = validate_dataset(category, case.get("declared_properties"))
    missing = missing_properties(category, dataset)
    surplus = surplus_properties(category, dataset)
    completeness = determination_completeness(category, dataset)
    coverage = temperature_coverage(
        case.get("determined_temperature_band_k"),
        case.get("mission_temperature_band_k"),
    )
    findings = []
    for name in missing:
        findings.append(
            "%s property %s has not been determined" % (property_group(name), name)
        )
    if not coverage["covered"]:
        if coverage["cold_shortfall_k"] > 0.0:
            findings.append(
                "determined band stops %.1f K short of the cold mission limit"
                % coverage["cold_shortfall_k"]
            )
        if coverage["hot_shortfall_k"] > 0.0:
            findings.append(
                "determined band stops %.1f K short of the hot mission limit"
                % coverage["hot_shortfall_k"]
            )
    for name in surplus:
        findings.append(
            "%s is determined but not required for a %s; kept for record"
            % (name, category)
        )
    determined = not missing and coverage["covered"]
    result = {
        "component_category": category,
        "required_properties": required_properties(category),
        "determined_properties": tuple(sorted(dataset)),
        "missing_properties": missing,
        "surplus_properties": surplus,
        "determination_completeness": completeness,
        "temperature_coverage": coverage,
        "verdict": DETERMINED_VERDICT if determined else OUTSTANDING_VERDICT,
        "complete": determined,
        "findings": findings,
    }
    if "solar-absorptance" in dataset and "infrared-emittance" in dataset:
        result["absorptance_to_emittance_ratio"] = absorptance_to_emittance_ratio(
            dataset["solar-absorptance"], dataset["infrared-emittance"]
        )
    else:
        result["absorptance_to_emittance_ratio"] = None
    if "youngs-modulus" in dataset and "density" in dataset:
        result["specific_stiffness_m2_s2"] = specific_stiffness(
            dataset["youngs-modulus"], dataset["density"]
        )
    else:
        result["specific_stiffness_m2_s2"] = None
    return result
