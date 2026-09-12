#!/usr/bin/env python3
"""ECSS-E-ST-32C clauses 4.6.3.16–4.6.3.17 ageing and contamination
verification test logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structures standard's ageing and contamination test clauses require
verification that structural materials and passive film coatings retain
adequate mechanical and functional properties after exposure to ageing
environments (thermal cycling, hygrothermal soak, UV irradiation) and
contamination conditions representative of the service life. Each specimen
type is assessed by computing the ratio of post-conditioning to pre-
conditioning property values and comparing against a minimum retention
threshold, while contamination exposure is checked against a recorded
allowable limit. This module implements specimen-type categorization,
ageing-condition validation, property-retention computation, contamination-
exposure assessment, and campaign-level acceptance aggregation.
"""

SPECIMEN_TYPES = frozenset({"passive_film_coating", "structural_material"})

AGEING_CONDITION_TYPES = frozenset(
    {"thermal_cycling", "hygrothermal_soak", "uv_irradiation"}
)


def categorize_specimen(specimen_type):
    """Category for a specimen type: 'passive_film_coating' or
    'structural_material'. Raises ValueError for a type outside both known sets."""
    if specimen_type in SPECIMEN_TYPES:
        return specimen_type
    raise ValueError(
        "unrecognized specimen type %r under E-ST-32C clause 4.6.3.16"
        % (specimen_type,)
    )


def validate_ageing_condition(condition):
    """Validates one ageing condition dict. Returns True on success.
    Raises ValueError for an unrecognized condition type or out-of-range
    field values. Does not mutate the input."""
    condition_type = condition.get("type")
    if condition_type not in AGEING_CONDITION_TYPES:
        raise ValueError(
            "unrecognized ageing condition type %r" % (condition_type,)
        )
    if condition_type == "thermal_cycling":
        cycles = condition.get("cycles")
        if not (isinstance(cycles, (int, float)) and cycles > 0):
            raise ValueError("thermal_cycling requires cycles > 0")
        temp_low = condition.get("temp_low_c")
        temp_high = condition.get("temp_high_c")
        if temp_low is None or temp_high is None:
            raise ValueError(
                "thermal_cycling requires temp_low_c and temp_high_c"
            )
        if temp_low >= temp_high:
            raise ValueError(
                "thermal_cycling requires temp_low_c < temp_high_c"
            )
    elif condition_type == "hygrothermal_soak":
        duration_h = condition.get("duration_h")
        if not (isinstance(duration_h, (int, float)) and duration_h > 0):
            raise ValueError("hygrothermal_soak requires duration_h > 0")
        rh = condition.get("relative_humidity_percent")
        if not (isinstance(rh, (int, float)) and 0 < rh <= 100):
            raise ValueError(
                "hygrothermal_soak requires relative_humidity_percent in (0, 100]"
            )
    elif condition_type == "uv_irradiation":
        dose = condition.get("dose_esh")
        if not (isinstance(dose, (int, float)) and dose > 0):
            raise ValueError("uv_irradiation requires dose_esh > 0")
    return True


def compute_property_retention(pre_value, post_value):
    """Property retention ratio: post_value / pre_value. Raises ValueError
    for a non-positive pre_value or a negative post_value."""
    if pre_value <= 0:
        raise ValueError(
            "pre_value must be positive (got %r)" % (pre_value,)
        )
    if post_value < 0:
        raise ValueError(
            "post_value must be non-negative (got %r)" % (post_value,)
        )
    return post_value / pre_value


def evaluate_ageing_compliance(retention_ratio, min_retention_threshold):
    """True when retention_ratio >= min_retention_threshold. Raises ValueError
    for a threshold outside (0, 1]."""
    if not (0 < min_retention_threshold <= 1.0):
        raise ValueError(
            "min_retention_threshold must be in (0, 1] (got %r)"
            % (min_retention_threshold,)
        )
    return retention_ratio >= min_retention_threshold


def assess_contamination_exposure(exposure_level_mg_m2, max_allowable_mg_m2):
    """Returns 'acceptable' when exposure_level_mg_m2 <= max_allowable_mg_m2,
    else 'exceeds_allowable'. Raises ValueError for any negative argument."""
    if exposure_level_mg_m2 < 0:
        raise ValueError(
            "exposure_level_mg_m2 must be >= 0 (got %r)" % (exposure_level_mg_m2,)
        )
    if max_allowable_mg_m2 < 0:
        raise ValueError(
            "max_allowable_mg_m2 must be >= 0 (got %r)" % (max_allowable_mg_m2,)
        )
    if exposure_level_mg_m2 <= max_allowable_mg_m2:
        return "acceptable"
    return "exceeds_allowable"


def check_specimen_acceptance(specimen):
    """Full ageing and contamination acceptance check for one specimen.

    specimen: {
        "specimen_id": str,
        "specimen_type": str,
        "ageing_conditions": [{"type": str, ...condition fields}],
        "property_measurements": {
            "<property_name>": {
                "pre": float, "post": float, "min_retention": float
            }, ...
        },
        "contamination_exposure_mg_m2": float,
        "contamination_allowable_mg_m2": float | None,
    }

    Returns {"specimen_id": str, "violations": [...], "accepted": bool}.
    Raises ValueError for an unrecognized specimen_type or ageing condition type.
    Does not mutate specimen."""
    specimen_id = specimen["specimen_id"]
    categorize_specimen(specimen["specimen_type"])
    for condition in specimen.get("ageing_conditions", []):
        validate_ageing_condition(condition)

    violations = []

    for prop_name, measurements in specimen.get("property_measurements", {}).items():
        pre = measurements["pre"]
        post = measurements["post"]
        min_ret = measurements["min_retention"]
        retention = compute_property_retention(pre, post)
        if not evaluate_ageing_compliance(retention, min_ret):
            violations.append(
                {
                    "issue": "property_retention_below_threshold",
                    "specimen": specimen_id,
                    "property": prop_name,
                    "retention_ratio": retention,
                    "min_retention_threshold": min_ret,
                }
            )

    exposure = specimen.get("contamination_exposure_mg_m2", 0.0)
    allowable = specimen.get("contamination_allowable_mg_m2")
    if allowable is not None:
        outcome = assess_contamination_exposure(exposure, allowable)
        if outcome == "exceeds_allowable":
            violations.append(
                {
                    "issue": "contamination_exposure_exceeds_allowable",
                    "specimen": specimen_id,
                    "exposure_mg_m2": exposure,
                    "allowable_mg_m2": allowable,
                }
            )
    elif exposure > 0:
        violations.append(
            {
                "issue": "missing_contamination_allowable",
                "specimen": specimen_id,
                "exposure_mg_m2": exposure,
            }
        )

    return {
        "specimen_id": specimen_id,
        "violations": violations,
        "accepted": len(violations) == 0,
    }


def evaluate_test_campaign(specimens):
    """Returns a list of acceptance results (one per specimen). Does not
    mutate specimens."""
    return [check_specimen_acceptance(s) for s in specimens]


def is_campaign_accepted(results):
    """True when all specimen results in a campaign have accepted == True."""
    return all(r["accepted"] for r in results)
