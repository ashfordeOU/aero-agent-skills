"""
Dimensional stability analysis (DSA) DRD content checker and computation
helpers — ECSS-E-ST-32C Annex C.

All computations are deterministic and use stdlib only (no third-party deps).
"""

import math

# ---------------------------------------------------------------------------
# Mandatory DRD sections — ECSS-E-ST-32C Annex C
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = [
    "scope",
    "applicable_documents",
    "structure_description",
    "material_properties",
    "thermal_environments",
    "moisture_environments",
    "analysis_method",
    "displacement_results",
    "stability_requirements",
    "margin_summary",
    "conclusions",
]

VALID_CONTRIBUTOR_TYPES = {"thermal", "hygrothermal", "mechanical"}
VALID_ANALYSIS_METHODS = {"analytical", "fea", "test_correlated"}


def validate_required_sections(report: dict) -> list:
    """Return list of missing mandatory DRD section keys.

    Raises TypeError if report is not a dict.
    """
    if not isinstance(report, dict):
        raise TypeError("report must be a dict")
    return [s for s in REQUIRED_SECTIONS if s not in report]


def compute_thermal_displacement(alpha_per_K: float, length_mm: float, delta_T_K: float) -> float:
    """Compute linear thermal displacement: delta = alpha * L * delta_T.

    Parameters
    ----------
    alpha_per_K : CTE in 1/K (finite; may be negative for zero-CTE laminates)
    length_mm   : nominal member length in mm (must be > 0)
    delta_T_K   : temperature change in K (signed; worst-case extreme)

    Returns
    -------
    Displacement in mm (signed).
    """
    if not math.isfinite(alpha_per_K):
        raise ValueError("alpha_per_K must be finite")
    if not math.isfinite(length_mm) or length_mm <= 0:
        raise ValueError("length_mm must be positive and finite")
    if not math.isfinite(delta_T_K):
        raise ValueError("delta_T_K must be finite")
    return alpha_per_K * length_mm * delta_T_K


def compute_hygrothermal_displacement(beta_per_pct: float, length_mm: float, delta_moisture_pct: float) -> float:
    """Compute hygrothermal (moisture-induced) displacement: delta = beta * L * delta_M.

    Parameters
    ----------
    beta_per_pct      : coefficient of moisture expansion in 1/% (finite)
    length_mm         : nominal member length in mm (must be > 0)
    delta_moisture_pct: moisture content change in % (signed)

    Returns
    -------
    Displacement in mm (signed).
    """
    if not math.isfinite(beta_per_pct):
        raise ValueError("beta_per_pct must be finite")
    if not math.isfinite(length_mm) or length_mm <= 0:
        raise ValueError("length_mm must be positive and finite")
    if not math.isfinite(delta_moisture_pct):
        raise ValueError("delta_moisture_pct must be finite")
    return beta_per_pct * length_mm * delta_moisture_pct


def compute_combined_displacement(thermal_mm: float, hygro_mm: float) -> float:
    """Combine thermal and hygrothermal displacements by algebraic sum.

    Returns total displacement in mm.
    """
    if not math.isfinite(thermal_mm):
        raise ValueError("thermal_mm must be finite")
    if not math.isfinite(hygro_mm):
        raise ValueError("hygro_mm must be finite")
    return thermal_mm + hygro_mm


def compute_stability_margin(allowable_mm: float, actual_mm: float) -> float:
    """Compute dimensional stability margin: margin = (allowable / |actual|) - 1.

    A margin >= 0 indicates compliance; < 0 is an exceedance.

    Parameters
    ----------
    allowable_mm : positive allowable displacement magnitude (must be > 0)
    actual_mm    : computed displacement (signed; magnitude is used)

    Returns
    -------
    Margin (dimensionless). Returns +inf when actual_mm == 0.
    """
    if not math.isfinite(allowable_mm) or allowable_mm <= 0:
        raise ValueError("allowable_mm must be positive and finite")
    if not math.isfinite(actual_mm):
        raise ValueError("actual_mm must be finite")
    if actual_mm == 0.0:
        return float("inf")
    return (allowable_mm / abs(actual_mm)) - 1.0


def assess_cte_mismatch(alpha1_per_K: float, alpha2_per_K: float, threshold_per_K: float) -> dict:
    """Assess CTE mismatch between two joined dissimilar materials.

    Parameters
    ----------
    alpha1_per_K, alpha2_per_K : CTE values in 1/K for material 1 and 2
    threshold_per_K            : maximum allowable |alpha1 - alpha2| (must be >= 0)

    Returns
    -------
    dict with keys:
        mismatch (float) : |alpha1 - alpha2|
        threshold (float): supplied threshold
        exceeds (bool)   : True if mismatch > threshold
    """
    for v, name in [(alpha1_per_K, "alpha1_per_K"), (alpha2_per_K, "alpha2_per_K"), (threshold_per_K, "threshold_per_K")]:
        if not math.isfinite(v):
            raise ValueError(f"{name} must be finite")
    if threshold_per_K < 0:
        raise ValueError("threshold_per_K must be >= 0")
    mismatch = abs(alpha1_per_K - alpha2_per_K)
    return {"mismatch": mismatch, "threshold": threshold_per_K, "exceeds": mismatch > threshold_per_K}


def validate_material_entry(material: dict) -> list:
    """Validate a single material entry has all required DSA properties.

    Required keys: name (str), alpha_per_K (float), beta_per_pct (float), E_GPa (float).
    Returns list of issue strings (empty list = valid). Raises TypeError if not a dict.
    """
    if not isinstance(material, dict):
        raise TypeError("material must be a dict")
    required_numeric = ["alpha_per_K", "beta_per_pct", "E_GPa"]
    issues = []
    if "name" not in material:
        issues.append("missing:name")
    for key in required_numeric:
        if key not in material:
            issues.append(f"missing:{key}")
        elif not isinstance(material[key], (int, float)):
            issues.append(f"non-numeric:{key}")
        elif not math.isfinite(float(material[key])):
            issues.append(f"non-finite:{key}")
    return issues


def categorize_displacement_contributors(contributors: list) -> dict:
    """Categorize displacement contributors by type.

    Each contributor dict must have a 'type' key in VALID_CONTRIBUTOR_TYPES.
    Unknown types go into the 'unknown' bucket.

    Returns
    -------
    dict: {type_name: [contributor, ...]} for each valid type plus 'unknown'.
    Raises ValueError if contributors is not a list.
    """
    if not isinstance(contributors, list):
        raise ValueError("contributors must be a list")
    buckets: dict = {t: [] for t in VALID_CONTRIBUTOR_TYPES}
    buckets["unknown"] = []
    for c in contributors:
        ctype = c.get("type", "").lower() if isinstance(c, dict) else ""
        if ctype in VALID_CONTRIBUTOR_TYPES:
            buckets[ctype].append(c)
        else:
            buckets["unknown"].append(c)
    return buckets


def check_stability_requirement(displacement_mm: float, requirement_mm: float) -> str:
    """Compare computed displacement magnitude against a stability requirement.

    Returns 'PASS' if |displacement_mm| <= requirement_mm, else 'FAIL'.
    Raises ValueError for non-positive requirement or non-finite inputs.
    """
    if not math.isfinite(displacement_mm):
        raise ValueError("displacement_mm must be finite")
    if not math.isfinite(requirement_mm) or requirement_mm <= 0:
        raise ValueError("requirement_mm must be positive and finite")
    return "PASS" if abs(displacement_mm) <= requirement_mm else "FAIL"


def validate_analysis_method(method: str) -> bool:
    """Return True if method is a recognized DSA analysis approach, else False."""
    return isinstance(method, str) and method.lower() in VALID_ANALYSIS_METHODS
