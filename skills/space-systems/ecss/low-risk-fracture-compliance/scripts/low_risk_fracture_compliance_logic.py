"""
Low-risk fracture item compliance logic.
Implements the qualification procedure for ECSS E-ST-32C clause 6.3.5:
load-limited metal criterion and non-fracture-critical consequence check.
stdlib only; deterministic; offline.
"""

LOAD_LIMITED_STRESS_RATIO_THRESHOLD = 0.6  # max stress / yield strength

NON_FRACTURE_CRITICAL_CONSEQUENCES = frozenset({
    "contained_failure",
    "redundant_load_path",
    "non_structural_function",
    "cosmetic_only",
    "mission_non_critical",
})

FRACTURE_CRITICAL_CONSEQUENCES = frozenset({
    "loss_of_crew_safety",
    "loss_of_mission",
    "primary_structure_single_load_path",
    "pressure_vessel_failure",
    "life_support_failure",
})


class LowRiskFractureError(ValueError):
    """Raised when input data is invalid or cannot be evaluated."""


def check_load_limited(
    max_stress_mpa: float,
    yield_strength_mpa: float,
    threshold_ratio: float = LOAD_LIMITED_STRESS_RATIO_THRESHOLD,
) -> dict:
    """
    Verify the load-limited criterion for a metal item.

    Criterion: max_stress / yield_strength <= threshold_ratio.

    Returns dict: passes, stress_ratio, margin, threshold, criterion.
    Raises LowRiskFractureError on invalid inputs.
    """
    if not isinstance(max_stress_mpa, (int, float)) or max_stress_mpa <= 0:
        raise LowRiskFractureError(
            f"max_stress_mpa must be a positive number, got {max_stress_mpa!r}"
        )
    if not isinstance(yield_strength_mpa, (int, float)) or yield_strength_mpa <= 0:
        raise LowRiskFractureError(
            f"yield_strength_mpa must be a positive number, got {yield_strength_mpa!r}"
        )
    if not isinstance(threshold_ratio, (int, float)) or not (0.0 < threshold_ratio <= 1.0):
        raise LowRiskFractureError(
            f"threshold_ratio must be in (0, 1], got {threshold_ratio!r}"
        )

    stress_ratio = max_stress_mpa / yield_strength_mpa
    margin = threshold_ratio - stress_ratio
    passes = stress_ratio <= threshold_ratio

    return {
        "passes": passes,
        "stress_ratio": round(stress_ratio, 6),
        "margin": round(margin, 6),
        "threshold": threshold_ratio,
        "criterion": "load_limited",
    }


def check_non_fracture_critical(failure_consequence: str) -> dict:
    """
    Determine whether an item qualifies as non-fracture-critical based on its failure consequence.

    Returns dict: passes, failure_consequence, basis, criterion.
    Raises LowRiskFractureError on empty or unrecognized consequence.
    """
    if not failure_consequence or not isinstance(failure_consequence, str):
        raise LowRiskFractureError("failure_consequence must be a non-empty string")

    fc_lower = failure_consequence.strip().lower()

    if fc_lower in FRACTURE_CRITICAL_CONSEQUENCES:
        return {
            "passes": False,
            "failure_consequence": fc_lower,
            "basis": "fracture_critical_consequence",
            "criterion": "non_fracture_critical",
        }

    if fc_lower in NON_FRACTURE_CRITICAL_CONSEQUENCES:
        return {
            "passes": True,
            "failure_consequence": fc_lower,
            "basis": "accepted_low_risk_consequence",
            "criterion": "non_fracture_critical",
        }

    raise LowRiskFractureError(
        f"Unrecognized failure consequence '{failure_consequence}'. "
        f"Must be one of: {sorted(NON_FRACTURE_CRITICAL_CONSEQUENCES | FRACTURE_CRITICAL_CONSEQUENCES)}"
    )


def qualify_low_risk_item(item: dict) -> dict:
    """
    Determine whether a structural item qualifies as a low-risk fracture item.

    An item qualifies if the load-limited criterion passes (stress data provided)
    OR the non-fracture-critical criterion passes (consequence data provided),
    and the consequence is not fracture-critical.

    Required key: name (str).
    Optional keys (at least one path must be evaluable):
      max_stress_mpa, yield_strength_mpa — for load-limited check.
      failure_consequence — for non-fracture-critical check.
      threshold_ratio — custom load-limited threshold (default 0.6).

    Returns dict: name, qualifies, path, findings.
    Raises LowRiskFractureError on malformed input or no evaluable path.
    """
    if not isinstance(item, dict):
        raise LowRiskFractureError("item must be a dict")
    name = item.get("name")
    if not name:
        raise LowRiskFractureError("item must have a non-empty 'name' field")

    findings = []
    load_limited_result = None
    nfc_result = None

    has_stress_data = "max_stress_mpa" in item and "yield_strength_mpa" in item
    has_consequence_data = "failure_consequence" in item

    if not has_stress_data and not has_consequence_data:
        raise LowRiskFractureError(
            f"Item '{name}': must provide either stress data "
            "(max_stress_mpa + yield_strength_mpa) or failure_consequence."
        )

    if has_stress_data:
        threshold = item.get("threshold_ratio", LOAD_LIMITED_STRESS_RATIO_THRESHOLD)
        load_limited_result = check_load_limited(
            item["max_stress_mpa"], item["yield_strength_mpa"], threshold
        )

    if has_consequence_data:
        nfc_result = check_non_fracture_critical(item["failure_consequence"])

    # Fracture-critical consequence is an absolute disqualifier
    if nfc_result is not None and not nfc_result["passes"]:
        findings.append(
            f"Fracture-critical consequence '{nfc_result['failure_consequence']}'"
            " — item cannot follow the low-risk path."
        )
        return {"name": name, "qualifies": False, "path": None, "findings": findings}

    qualifying_path = None
    if load_limited_result is not None and load_limited_result["passes"]:
        qualifying_path = "load_limited"
    elif nfc_result is not None and nfc_result["passes"]:
        qualifying_path = "non_fracture_critical"

    if load_limited_result is not None and not load_limited_result["passes"]:
        findings.append(
            f"Load-limited criterion not met: stress ratio "
            f"{load_limited_result['stress_ratio']:.4f} > "
            f"threshold {load_limited_result['threshold']:.2f}."
        )

    return {
        "name": name,
        "qualifies": qualifying_path is not None,
        "path": qualifying_path,
        "findings": findings,
    }


def assess_compliance(items: list) -> dict:
    """
    Assess low-risk fracture compliance for a list of structural items.

    Returns dict: total, qualified, not_qualified, errors, results, fully_compliant.
    Raises LowRiskFractureError if items is not a list.
    """
    if not isinstance(items, list):
        raise LowRiskFractureError("items must be a list")

    results = []
    qualified = 0
    not_qualified = 0
    errors = 0

    for item in items:
        try:
            result = qualify_low_risk_item(item)
            results.append(result)
            if result["qualifies"]:
                qualified += 1
            else:
                not_qualified += 1
        except LowRiskFractureError as exc:
            errors += 1
            name = item.get("name", "<unknown>") if isinstance(item, dict) else "<unknown>"
            results.append({
                "name": name,
                "qualifies": False,
                "path": None,
                "findings": [f"Evaluation error: {exc}"],
                "error": True,
            })

    total = len(items)
    return {
        "total": total,
        "qualified": qualified,
        "not_qualified": not_qualified,
        "errors": errors,
        "results": results,
        "fully_compliant": qualified == total and errors == 0,
    }
