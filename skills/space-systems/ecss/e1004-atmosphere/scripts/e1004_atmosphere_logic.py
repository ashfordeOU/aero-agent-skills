#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 7.2 neutral atmosphere model selection and
density scaling logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
neutral (non-ionized) upper-atmosphere gas drives aerodynamic drag on a
spacecraft, which drives orbital decay rate, drag-makeup propellant
budget, and low-altitude attitude disturbance torques. Density at a
given altitude is strongly modulated by solar activity (F10.7 index)
and, transiently, by geomagnetic activity (Ap index). NRLMSISE-00-class
models are the general-purpose Earth density reference; JB-2006-class
models are an alternative for precision analyses; HWM-type models add
thermospheric winds. This module implements the model-selection,
altitude-applicability, solar-activity classification, density-scaling,
and compliance logic; it does not implement charged-particle/plasma
environments (see the sibling e1004-plasma leaf) or planetary
reference atmospheres (see the sibling e1004-ref-atmosphere leaf).
"""

MODEL_BY_PRECISION = {
    "standard": "NRLMSISE-00-class empirical whole-atmosphere density model",
    "precision": "JB-2006-class (Jacchia-Bowman) density model",
}

VALID_ALTITUDE_MIN_KM = 90.0
VALID_ALTITUDE_MAX_KM = 1000.0

SOLAR_FLUX_LOW_SFU = 70.0
SOLAR_FLUX_HIGH_SFU = 200.0

WIND_MODEL_NAME = "HWM-type horizontal wind model"


def select_atmosphere_model(precision="standard"):
    """Reference Earth neutral-atmosphere density model name for one
    precision need ("standard" or "precision"). Raises ValueError for
    an unknown precision need."""
    if precision not in MODEL_BY_PRECISION:
        raise ValueError("unknown precision need: %r" % (precision,))
    return MODEL_BY_PRECISION[precision]


def requires_planetary_model(target_body):
    """True when target_body is not Earth, meaning a planet-specific
    reference atmosphere is required instead of an Earth neutral-
    atmosphere model. Comparison is case-insensitive."""
    return target_body.strip().lower() != "earth"


def altitude_in_valid_range(altitude_km):
    """True when altitude_km falls within the Earth neutral-atmosphere
    model's valid altitude range. Raises ValueError when altitude_km
    is negative."""
    if altitude_km < 0:
        raise ValueError("altitude must not be negative")
    return VALID_ALTITUDE_MIN_KM <= altitude_km <= VALID_ALTITUDE_MAX_KM


def classify_solar_activity(f107):
    """Classify an F10.7 solar flux index (solar flux units) into
    "low" (at or below the solar-minimum reference level), "high" (at
    or above the solar-maximum reference level), or "moderate". Raises
    ValueError when f107 is not positive."""
    if f107 <= 0:
        raise ValueError("F10.7 index must be positive")
    if f107 <= SOLAR_FLUX_LOW_SFU:
        return "low"
    if f107 >= SOLAR_FLUX_HIGH_SFU:
        return "high"
    return "moderate"


def select_wind_model(needs_wind):
    """WIND_MODEL_NAME when needs_wind is true, otherwise None: wind
    is a secondary correction only required for cases that need
    thermospheric wind data."""
    return WIND_MODEL_NAME if needs_wind else None


def density_scale_factor(f107, ap_index):
    """Scale factor applied to a reference density to account for
    solar activity (F10.7) and geomagnetic activity (Ap): increases
    with both, normalized so the solar-minimum reference F10.7 with
    quiet geomagnetic conditions (ap_index 0) gives a factor of 1.0.
    Raises ValueError when f107 is not positive or ap_index is
    negative."""
    if f107 <= 0:
        raise ValueError("F10.7 index must be positive")
    if ap_index < 0:
        raise ValueError("Ap index must not be negative")
    return (f107 / SOLAR_FLUX_LOW_SFU) * (1.0 + ap_index / 100.0)


def apply_density_scaling(reference_density, f107, ap_index):
    """Density at f107/ap_index obtained by scaling reference_density
    by density_scale_factor(). Raises ValueError when reference_density
    is negative."""
    if reference_density < 0:
        raise ValueError("reference density must not be negative")
    return reference_density * density_scale_factor(f107, ap_index)


def assess_atmosphere_case(case):
    """Full neutral-atmosphere model-selection and compliance
    assessment for one case dict. Required keys: id, target_body,
    altitude_km, f107, ap_index, reference_density. Optional keys:
    precision (default "standard"), needs_wind (default False).
    Returns a new dict; does not mutate the input. Raises ValueError
    when 'id' is missing or precision/f107/altitude are invalid."""
    if "id" not in case:
        raise ValueError("atmosphere case is missing an id")
    target_body = case["target_body"]
    needs_planetary_model = requires_planetary_model(target_body)
    altitude_km = case["altitude_km"]
    in_range = altitude_in_valid_range(altitude_km)
    precision = case.get("precision", "standard")
    model = None if needs_planetary_model else select_atmosphere_model(precision)
    f107 = case["f107"]
    ap_index = case["ap_index"]
    solar_activity = classify_solar_activity(f107)
    needs_wind = case.get("needs_wind", False)
    wind_model = select_wind_model(needs_wind)
    scaled_density = None
    if not needs_planetary_model:
        scaled_density = apply_density_scaling(
            case["reference_density"], f107, ap_index
        )
    compliant = (not needs_planetary_model) and in_range
    return {
        "id": case["id"],
        "target_body": target_body,
        "requires_planetary_model": needs_planetary_model,
        "altitude_km": altitude_km,
        "altitude_in_range": in_range,
        "model": model,
        "solar_activity": solar_activity,
        "wind_model": wind_model,
        "scaled_density": scaled_density,
        "compliant": compliant,
    }


def build_atmosphere_assessment(cases):
    """Assessment record: one assess_atmosphere_case() result per
    case, in input order. Raises ValueError on a duplicate case id."""
    record = []
    seen_ids = set()
    for case in cases:
        assessment = assess_atmosphere_case(case)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate atmosphere case id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def noncompliant_items(record):
    """Case ids in the record that are not compliant, in record
    order -- these cannot support the atmosphere characterization
    as-is."""
    return [entry["id"] for entry in record if not entry["compliant"]]


def all_compliant(record):
    """True when every entry in the assessment record is compliant."""
    return len(noncompliant_items(record)) == 0
