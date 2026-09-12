"""
Structural Alignment Budget logic — ECSS-E-ST-32C Annex L.

Implements contributor categorization, sensitivity application, combination
(RSS and worst-case arithmetic), and budget compliance checking.
stdlib only; no external dependencies.
"""

import math

# Canonical contributor types for ECSS-E-ST-32C Annex L alignment budgets.
CONTRIBUTOR_TYPES = {
    "manufacturing": "manufacturing-tolerance",
    "thermoelastic": "thermoelastic-distortion",
    "gravity-release": "gravity-release-deformation",
    "load-induced": "load-induced-deflection",
    "measurement": "measurement-uncertainty",
}

COMBINATION_METHODS = {"rss", "worst-case"}


def categorize_contributor(contributor_type: str) -> str:
    """
    Return the canonical category label for a contributor type key.

    Raises ValueError for unrecognized types so callers never silently
    carry unknown contributors into the budget.
    """
    if contributor_type not in CONTRIBUTOR_TYPES:
        raise ValueError(
            f"Unrecognized contributor type: '{contributor_type}'. "
            f"Accepted types: {sorted(CONTRIBUTOR_TYPES)}"
        )
    return CONTRIBUTOR_TYPES[contributor_type]


def apply_sensitivity(magnitude: float, sensitivity: float) -> float:
    """
    Multiply raw error magnitude by sensitivity coefficient.

    Both arguments must be non-negative. A sensitivity of 1.0 means no
    mechanical amplification; values above 1.0 indicate amplification.
    """
    if magnitude < 0:
        raise ValueError(
            f"Error magnitude must be non-negative; got {magnitude}"
        )
    if sensitivity < 0:
        raise ValueError(
            f"Sensitivity coefficient must be non-negative; got {sensitivity}"
        )
    return magnitude * sensitivity


def combine_rss(effective_errors: list) -> float:
    """
    Combine a list of effective errors by root-sum-square.

    Appropriate for statistically independent, uncorrelated contributors.
    Requires at least one entry.
    """
    if not effective_errors:
        raise ValueError(
            "combine_rss requires at least one effective error value"
        )
    return math.sqrt(sum(e * e for e in effective_errors))


def combine_worst_case(effective_errors: list) -> float:
    """
    Combine a list of effective errors by worst-case arithmetic sum.

    Appropriate for systematic or correlated contributors. Sums absolute
    values to reflect maximum possible accumulation. Requires at least one entry.
    """
    if not effective_errors:
        raise ValueError(
            "combine_worst_case requires at least one effective error value"
        )
    return sum(abs(e) for e in effective_errors)


def check_budget(total_error: float, allowable) -> dict:
    """
    Compare the total alignment error against the allowable value.

    Returns a dict with keys:
      status      — "compliant", "exceeded", or "missing-budget"
      exceedance  — positive margin of exceedance, 0.0 when compliant,
                    None when budget is missing
    """
    if allowable is None:
        return {"status": "missing-budget", "exceedance": None}
    if total_error > allowable:
        return {
            "status": "exceeded",
            "exceedance": total_error - allowable,
        }
    return {"status": "compliant", "exceedance": 0.0}


def build_alignment_budget(
    contributors: list,
    method: str = "rss",
    allowable=None,
) -> dict:
    """
    Build a complete alignment budget from a list of contributor records.

    Each contributor is a dict with:
      type        — contributor type key (see CONTRIBUTOR_TYPES)
      magnitude   — raw error magnitude (arcsec, mm, or any consistent unit)
      sensitivity — dimensionless sensitivity coefficient (>= 0)

    method      — "rss" or "worst-case"
    allowable   — maximum total alignment error in the same unit, or None

    Returns a result dict with:
      contributors       — list of contributor dicts with category and effective_error
      combination_method — method used
      total_error        — combined total alignment error
      allowable          — the allowable value passed in
      budget_status      — "compliant", "exceeded", or "missing-budget"
      exceedance         — exceedance margin (0.0 when compliant, None when missing)
    """
    if not contributors:
        raise ValueError(
            "build_alignment_budget requires at least one contributor"
        )
    if method not in COMBINATION_METHODS:
        raise ValueError(
            f"Unrecognized combination method: '{method}'. "
            f"Accepted: {sorted(COMBINATION_METHODS)}"
        )

    processed = []
    effective_errors = []

    for c in contributors:
        category = categorize_contributor(c["type"])
        eff = apply_sensitivity(c["magnitude"], c["sensitivity"])
        effective_errors.append(eff)
        processed.append(
            {
                "type": c["type"],
                "category": category,
                "magnitude": c["magnitude"],
                "sensitivity": c["sensitivity"],
                "effective_error": eff,
            }
        )

    if method == "rss":
        total = combine_rss(effective_errors)
    else:
        total = combine_worst_case(effective_errors)

    budget_result = check_budget(total, allowable)

    return {
        "contributors": processed,
        "combination_method": method,
        "total_error": total,
        "allowable": allowable,
        "budget_status": budget_result["status"],
        "exceedance": budget_result["exceedance"],
    }
