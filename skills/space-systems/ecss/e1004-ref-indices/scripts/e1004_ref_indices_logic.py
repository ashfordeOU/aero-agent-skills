#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex F (info) solar-activity and Earth albedo/IR
reference data (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
space environment specification's informative annex tabulates reference
values for the three solar-cycle activity levels (minimum, mean,
maximum) -- the F10.7 solar radio flux index and sunspot number for
each level -- and pairs each level with an Earth albedo and Earth
infrared (IR) emission reference value for use in thermal and power
environment analysis. This module implements the reference-value
tables, the F10.7-to-activity-level classification rule, input-range
validation for each dataset, solar-cycle-phase interpolation between
the tabulated levels, the hot/cold worst-case thermal combination
rule, and the source-citation registry for each parameter; it does not
define the underlying physical models that produced the tabulated
values.
"""

SOLAR_ACTIVITY_LEVELS = ("minimum", "mean", "maximum")

# F10.7 solar radio flux (solar flux units, sfu) and sunspot number
# reference values for each solar-cycle activity level.
SOLAR_INDEX_REFERENCE = {
    "minimum": {"f107_solar_flux_sfu": 70.0, "sunspot_number": 0.0},
    "mean": {"f107_solar_flux_sfu": 140.0, "sunspot_number": 90.0},
    "maximum": {"f107_solar_flux_sfu": 230.0, "sunspot_number": 180.0},
}

# Earth albedo (dimensionless, 0-1) and Earth IR emission (W/m^2)
# reference values paired with each solar-cycle activity level.
ALBEDO_IR_REFERENCE = {
    "minimum": {"earth_albedo": 0.25, "earth_ir_flux_w_m2": 260.0},
    "mean": {"earth_albedo": 0.30, "earth_ir_flux_w_m2": 237.0},
    "maximum": {"earth_albedo": 0.35, "earth_ir_flux_w_m2": 216.0},
}

# Documented physical validity range (inclusive) for each dataset.
DATASET_VALID_RANGES = {
    "f107_solar_flux_sfu": (50.0, 300.0),
    "sunspot_number": (0.0, 400.0),
    "earth_albedo": (0.0, 1.0),
    "earth_ir_flux_w_m2": (150.0, 300.0),
}

# Canonical reference-source citation for each parameter.
SOURCE_REGISTRY = {
    "f107_solar_flux_sfu": "ECSS-E-ST-10-04C Annex F solar activity index reference data",
    "sunspot_number": "ECSS-E-ST-10-04C Annex F solar activity index reference data",
    "earth_albedo": "ECSS-E-ST-10-04C Annex F Earth albedo/IR reference data",
    "earth_ir_flux_w_m2": "ECSS-E-ST-10-04C Annex F Earth albedo/IR reference data",
}

# F10.7 classification boundaries: value <= _F107_MIN_MAX is "minimum",
# _F107_MIN_MAX < value <= _F107_MEAN_MAX is "mean", above is "maximum".
_F107_MIN_MAX = 100.0
_F107_MEAN_MAX = 180.0


def classify_f107_activity_level(f107_solar_flux_sfu):
    """Solar-cycle activity level ("minimum"/"mean"/"maximum") for a
    measured F10.7 value. Raises ValueError if the value is outside
    the documented physical range for f107_solar_flux_sfu."""
    violations = validate_index_value("f107_solar_flux_sfu", f107_solar_flux_sfu)
    if violations:
        raise ValueError(
            "F10.7 value %r outside documented physical range %r"
            % (f107_solar_flux_sfu, DATASET_VALID_RANGES["f107_solar_flux_sfu"])
        )
    if f107_solar_flux_sfu <= _F107_MIN_MAX:
        return "minimum"
    if f107_solar_flux_sfu <= _F107_MEAN_MAX:
        return "mean"
    return "maximum"


def get_solar_index(activity_level):
    """Reference dict {"f107_solar_flux_sfu", "sunspot_number"} for a
    solar-cycle activity level. Raises ValueError for an unrecognized
    activity level."""
    if activity_level not in SOLAR_INDEX_REFERENCE:
        raise ValueError(
            "unrecognized solar-cycle activity level %r under Annex F "
            "(expected one of %r)" % (activity_level, SOLAR_ACTIVITY_LEVELS)
        )
    return dict(SOLAR_INDEX_REFERENCE[activity_level])


def get_albedo_ir_reference(activity_level):
    """Reference dict {"earth_albedo", "earth_ir_flux_w_m2"} for a
    solar-cycle activity level. Raises ValueError for an unrecognized
    activity level."""
    if activity_level not in ALBEDO_IR_REFERENCE:
        raise ValueError(
            "unrecognized solar-cycle activity level %r under Annex F "
            "(expected one of %r)" % (activity_level, SOLAR_ACTIVITY_LEVELS)
        )
    return dict(ALBEDO_IR_REFERENCE[activity_level])


def validate_index_value(dataset_id, value):
    """Violation list (empty if within range) for a value against the
    documented physical range of dataset_id. Raises ValueError for an
    unrecognized dataset_id."""
    if dataset_id not in DATASET_VALID_RANGES:
        raise ValueError("unrecognized reference dataset %r" % (dataset_id,))
    low, high = DATASET_VALID_RANGES[dataset_id]
    if value < low or value > high:
        return [
            {
                "issue": "value_out_of_documented_range",
                "dataset": dataset_id,
                "value": value,
                "valid_range": [low, high],
            }
        ]
    return []


def source_reference_for_parameter(parameter):
    """Canonical Annex F source citation string for a reference
    parameter. Raises ValueError if no source is registered for it."""
    if parameter not in SOURCE_REGISTRY:
        raise ValueError(
            "no Annex F reference source recorded for parameter %r" % (parameter,)
        )
    return SOURCE_REGISTRY[parameter]


def interpolate_solar_cycle_index(dataset_id, cycle_phase_fraction):
    """Piecewise-linear interpolation of dataset_id across the solar
    cycle: phase 0.0 -> minimum, 0.5 -> mean, 1.0 -> maximum. dataset_id
    must be a key of SOLAR_INDEX_REFERENCE's per-level dicts or
    ALBEDO_IR_REFERENCE's. Raises ValueError for cycle_phase_fraction
    outside [0.0, 1.0] or an unrecognized dataset_id."""
    if cycle_phase_fraction < 0.0 or cycle_phase_fraction > 1.0:
        raise ValueError(
            "cycle_phase_fraction must be within [0.0, 1.0], got %r"
            % (cycle_phase_fraction,)
        )
    if dataset_id in SOLAR_INDEX_REFERENCE["minimum"]:
        table = SOLAR_INDEX_REFERENCE
    elif dataset_id in ALBEDO_IR_REFERENCE["minimum"]:
        table = ALBEDO_IR_REFERENCE
    else:
        raise ValueError("unrecognized reference dataset %r" % (dataset_id,))
    minimum = table["minimum"][dataset_id]
    mean = table["mean"][dataset_id]
    maximum = table["maximum"][dataset_id]
    if cycle_phase_fraction <= 0.5:
        local_fraction = cycle_phase_fraction / 0.5
        return minimum + (mean - minimum) * local_fraction
    local_fraction = (cycle_phase_fraction - 0.5) / 0.5
    return mean + (maximum - mean) * local_fraction


def thermal_case_reference(case):
    """Combined solar-index and albedo/IR reference dict for a worst
    case thermal analysis combination: "hot" pairs the maximum
    solar-cycle activity level for every parameter (maximizes heat
    input), "cold" pairs the minimum level for every parameter
    (minimizes heat input). Raises ValueError for any other case."""
    if case == "hot":
        activity_level = "maximum"
    elif case == "cold":
        activity_level = "minimum"
    else:
        raise ValueError("unrecognized thermal case %r (expected 'hot' or 'cold')" % (case,))
    combined = get_solar_index(activity_level)
    combined.update(get_albedo_ir_reference(activity_level))
    return combined


def reference_data_review(request):
    """Full Annex F reference-data check for one lookup request.

    request: {"dataset_id": str, "value": float}. Returns a dict with
    "activity_level" (the classification of the value, only computed
    for "f107_solar_flux_sfu"; None otherwise), "source" (the
    registered citation for dataset_id), and "violations" (list, empty
    if the value is within the documented range). Raises ValueError for
    an unrecognized dataset_id."""
    dataset_id = request["dataset_id"]
    value = request["value"]
    source = source_reference_for_parameter(dataset_id)
    violations = validate_index_value(dataset_id, value)
    activity_level = None
    if dataset_id == "f107_solar_flux_sfu" and not violations:
        activity_level = classify_f107_activity_level(value)
    return {
        "activity_level": activity_level,
        "source": source,
        "violations": violations,
    }


def is_reference_data_valid(review):
    """True when a reference_data_review result carries no
    violations."""
    return len(review["violations"]) == 0
