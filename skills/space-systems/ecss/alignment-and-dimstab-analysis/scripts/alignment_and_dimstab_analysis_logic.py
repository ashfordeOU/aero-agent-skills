#!/usr/bin/env python3
"""ECSS-E-ST-32C clauses 4.6.2.19–4.6.2.20 alignment demonstration and
dimensional stability analysis (paraphrase — not verbatim text).

Common-knowledge procedure summary (standards-map.yaml, ecss: gated false):
clause 4.6.2.19 requires demonstrating by analysis that each alignment-critical
interface stays within its requirement across all applicable load cases; alignment
contributors are categorized as systematic (manufacturing tolerance, combined by
absolute sum) or random (thermo-elastic, hygrothermal, load-induced, creep —
combined by root-sum-square), and the analysis must cover at minimum the hot-case,
cold-case, and eclipse thermal environments. Clause 4.6.2.20 requires dimensional
stability analysis for elements where dimensional change affects performance; the
analysis computes the thermo-elastic component (|α × L × ΔT|) and the hygrothermal
component (|CME × Δm × L|), sums them conservatively (worst-case phasing), and
compares the result against the element's dimensional allowable. This module
implements contributor categorization, budget combination, thermal-case coverage
checking, per-element dimensional stability computation, and violation reporting;
it does not define alignment requirements or dimensional allowables.
"""

import math

# Contributor source types — systematic contributors add linearly;
# random contributors combine via root-sum-square.
SYSTEMATIC_SOURCE_TYPES = frozenset({"manufacturing_tolerance"})
RANDOM_SOURCE_TYPES = frozenset(
    {"thermo_elastic", "hygrothermal", "load_induced", "creep"}
)
ALL_SOURCE_TYPES = SYSTEMATIC_SOURCE_TYPES | RANDOM_SOURCE_TYPES

# Thermal environments required for a complete alignment demonstration
# per clause 4.6.2.19 (paraphrased).
REQUIRED_THERMAL_CASES = frozenset({"hot_case", "cold_case", "eclipse"})


def categorize_contributor(source_type):
    """Combination category for an alignment contributor: "systematic"
    (absolute sum) or "random" (root-sum-square).
    Raises ValueError for an unrecognized source type."""
    if source_type in SYSTEMATIC_SOURCE_TYPES:
        return "systematic"
    if source_type in RANDOM_SOURCE_TYPES:
        return "random"
    raise ValueError(
        "unrecognized alignment contributor type %r under "
        "E-ST-32C clause 4.6.2.19; recognized types: %s"
        % (source_type, sorted(ALL_SOURCE_TYPES))
    )


def thermo_elastic_deformation(cte_per_K, length_m, delta_T_K):
    """Thermo-elastic deformation |α × L × ΔT| in metres.
    Raises ValueError for negative CTE or non-positive length."""
    if cte_per_K < 0:
        raise ValueError("cte_per_K must be >= 0, got %r" % cte_per_K)
    if length_m <= 0:
        raise ValueError("length_m must be > 0, got %r" % length_m)
    return abs(cte_per_K * length_m * delta_T_K)


def hygrothermal_deformation(cme, length_m, delta_moisture):
    """Hygrothermal expansion |CME × Δm × L| in metres.
    CME is the coefficient of moisture expansion (m/m per kg/kg).
    Raises ValueError for negative CME, non-positive length, or negative moisture change."""
    if cme < 0:
        raise ValueError("cme must be >= 0, got %r" % cme)
    if length_m <= 0:
        raise ValueError("length_m must be > 0, got %r" % length_m)
    if delta_moisture < 0:
        raise ValueError("delta_moisture must be >= 0, got %r" % delta_moisture)
    return abs(cme * delta_moisture * length_m)


def lateral_deformation_to_arcsec(lateral_delta_m, baseline_m):
    """Angular misalignment (arcseconds) from a lateral deformation via
    the small-angle approximation: θ = atan(ΔL / L) converted to arcseconds.
    Raises ValueError for non-positive baseline or negative deformation."""
    if baseline_m <= 0:
        raise ValueError("baseline_m must be > 0, got %r" % baseline_m)
    if lateral_delta_m < 0:
        raise ValueError("lateral_delta_m must be >= 0, got %r" % lateral_delta_m)
    theta_rad = math.atan(lateral_delta_m / baseline_m)
    return math.degrees(theta_rad) * 3600.0


def combine_alignment_budget(contributors):
    """Combine alignment contributors into a total misalignment (arcseconds).

    contributors: iterable of dicts with keys:
      "source_type" (str in ALL_SOURCE_TYPES) and "value_arcsec" (float >= 0).
      Optionally "name" (str) for error messages.

    Combination rule (clause 4.6.2.19, paraphrased):
      total = systematic_sum + sqrt(sum_of_squares_of_random_contributors)

    Returns {"systematic_sum": float, "random_rss": float, "total": float}.
    Raises ValueError for an empty list, negative value, or unrecognized source_type.
    Does not mutate contributors."""
    contributors = list(contributors)
    if not contributors:
        raise ValueError("contributor list must not be empty")

    systematic_sum = 0.0
    random_sq = 0.0

    for c in contributors:
        v = c["value_arcsec"]
        if v < 0:
            raise ValueError(
                "value_arcsec must be >= 0 for contributor %r, got %r"
                % (c.get("name", "<unnamed>"), v)
            )
        category = categorize_contributor(c["source_type"])
        if category == "systematic":
            systematic_sum += v
        else:
            random_sq += v * v

    random_rss = math.sqrt(random_sq)
    total = systematic_sum + random_rss
    return {"systematic_sum": systematic_sum, "random_rss": random_rss, "total": total}


def alignment_budget_violations(interface_id, contributors, budget_arcsec):
    """Violation list for one alignment interface (empty list = compliant).

    A missing (None) or non-positive budget is itself a finding — it means
    the requirement was not captured, which is not a pass.
    Does not mutate contributors."""
    if budget_arcsec is None or budget_arcsec <= 0:
        return [
            {
                "issue": "missing_or_invalid_alignment_budget",
                "interface": interface_id,
                "budget_arcsec": budget_arcsec,
            }
        ]

    result = combine_alignment_budget(contributors)
    total = result["total"]
    if total > budget_arcsec:
        return [
            {
                "issue": "alignment_budget_exceeded",
                "interface": interface_id,
                "total_arcsec": total,
                "budget_arcsec": budget_arcsec,
                "margin_arcsec": budget_arcsec - total,
            }
        ]
    return []


def check_thermal_case_coverage(thermal_cases):
    """Verify that the required thermal environments are represented.

    thermal_cases: iterable of case name strings.
    Returns {"covered": bool, "missing": sorted list of missing case names}.
    Per clause 4.6.2.19 (paraphrased), hot_case, cold_case, and eclipse
    must all be present; any omission makes the demonstration incomplete."""
    provided = frozenset(thermal_cases)
    missing = sorted(REQUIRED_THERMAL_CASES - provided)
    return {"covered": len(missing) == 0, "missing": missing}


def dimstab_violations(element_id, cte_per_K, length_m, delta_T_K,
                       cme, delta_moisture, allowable_delta_m):
    """Violation list for dimensional stability of one element (empty list = compliant).

    Computes total dimensional change = thermo-elastic + hygrothermal (absolute
    sum, conservative worst-case phasing) and compares against the allowable.
    Per clause 4.6.2.20 (paraphrased).
    A missing (None) or non-positive allowable is flagged as a missing requirement."""
    if allowable_delta_m is None or allowable_delta_m <= 0:
        return [
            {
                "issue": "missing_or_invalid_dimstab_allowable",
                "element": element_id,
                "allowable_delta_m": allowable_delta_m,
            }
        ]

    te = thermo_elastic_deformation(cte_per_K, length_m, delta_T_K)
    hy = hygrothermal_deformation(cme, length_m, delta_moisture)
    total = te + hy

    if total > allowable_delta_m:
        return [
            {
                "issue": "dimstab_allowable_exceeded",
                "element": element_id,
                "thermo_elastic_delta_m": te,
                "hygrothermal_delta_m": hy,
                "total_delta_m": total,
                "allowable_delta_m": allowable_delta_m,
                "margin_m": allowable_delta_m - total,
            }
        ]
    return []


def is_element_compliant(violations):
    """True when the violation list is empty."""
    return len(violations) == 0
