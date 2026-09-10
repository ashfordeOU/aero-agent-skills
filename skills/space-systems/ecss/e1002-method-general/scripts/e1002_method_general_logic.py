"""Deterministic, offline logic for ECSS-E-ST-10-02C SS 5.2.2.1
verification-method selection: choosing test, analysis, review-of-design,
or inspection (and combinations of them) for a requirement, with a stated
rationale and a precedence rule among the methods.

stdlib only. No network, no external state.
"""

from __future__ import annotations

# --- Canonical methods, in decreasing order of rigor/precedence -----------

TEST = "test"
ANALYSIS = "analysis"
REVIEW_OF_DESIGN = "review-of-design"
INSPECTION = "inspection"

ALL_METHODS = (TEST, ANALYSIS, REVIEW_OF_DESIGN, INSPECTION)

# Lower number = higher rigor = preferred method when more than one is
# eligible for a requirement's category.
PRECEDENCE = {
    TEST: 1,
    ANALYSIS: 2,
    REVIEW_OF_DESIGN: 3,
    INSPECTION: 4,
}

_METHOD_ALIASES = {
    "test": TEST,
    "analysis": ANALYSIS,
    "review-of-design": REVIEW_OF_DESIGN,
    "review of design": REVIEW_OF_DESIGN,
    "reviewofdesign": REVIEW_OF_DESIGN,
    "inspection": INSPECTION,
}

# --- Requirement categories and which methods may satisfy each one --------

CATEGORY_ELIGIBILITY = {
    "functional": (TEST, ANALYSIS),
    "performance": (TEST, ANALYSIS),
    "physical": (TEST, INSPECTION),
    "workmanship": (INSPECTION,),
    "design-process": (REVIEW_OF_DESIGN,),
    "safety-critical": (TEST, ANALYSIS),
}

SAFETY_CRITICAL_CATEGORY = "safety-critical"

RATIONALE_JUSTIFICATION_MIN_WORDS = 6


def normalize_method(name):
    """Map a method name to its canonical form, case/space-insensitive.

    Raises ValueError for anything not in ALL_METHODS.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("method name must be a non-empty string")
    key = name.strip().lower()
    if key not in _METHOD_ALIASES:
        raise ValueError(f"unrecognized verification method: {name!r}")
    return _METHOD_ALIASES[key]


def normalize_category(name):
    """Map a requirement category name to its canonical form.

    Raises ValueError for anything not in CATEGORY_ELIGIBILITY.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("category name must be a non-empty string")
    key = name.strip().lower()
    if key not in CATEGORY_ELIGIBILITY:
        raise ValueError(f"unrecognized requirement category: {name!r}")
    return key


def eligible_methods_for_category(category):
    """Return the tuple of methods that may verify a requirement of the
    given category (canonical category name required upstream errors)."""
    canon = normalize_category(category)
    return CATEGORY_ELIGIBILITY[canon]


def _word_count(text):
    return len(text.split())


def evaluate_requirement(req_id, category, methods, rationale):
    """Validate a single requirement's proposed verification method(s).

    Returns a dict:
      id, valid (bool), errors (list[str]), warnings (list[str]),
      valid_methods (list[str] canonical, precedence order),
      primary_method (str or None)

    Raises ValueError for structurally malformed input (unrecognized
    category/method name, or an empty methods list) -- those are caller
    bugs, not plan-quality findings. Plan-quality problems (ineligible
    method choice, missing rationale, an unjustified precedence
    deviation, a safety-critical requirement lacking test) are reported
    in the returned errors/warnings lists instead of raised.
    """
    canon_category = normalize_category(category)

    if methods is None or len(methods) == 0:
        raise ValueError(f"requirement {req_id!r} has no proposed method")

    canon_methods = [normalize_method(m) for m in methods]

    eligible = CATEGORY_ELIGIBILITY[canon_category]
    errors = []
    warnings = []

    ineligible = [m for m in canon_methods if m not in eligible]
    valid_methods = [m for m in canon_methods if m in eligible]
    # keep precedence order, de-duplicated
    valid_methods = sorted(set(valid_methods), key=lambda m: PRECEDENCE[m])

    if ineligible:
        errors.append(
            f"ineligible method(s) for category {canon_category!r}: {sorted(set(ineligible))}"
        )

    if not valid_methods:
        errors.append("no eligible method selected")

    rationale_text = rationale.strip() if isinstance(rationale, str) else ""
    if not rationale_text:
        errors.append("missing rationale")

    if canon_category == SAFETY_CRITICAL_CATEGORY and TEST not in valid_methods:
        errors.append("safety-critical requirement must include the test method")

    primary_method = valid_methods[0] if valid_methods else None

    if valid_methods:
        best_eligible_rank = min(PRECEDENCE[m] for m in eligible)
        best_selected_rank = PRECEDENCE[primary_method]
        if best_selected_rank > best_eligible_rank:
            skipped = [
                m for m in eligible
                if PRECEDENCE[m] < best_selected_rank and m not in valid_methods
            ]
            if skipped and rationale_text and _word_count(rationale_text) < RATIONALE_JUSTIFICATION_MIN_WORDS:
                warnings.append(
                    f"precedence deviation not justified: rationale too brief to "
                    f"explain skipping higher-rigor method(s) {skipped}"
                )

    return {
        "id": req_id,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "valid_methods": valid_methods,
        "primary_method": primary_method,
    }


def summarize_plan(requirements):
    """Roll up a verification plan (list of requirement dicts with keys
    id/category/methods/rationale) into per-method counts and a list of
    non-compliant requirement ids.

    Raises ValueError if the plan is empty.
    """
    if not requirements:
        raise ValueError("verification plan has no requirements to summarize")

    method_counts = {m: 0 for m in ALL_METHODS}
    non_compliant_ids = []
    warning_ids = []

    for req in requirements:
        result = evaluate_requirement(
            req["id"], req["category"], req["methods"], req["rationale"]
        )
        if result["primary_method"] is not None:
            method_counts[result["primary_method"]] += 1
        if not result["valid"]:
            non_compliant_ids.append(result["id"])
        if result["warnings"]:
            warning_ids.append(result["id"])

    return {
        "total": len(requirements),
        "method_counts": method_counts,
        "non_compliant_ids": non_compliant_ids,
        "warning_ids": warning_ids,
        "compliant": len(non_compliant_ids) == 0,
    }
