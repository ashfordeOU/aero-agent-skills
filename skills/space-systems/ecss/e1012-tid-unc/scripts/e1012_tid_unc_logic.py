"""
TID assessment uncertainty accounting logic — ECSS-E-ST-10-12C §7.8.

Implements, as deterministic offline engineering logic, the procedure the leaf
describes: every TID uncertainty source is assigned to one of four categories
(environment model, shielding geometry, test conditions, part-to-part
variability), each carries a multiplicative factor >= 1.0, the combined factor
is the product of the individual factors, the design TID is the mean
environment TID times that product, and the achieved Radiation Design Margin
(minimum lot tolerance / design TID) is checked against the required minimum.

No third-party dependencies — stdlib only. No network. Deterministic.
"""

# --- The four uncertainty source categories of §7.8 -----------------------
SOURCE_ENVIRONMENT_MODEL = "environment_model"
SOURCE_SHIELDING_GEOMETRY = "shielding_geometry"
SOURCE_TEST_CONDITIONS = "test_conditions"
SOURCE_PART_VARIABILITY = "part_variability"

# Fixed order: used for deterministic reporting.
UNCERTAINTY_SOURCES = (
    SOURCE_ENVIRONMENT_MODEL,
    SOURCE_SHIELDING_GEOMETRY,
    SOURCE_TEST_CONDITIONS,
    SOURCE_PART_VARIABILITY,
)

# Required minimum Radiation Design Margin for standard space-qualified parts.
DEFAULT_REQUIRED_RDM = 2.0

_SOURCE_ALIASES = {
    "environment": SOURCE_ENVIRONMENT_MODEL,
    "environment_model": SOURCE_ENVIRONMENT_MODEL,
    "env_model": SOURCE_ENVIRONMENT_MODEL,
    "orbit_model": SOURCE_ENVIRONMENT_MODEL,
    "shielding": SOURCE_SHIELDING_GEOMETRY,
    "shielding_geometry": SOURCE_SHIELDING_GEOMETRY,
    "geometry": SOURCE_SHIELDING_GEOMETRY,
    "test": SOURCE_TEST_CONDITIONS,
    "test_conditions": SOURCE_TEST_CONDITIONS,
    "dose_rate": SOURCE_TEST_CONDITIONS,
    "temperature": SOURCE_TEST_CONDITIONS,
    "part": SOURCE_PART_VARIABILITY,
    "part_variability": SOURCE_PART_VARIABILITY,
    "lot_variability": SOURCE_PART_VARIABILITY,
    "variability": SOURCE_PART_VARIABILITY,
    "part_to_part": SOURCE_PART_VARIABILITY,
}

# Numerical tolerance for exact-boundary comparisons.
_TOL = 1e-12


def _require_number(value, label):
    """Return value as float, rejecting booleans and non-numeric input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number; got {value!r}")
    return float(value)


def resolve_source_category(value):
    """
    Map an uncertainty source spelling to one canonical category name.

    Accepts the canonical names plus common engineering synonyms such as
    'orbit_model', 'geometry', 'dose_rate' and 'part_to_part'.

    Ref: ECSS-E-ST-10-12C §7.8 — TID uncertainty source categories.

    Raises ValueError when the category is missing, not a string, or cannot be
    mapped to exactly one of the four categories.
    """
    if not isinstance(value, str):
        raise ValueError(
            f"source category must be a string; got {value!r}. "
            f"Valid categories: {list(UNCERTAINTY_SOURCES)}"
        )
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in _SOURCE_ALIASES:
        raise ValueError(
            f"Unknown uncertainty source {value!r}. "
            f"Valid categories: {list(UNCERTAINTY_SOURCES)}"
        )
    return _SOURCE_ALIASES[key]


def validate_factor(factor, source=None):
    """
    Validate one multiplicative uncertainty factor.

    A factor must be a number >= 1.0. A factor below 1.0 would shrink the
    design dose and is a modelling error, not a conservative correction; it is
    rejected rather than silently accepted.

    Returns the factor as a float.

    Raises ValueError for a non-numeric or sub-unity factor.
    """
    label = "factor" if source is None else f"factor for source '{source}'"
    value = _require_number(factor, label)
    if value < 1.0 - _TOL:
        raise ValueError(
            f"{label} must be >= 1.0 (a factor below 1.0 is a modelling error); "
            f"got {value}"
        )
    return value


def _coerce_items(factors):
    """Normalise a mapping or pair-sequence into an ordered list of pairs."""
    if isinstance(factors, dict):
        items = list(factors.items())
    elif isinstance(factors, (list, tuple)):
        items = []
        for entry in factors:
            if isinstance(entry, (list, tuple)) and len(entry) == 2:
                items.append((entry[0], entry[1]))
            else:
                raise ValueError(
                    "each factor entry must be a (category, factor) pair; "
                    f"got {entry!r}"
                )
    else:
        raise ValueError(
            "factors must be a dict or a list of (category, factor) pairs; "
            f"got {type(factors).__name__}"
        )

    if not factors:
        raise ValueError(
            "factors must not be empty — a component with no uncertainty "
            "source recorded is not automatically compliant"
        )
    return items


def combine_uncertainty_factors(factors):
    """
    Compute the combined uncertainty factor as the product of the individual
    source factors.

    factors — a dict {category: factor} or a sequence of (category, factor)
              pairs. Every category must resolve to one of the four
              categories, every factor must be >= 1.0, and no category may be
              supplied twice.

    Returns the product as a float.

    Ref: ECSS-E-ST-10-12C §7.8 — combined uncertainty factor.

    Raises ValueError for an empty factor set, a malformed entry, a duplicate
    category, an unresolvable category, or a sub-unity factor.
    """
    items = _coerce_items(factors)
    combined = 1.0
    seen = set()
    for raw_category, raw_factor in items:
        category = resolve_source_category(raw_category)
        if category in seen:
            raise ValueError(f"uncertainty source '{category}' supplied more than once")
        seen.add(category)
        combined *= validate_factor(raw_factor, category)
    return combined


def compute_design_tid(mean_tid, factors):
    """
    Compute the design TID for one component.

    design TID = mean environment TID * combined uncertainty factor

    mean_tid — mean environment TID for the component (must be > 0, same
               material basis as the lot tolerance)
    factors  — uncertainty source factors (see combine_uncertainty_factors)

    Ref: ECSS-E-ST-10-12C §7.8 — design dose.

    Raises ValueError for a non-positive mean TID or invalid factors.
    """
    mean_tid = _require_number(mean_tid, "mean_tid")
    if mean_tid <= 0.0:
        raise ValueError(f"mean_tid must be positive; got {mean_tid}")
    return mean_tid * combine_uncertainty_factors(factors)


def compute_rdm(lot_tolerance, design_tid):
    """
    Compute the achieved Radiation Design Margin.

    RDM = minimum guaranteed lot tolerance / design TID

    Ref: ECSS-E-ST-10-12C §7.8 — design margin applied to the dose, i.e. the
    factor divides the dose, not the tolerance.

    Raises ValueError for a non-positive lot tolerance or design TID.
    """
    lot_tolerance = _require_number(lot_tolerance, "lot_tolerance")
    design_tid = _require_number(design_tid, "design_tid")
    if lot_tolerance <= 0.0:
        raise ValueError(f"lot_tolerance must be positive; got {lot_tolerance}")
    if design_tid <= 0.0:
        raise ValueError(f"design_tid must be positive; got {design_tid}")
    return lot_tolerance / design_tid


def check_rdm(achieved_rdm, required_min=DEFAULT_REQUIRED_RDM):
    """
    Compare the achieved RDM against the required minimum.

    Returns a dict: achieved_rdm, required_min, meets_minimum (achieved >=
    required) and borderline (achieved is equal to the required minimum within
    tolerance). A borderline result technically meets the requirement but
    leaves no room for later model refinement and is flagged separately.

    Raises ValueError for a negative achieved RDM or a non-positive required
    minimum.
    """
    achieved_rdm = _require_number(achieved_rdm, "achieved_rdm")
    required_min = _require_number(required_min, "required_min")
    if achieved_rdm < 0.0:
        raise ValueError(f"achieved_rdm must be non-negative; got {achieved_rdm}")
    if required_min <= 0.0:
        raise ValueError(f"required_min must be positive; got {required_min}")
    return {
        "achieved_rdm": achieved_rdm,
        "required_min": required_min,
        "meets_minimum": achieved_rdm >= required_min - _TOL,
        "borderline": abs(achieved_rdm - required_min) <= _TOL,
    }


def assess_component(name, mean_tid, lot_tolerance, factors, required_min=DEFAULT_REQUIRED_RDM):
    """
    Run the full §7.8 uncertainty assessment for one component.

    name          — non-empty component identifier
    mean_tid      — mean environment TID for the component (> 0)
    lot_tolerance — minimum guaranteed lot tolerance (> 0)
    factors       — dict {category: factor} or sequence of (category, factor)
                    pairs; must be non-empty
    required_min  — required minimum RDM (default 2.0)

    Returns a dict: name, mean_tid, combined_factor, design_tid,
    lot_tolerance, achieved_rdm, required_min, meets_minimum, borderline,
    status ('PASS' or 'FAIL'), categories (sorted canonical source names) and
    requires_justification (True when the combined factor is exactly 1.0, i.e.
    no residual uncertainty was declared for any source).

    Raises ValueError for a blank name or any invalid numeric/factor input.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"name must be a non-empty string; got {name!r}")

    items = _coerce_items(factors)
    combined_factor = combine_uncertainty_factors(items)
    categories = sorted({resolve_source_category(c) for c, _ in items})

    design_tid = compute_design_tid(mean_tid, items)
    achieved_rdm = compute_rdm(lot_tolerance, design_tid)
    verdict = check_rdm(achieved_rdm, required_min)

    return {
        "name": name.strip(),
        "mean_tid": _require_number(mean_tid, "mean_tid"),
        "combined_factor": combined_factor,
        "design_tid": design_tid,
        "lot_tolerance": _require_number(lot_tolerance, "lot_tolerance"),
        "achieved_rdm": achieved_rdm,
        "required_min": verdict["required_min"],
        "meets_minimum": verdict["meets_minimum"],
        "borderline": verdict["borderline"],
        "status": "PASS" if verdict["meets_minimum"] else "FAIL",
        "categories": categories,
        "requires_justification": abs(combined_factor - 1.0) <= _TOL,
    }


def assess_mission(components, required_min=DEFAULT_REQUIRED_RDM):
    """
    Assess every component in scope and aggregate the outcome.

    components — list of dicts, each with mandatory keys 'name', 'mean_tid',
                 'lot_tolerance' and 'factors'; an optional per-component
                 'required_min' overrides the mission-level default.

    Returns a dict: results (one entry per component), total, passed, failed,
    borderline_count, justification_required (list of component names whose
    combined factor is exactly 1.0) and all_pass (True only when every
    component meets its required minimum).

    Raises ValueError when components is not a list, when the list is empty,
    or when an entry is malformed.
    """
    if isinstance(components, (str, bytes)) or not isinstance(components, (list, tuple)):
        raise ValueError(
            "components must be a list of component dicts; "
            f"got {type(components).__name__}"
        )
    if not components:
        raise ValueError("components must not be empty — no TID assessment scope")

    results = []
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise ValueError(
                f"component at index {index} must be a dict; "
                f"got {type(component).__name__}"
            )
        for key in ("name", "mean_tid", "lot_tolerance", "factors"):
            if key not in component:
                raise ValueError(
                    f"component at index {index} is missing mandatory key '{key}'"
                )
        results.append(
            assess_component(
                component["name"],
                component["mean_tid"],
                component["lot_tolerance"],
                component["factors"],
                component.get("required_min", required_min),
            )
        )

    passed = sum(1 for r in results if r["meets_minimum"])
    return {
        "results": results,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "borderline_count": sum(1 for r in results if r["borderline"]),
        "justification_required": [
            r["name"] for r in results if r["requires_justification"]
        ],
        "all_pass": passed == len(results),
    }
