#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.2.1.6 physical and psycho-physiological environment
characterisation for human performance (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
ECSS human factors engineering standard requires that environments
relevant to human performance are characterised before operational tasks
are assigned; the characterisation covers physical parameters (thermal
comfort, acoustic, whole-body vibration, illuminance, atmospheric
composition) and psycho-physiological parameters (workload, stress/
fatigue, sleep adequacy); each parameter is checked against a
human-performance acceptability bound; a parameter not yet assessed is a
coverage gap, not a pass; and the characterisation is complete only when
all required parameters are assessed and within bounds. This module
implements parameter categorization, bounds checking, coverage assessment,
and environment review aggregation; it does not define mission-specific
performance bounds -- those are set by mission requirements and override
the HFE-literature-derived defaults supplied here.
"""

PHYSICAL_PARAMS = frozenset({
    "temperature_c",
    "relative_humidity_pct",
    "noise_level_dba",
    "rms_vibration_ms2",
    "illuminance_lux",
    "o2_partial_pressure_kpa",
    "co2_partial_pressure_kpa",
})

PSYCHOPHYSIOLOGICAL_PARAMS = frozenset({
    "workload_index",
    "stress_index",
    "sleep_hours_per_day",
})

ALL_REQUIRED_PARAMS = PHYSICAL_PARAMS | PSYCHOPHYSIOLOGICAL_PARAMS

# Default human-performance acceptability bounds: (lower_bound, upper_bound).
# A value within [lower, upper] is acceptable for sustained human performance.
# Source: HFE literature (common knowledge); ECSS-E-ST-10-11C §4.2.1.6
# mandates the characterisation but does not reproduce these numeric values.
DEFAULT_BOUNDS = {
    "temperature_c":            (18.0, 26.0),   # °C, sustained work comfort band
    "relative_humidity_pct":    (25.0, 70.0),   # % RH
    "noise_level_dba":          (0.0,  68.0),   # dB(A), sustained work limit
    "rms_vibration_ms2":        (0.0,  0.315),  # m/s², ISO 2631-1 8 h boundary
    "illuminance_lux":          (200.0, 2000.0),# lux, task-area range
    "o2_partial_pressure_kpa":  (18.0, 23.0),   # kPa, breathable range
    "co2_partial_pressure_kpa": (0.0,  0.5),    # kPa (~5 000 ppm ceiling)
    "workload_index":           (0.0,  7.0),    # 0–10 composite; concern above 7
    "stress_index":             (0.0,  7.0),    # 0–10 composite; concern above 7
    "sleep_hours_per_day":      (6.0,  10.0),   # h; below 6 h degrades performance
}


def categorize_parameter(param_name):
    """Return "physical" or "psychophysiological" for a known parameter.
    Raises ValueError for an unrecognized parameter name."""
    if param_name in PHYSICAL_PARAMS:
        return "physical"
    if param_name in PSYCHOPHYSIOLOGICAL_PARAMS:
        return "psychophysiological"
    raise ValueError(
        "unrecognized environment parameter %r; not in the "
        "E-ST-10-11C §4.2.1.6 parameter set" % (param_name,)
    )


def check_bounds(param_name, value, bounds=None):
    """Return a result dict for one parameter value against its bound.

    Returns {"param": param_name, "value": value, "lower": lower,
    "upper": upper, "in_bounds": bool}. Uses DEFAULT_BOUNDS when bounds
    is None. Raises ValueError for an unrecognized parameter name when no
    explicit bounds are supplied, or for a bounds pair where lower > upper."""
    if bounds is None:
        if param_name not in DEFAULT_BOUNDS:
            raise ValueError(
                "no default bounds on record for parameter %r; "
                "provide explicit bounds or add to DEFAULT_BOUNDS" % (param_name,)
            )
        lower, upper = DEFAULT_BOUNDS[param_name]
    else:
        lower, upper = bounds
        if lower > upper:
            raise ValueError(
                "lower bound %r exceeds upper bound %r for parameter %r"
                % (lower, upper, param_name)
            )
    return {
        "param": param_name,
        "value": value,
        "lower": lower,
        "upper": upper,
        "in_bounds": lower <= value <= upper,
    }


def assess_coverage(assessed_params, required_params=None):
    """Return a sorted list of required parameter names absent from
    assessed_params.

    assessed_params: any iterable of parameter name strings.
    required_params: collection of parameter names that must be present;
                     defaults to ALL_REQUIRED_PARAMS.
    Does not mutate inputs."""
    if required_params is None:
        required_params = ALL_REQUIRED_PARAMS
    assessed = frozenset(assessed_params)
    return sorted(required_params - assessed)


def environment_review(params, bounds_map=None):
    """Full §4.2.1.6 environment characterisation review.

    params: dict mapping parameter name to measured or predicted value.
    bounds_map: optional dict mapping parameter name to (lower, upper);
                DEFAULT_BOUNDS used for any parameter not present.
    Returns {"out_of_bounds": [...], "missing_params": [...]}.
      out_of_bounds: list of check_bounds result dicts where in_bounds is False.
      missing_params: sorted list of required params absent from params.
    Raises ValueError for any unrecognized parameter name in params."""
    resolved = dict(bounds_map) if bounds_map else {}
    out_of_bounds = []
    for name, value in params.items():
        categorize_parameter(name)          # raises ValueError if unrecognized
        result = check_bounds(name, value, resolved.get(name))
        if not result["in_bounds"]:
            out_of_bounds.append(result)
    missing = assess_coverage(params.keys())
    return {"out_of_bounds": out_of_bounds, "missing_params": missing}


def is_environment_acceptable(review):
    """True when environment_review shows no out-of-bounds values and no
    missing required parameters -- the characterisation is complete and
    within the human-performance acceptability bounds."""
    return (
        len(review["out_of_bounds"]) == 0
        and len(review["missing_params"]) == 0
    )
