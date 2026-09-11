"""
Shielding calculation uncertainty logic — ECSS-E-ST-10C §6.4.

Implements, as deterministic offline engineering logic, the procedure the leaf
describes: every uncertainty contributor is assigned to exactly one of three
families (model, geometry, cross-section), carries a fractional uncertainty in
[0, 1], is combined by root-sum-square for independent contributors or by a
linear worst-case sum for correlated ones, and the combined fractional
uncertainty is applied as a k-sigma margin to the nominal shielded dose or
fluence before the result is checked against the shielding requirement.

No third-party dependencies — stdlib only. No network. Deterministic.
"""

import math

# --- The three uncertainty families of §6.4 -------------------------------
FAMILY_MODEL = "model"
FAMILY_GEOMETRY = "geometry"
FAMILY_CROSS_SECTION = "cross_section"

# Fixed order: used for deterministic tie-breaking of the dominant family.
UNCERTAINTY_FAMILIES = (FAMILY_MODEL, FAMILY_GEOMETRY, FAMILY_CROSS_SECTION)

# Accepted spellings of each family, so a caller may write "transport code"
# or "nuclear data" and still land in exactly one family.
_FAMILY_ALIASES = {
    "model": FAMILY_MODEL,
    "transport": FAMILY_MODEL,
    "transport_code": FAMILY_MODEL,
    "code": FAMILY_MODEL,
    "dose_conversion": FAMILY_MODEL,
    "dose_conversion_factor": FAMILY_MODEL,
    "geometry": FAMILY_GEOMETRY,
    "mesh": FAMILY_GEOMETRY,
    "structural": FAMILY_GEOMETRY,
    "structural_model": FAMILY_GEOMETRY,
    "as_built": FAMILY_GEOMETRY,
    "cross-section": FAMILY_CROSS_SECTION,
    "cross_section": FAMILY_CROSS_SECTION,
    "crosssection": FAMILY_CROSS_SECTION,
    "nuclear_data": FAMILY_CROSS_SECTION,
    "cross_section_data": FAMILY_CROSS_SECTION,
    "reaction_data": FAMILY_CROSS_SECTION,
}

COMBINATION_METHODS = ("rss", "worst_case")

# Numerical tolerance for exact-boundary comparisons.
_TOL = 1e-12


def _require_number(value, label):
    """Return value as float, rejecting booleans and non-numeric input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number; got {value!r}")
    return float(value)


def resolve_family(value):
    """
    Map a contributor's family spelling to one canonical family name.

    Accepts the canonical names plus the common engineering synonyms
    (transport/code -> model, mesh/structural -> geometry,
    nuclear_data -> cross_section).

    Ref: ECSS-E-ST-10C §6.4 — uncertainty contributor families.

    Raises ValueError when the family is missing, not a string, or cannot be
    mapped to exactly one family (the contributor must not enter the budget).
    """
    if not isinstance(value, str):
        raise ValueError(
            f"family must be a string; got {value!r}. "
            f"Valid families: {list(UNCERTAINTY_FAMILIES)}"
        )
    key = value.strip().lower().replace(" ", "_")
    if key not in _FAMILY_ALIASES:
        raise ValueError(
            f"Unknown uncertainty family {value!r}. "
            f"Valid families: {list(UNCERTAINTY_FAMILIES)}"
        )
    return _FAMILY_ALIASES[key]


def validate_contributor(contributor):
    """
    Validate and normalise one uncertainty contributor.

    Mandatory keys:
      id                     — non-empty contributor identifier (string)
      family                 — model | geometry | cross_section (or a synonym)
      fractional_uncertainty — dimensionless ratio in [0, 1]
    Optional keys:
      substantiated — bool, default True; False marks an unreviewed
                      engineering-judgement placeholder
      rationale     — free-text justification (documented in the report)

    Returns a normalised dict with the canonical family name.

    Raises ValueError for a non-dict contributor, a missing/blank id, a
    missing or unresolvable family, a non-numeric or out-of-range fractional
    uncertainty, or a non-boolean 'substantiated' flag.
    """
    if not isinstance(contributor, dict):
        raise ValueError(f"contributor must be a dict; got {type(contributor).__name__}")

    for key in ("id", "family", "fractional_uncertainty"):
        if key not in contributor:
            raise ValueError(f"contributor is missing mandatory key '{key}'")

    cid = contributor["id"]
    if not isinstance(cid, str) or not cid.strip():
        raise ValueError(f"contributor 'id' must be a non-empty string; got {cid!r}")

    frac = _require_number(
        contributor["fractional_uncertainty"],
        f"fractional_uncertainty for contributor '{cid}'",
    )
    if frac < 0.0 or frac > 1.0:
        raise ValueError(
            f"fractional_uncertainty for contributor '{cid}' must be within "
            f"[0, 1]; got {frac}"
        )

    substantiated = contributor.get("substantiated", True)
    if not isinstance(substantiated, bool):
        raise ValueError(
            f"'substantiated' for contributor '{cid}' must be a boolean; "
            f"got {substantiated!r}"
        )

    return {
        "id": cid.strip(),
        "family": resolve_family(contributor["family"]),
        "fractional_uncertainty": frac,
        "substantiated": substantiated,
        "rationale": contributor.get("rationale", ""),
    }


def _normalise_all(contributors):
    """Validate a sequence of contributors and return the normalised list."""
    if isinstance(contributors, (str, bytes)) or not isinstance(contributors, (list, tuple)):
        raise ValueError(
            "contributors must be a list or tuple of contributor dicts; "
            f"got {type(contributors).__name__}"
        )
    if not contributors:
        raise ValueError("contributors must not be empty — no uncertainty budget to combine")
    return [validate_contributor(c) for c in contributors]


def check_duplicate_contributors(contributors):
    """
    Return the sorted ids that occur more than once in the contributor list.

    A repeated id means the same source of error has been counted twice (or
    assigned to two families), which inflates the combined uncertainty.
    An empty list means every contributor is unique.

    Raises ValueError for a malformed contributor list.
    """
    normalised = _normalise_all(contributors)
    seen = set()
    duplicates = set()
    for item in normalised:
        if item["id"] in seen:
            duplicates.add(item["id"])
        seen.add(item["id"])
    return sorted(duplicates)


def family_totals(contributors):
    """
    Return the per-family sum of squared fractional uncertainties.

    This is the share of a root-sum-square combination that each family
    contributes, and is the basis for identifying the dominant family.

    Raises ValueError for a malformed or duplicate-bearing contributor list.
    """
    normalised = _normalise_all(contributors)
    duplicates = check_duplicate_contributors(normalised)
    if duplicates:
        raise ValueError(
            "duplicate contributor id(s) present: " + ", ".join(duplicates)
        )
    totals = {family: 0.0 for family in UNCERTAINTY_FAMILIES}
    for item in normalised:
        totals[item["family"]] += item["fractional_uncertainty"] ** 2
    return totals


def combine_uncertainties(contributors, method="rss"):
    """
    Combine fractional uncertainties into a single combined value.

    method='rss'        root-sum-square: sqrt(sum(u_i^2)); use for
                        statistically independent contributors.
    method='worst_case' linear sum: sum(u_i); use when contributors are
                        correlated or a conservative bound is required.

    Returns the combined fractional uncertainty as a float.

    Raises ValueError for an unknown method, an empty/malformed contributor
    list, or duplicate contributor ids.
    """
    if method not in COMBINATION_METHODS:
        raise ValueError(
            f"Unknown combination method {method!r}. "
            f"Valid methods: {list(COMBINATION_METHODS)}"
        )
    normalised = _normalise_all(contributors)
    duplicates = check_duplicate_contributors(normalised)
    if duplicates:
        raise ValueError(
            "duplicate contributor id(s) present: " + ", ".join(duplicates)
        )

    fractions = [item["fractional_uncertainty"] for item in normalised]
    if method == "rss":
        return math.sqrt(sum(f * f for f in fractions))
    return sum(fractions)


def dominant_family(contributors):
    """
    Identify the family contributing most to the combined uncertainty.

    Selection is by the family's share of the sum of squared fractional
    uncertainties; ties are broken by the fixed order in UNCERTAINTY_FAMILIES
    so the result is deterministic. Returns None when every contributor has a
    zero fractional uncertainty (no dominant family).

    Raises ValueError for a malformed or duplicate-bearing contributor list.
    """
    totals = family_totals(contributors)
    if sum(totals.values()) <= _TOL:
        return None
    best = None
    best_value = -1.0
    for family in UNCERTAINTY_FAMILIES:
        if totals[family] > best_value + _TOL:
            best_value = totals[family]
            best = family
    return best


def apply_margin(nominal, combined_uncertainty, k):
    """
    Apply the k-sigma margin to a nominal shielded dose or fluence.

    margined = nominal * (1 + k * combined_uncertainty)

    nominal              — nominal computed dose or fluence (>= 0)
    combined_uncertainty — combined fractional uncertainty in [0, 1]
    k                    — margin multiplier; must be supplied explicitly and
                           be > 0. A zero or absent k would compare the bare
                           nominal value against the requirement.

    Ref: ECSS-E-ST-10C §6.4 — margin on the shielding calculation result.

    Raises ValueError for a negative nominal, a combined uncertainty outside
    [0, 1], or a missing/non-positive k.
    """
    nominal = _require_number(nominal, "nominal")
    combined_uncertainty = _require_number(
        combined_uncertainty, "combined_uncertainty"
    )
    if nominal < 0.0:
        raise ValueError(f"nominal must be non-negative; got {nominal}")
    if combined_uncertainty < 0.0 or combined_uncertainty > 1.0:
        raise ValueError(
            f"combined_uncertainty must be within [0, 1]; got {combined_uncertainty}"
        )
    if k is None:
        raise ValueError(
            "k must be supplied explicitly; a missing k is not equivalent to k = 0"
        )
    k = _require_number(k, "k")
    if k <= 0.0:
        raise ValueError(
            f"k must be positive (a zero margin applies no uncertainty "
            f"allowance); got {k}"
        )
    return nominal * (1.0 + k * combined_uncertainty)


def check_requirement(margined_value, requirement):
    """
    Compare the margined result against the shielding requirement.

    Returns a dict: margined, requirement, compliant (margined <= requirement)
    and exceedance_ratio (margined / requirement), all floats.

    Raises ValueError for a negative margined value or a non-positive
    requirement.
    """
    margined_value = _require_number(margined_value, "margined_value")
    requirement = _require_number(requirement, "requirement")
    if margined_value < 0.0:
        raise ValueError(f"margined_value must be non-negative; got {margined_value}")
    if requirement <= 0.0:
        raise ValueError(f"requirement must be positive; got {requirement}")
    return {
        "margined": margined_value,
        "requirement": requirement,
        "compliant": margined_value <= requirement + _TOL,
        "exceedance_ratio": margined_value / requirement,
    }


def assess_shielding_uncertainty(nominal, contributors, requirement, k, method="rss"):
    """
    Run the full §6.4 shielding-uncertainty assessment.

    nominal      — nominal computed shielded dose or fluence
    contributors — list of uncertainty contributor dicts (see
                   validate_contributor)
    requirement  — allowable shielding requirement for the same quantity
    k            — margin multiplier (explicit, > 0)
    method       — 'rss' (default) or 'worst_case'

    Returns a dict:
      nominal, method, k, combined_uncertainty, margined, requirement,
      compliant, exceedance_ratio, dominant_family, unsubstantiated
      (sorted ids with an unreviewed placeholder value), accepted.

    'accepted' is True only when the margined result is compliant AND every
    contributor value is substantiated — a compliant number backed by an
    unreviewed placeholder is not accepted.

    Raises ValueError for malformed contributors, for a duplicate contributor
    id (double counting must be resolved before the budget is combined), or
    for any other invalid numeric input.
    """
    normalised = _normalise_all(contributors)
    duplicate_ids = check_duplicate_contributors(normalised)
    if duplicate_ids:
        raise ValueError(
            "duplicate contributor id(s) present: " + ", ".join(duplicate_ids)
        )
    combined = combine_uncertainties(normalised, method)
    margined = apply_margin(nominal, combined, k)
    requirement_result = check_requirement(margined, requirement)

    unsubstantiated = sorted(
        item["id"] for item in normalised if not item["substantiated"]
    )

    return {
        "nominal": _require_number(nominal, "nominal"),
        "method": method,
        "k": _require_number(k, "k"),
        "combined_uncertainty": combined,
        "margined": margined,
        "requirement": requirement_result["requirement"],
        "compliant": requirement_result["compliant"],
        "exceedance_ratio": requirement_result["exceedance_ratio"],
        "dominant_family": dominant_family(normalised),
        "unsubstantiated": unsubstantiated,
        "accepted": requirement_result["compliant"] and not unsubstantiated,
    }
