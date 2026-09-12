"""
Reduced Fracture Control Programme — applicability and modifications.
Anchor: ECSS-E-ST-32C clause 11.
Stdlib only; deterministic; offline.
"""

VALID_FRACTURE_CATEGORIES = {"non_fracture_critical", "fracture_critical"}
VALID_CONSEQUENCES = {"minor", "major", "critical", "catastrophic"}
VALID_MISSION_TYPES = {"crewed", "uncrewed"}

# Stress ratio thresholds (max operating stress / yield stress)
STRESS_RATIO_THRESHOLD_UNCREWED = 0.50
STRESS_RATIO_THRESHOLD_CREWED = 0.40

# Minimum acceptable fracture toughness (MPa sqrt(m))
MIN_KIC_MPA_SQRTM = 30.0

# Modifications granted to eligible items
WAIVABLE_STEPS = [
    "crack_growth_life_calculation",
    "fracture_mechanics_stress_intensity_analysis",
    "nde_reduced_to_visual_surface_only",
]

# Mandatory actions retained regardless of reduced programme status
MANDATORY_REMAINING_ACTIONS = [
    "document_operating_stress_ratio",
    "confirm_kic_on_record",
    "retain_consequence_of_failure_justification_in_fcp",
]


class InputError(ValueError):
    """Raised when component input contains an unrecognized or out-of-range value."""


def _validate_component(component: dict) -> None:
    """Raise InputError for any unrecognized or missing mandatory field."""
    required = {
        "id": str,
        "fracture_category": str,
        "consequence": str,
        "operating_stress_ratio": (int, float),
        "mission_type": str,
        "kic_mpa_sqrtm": (int, float),
    }
    for field, expected_type in required.items():
        if field not in component:
            raise InputError(f"Missing required field: '{field}'")
        if not isinstance(component[field], expected_type):
            raise InputError(
                f"Field '{field}' must be {expected_type}, "
                f"got {type(component[field]).__name__}"
            )

    if component["fracture_category"] not in VALID_FRACTURE_CATEGORIES:
        raise InputError(
            f"Unknown fracture_category '{component['fracture_category']}'; "
            f"must be one of {sorted(VALID_FRACTURE_CATEGORIES)}"
        )
    if component["consequence"] not in VALID_CONSEQUENCES:
        raise InputError(
            f"Unknown consequence '{component['consequence']}'; "
            f"must be one of {sorted(VALID_CONSEQUENCES)}"
        )
    if component["mission_type"] not in VALID_MISSION_TYPES:
        raise InputError(
            f"Unknown mission_type '{component['mission_type']}'; "
            f"must be one of {sorted(VALID_MISSION_TYPES)}"
        )

    ratio = component["operating_stress_ratio"]
    if not (0.0 <= ratio <= 1.0):
        raise InputError(
            f"operating_stress_ratio must be in [0, 1], got {ratio}"
        )

    kic = component["kic_mpa_sqrtm"]
    if kic <= 0.0:
        raise InputError(
            f"kic_mpa_sqrtm must be positive, got {kic}"
        )


def assess_eligibility(component: dict) -> dict:
    """
    Determine whether a single structural item qualifies for the reduced
    fracture control programme (ECSS-E-ST-32C clause 11) and list which
    programme steps may be modified.

    Parameters
    ----------
    component : dict with keys:
        id                    : str — item identifier
        fracture_category     : "fracture_critical" | "non_fracture_critical"
        consequence           : "minor" | "major" | "critical" | "catastrophic"
        operating_stress_ratio: float in [0, 1]  (max_stress / yield_stress)
        mission_type          : "crewed" | "uncrewed"
        kic_mpa_sqrtm         : float > 0  (fracture toughness in MPa sqrt(m))

    Returns
    -------
    dict with keys:
        id                   : str
        eligible             : bool
        ineligibility_reason : str | None  (None when eligible)
        modifications        : list[str]   (empty when not eligible)
        mandatory_actions    : list[str]   (always populated)
    """
    _validate_component(component)

    item_id = component["id"]
    result = {
        "id": item_id,
        "eligible": False,
        "ineligibility_reason": None,
        "modifications": [],
        "mandatory_actions": list(MANDATORY_REMAINING_ACTIONS),
    }

    # Screen 1: fracture category
    if component["fracture_category"] == "fracture_critical":
        result["ineligibility_reason"] = (
            "Item is fracture-critical; full programme required."
        )
        return result

    # Screen 2: consequence of failure
    if component["consequence"] == "catastrophic":
        result["ineligibility_reason"] = (
            "Consequence of failure is catastrophic; full programme required."
        )
        return result

    # Screen 3: operating stress ratio
    mission = component["mission_type"]
    threshold = (
        STRESS_RATIO_THRESHOLD_CREWED
        if mission == "crewed"
        else STRESS_RATIO_THRESHOLD_UNCREWED
    )
    ratio = component["operating_stress_ratio"]
    if ratio > threshold:
        result["ineligibility_reason"] = (
            f"Operating stress ratio {ratio:.4f} exceeds allowable "
            f"{threshold:.2f} for {mission} mission."
        )
        return result

    # Screen 4: fracture toughness
    kic = component["kic_mpa_sqrtm"]
    if kic < MIN_KIC_MPA_SQRTM:
        result["ineligibility_reason"] = (
            f"K_IC {kic:.2f} MPa√m is below minimum {MIN_KIC_MPA_SQRTM:.1f} "
            f"MPa√m; full fracture mechanics treatment required."
        )
        return result

    # All screens passed
    result["eligible"] = True
    result["modifications"] = list(WAIVABLE_STEPS)
    return result


def assess_batch(components: list) -> list:
    """
    Assess a list of component dicts; returns a result dict for each.
    Raises InputError on the first invalid component encountered.
    """
    return [assess_eligibility(c) for c in components]


def summary_counts(results: list) -> dict:
    """
    Tally eligible and ineligible items from a batch result list.

    Returns dict with keys: total, eligible, ineligible.
    """
    eligible = sum(1 for r in results if r["eligible"])
    return {
        "total": len(results),
        "eligible": eligible,
        "ineligible": len(results) - eligible,
    }
