"""Yield and ultimate margins of safety for a spacecraft mechanism structure.

Anchor: ECSS-E-ST-33-01 clauses 4.7.5.2.5 and 4.7.5.2.6, with the
factor-of-safety policy they inherit from the structural-factors
standard (paraphrased into an implementable procedure; no standard text
is reproduced).

Procedure implemented here:

1. Fix the factors of safety from the verification route and the
   material category. A structure qualified by a dedicated test carries
   the lightest factors, a protoflight article more, and a structure
   verified by analysis alone the heaviest. A special factor is added
   on top for a material or joint whose failure has no ductile warning.
2. Apply the factors to the design limit load, never to the allowable.
   The allowable stays the material property it was established as, so
   the same number can be reused across parts with different routes.
3. Take the yield margin and the ultimate margin separately. They use
   different allowables and different factors, and the smaller of the
   two is not predictable from the load alone.
4. Refuse to invent a yield margin for a material category that has no
   yield point. A brittle or fibre-dominated laminate fails without
   yielding, so its yield margin is reported as not applicable rather
   than as zero or as a copy of the ultimate margin.
5. Report the governing margin, the load case that drives it and the
   failure mode it belongs to, and grade the structure on the worst
   case rather than on an average.

Stdlib only, offline, deterministic.
"""

MODE_YIELD = "yield"
MODE_ULTIMATE = "ultimate"
FAILURE_MODES = (MODE_YIELD, MODE_ULTIMATE)

# Verification route of the structure, and the factors of safety it
# carries against yield and against ultimate.
FACTORS_BY_APPROACH = {
    "qualification-test": {MODE_YIELD: 1.10, MODE_ULTIMATE: 1.25},
    "protoflight-test": {MODE_YIELD: 1.25, MODE_ULTIMATE: 1.50},
    "analysis-only": {MODE_YIELD: 1.50, MODE_ULTIMATE: 2.00},
}
VALID_APPROACHES = tuple(sorted(FACTORS_BY_APPROACH))

# Additional factor carried by the material or joint category, applied
# on top of the route factors.
SPECIAL_FACTOR_BY_CATEGORY = {
    "metallic-ductile": 1.00,
    "metallic-brittle": 1.20,
    "fibre-composite": 1.20,
    "bonded-joint": 1.25,
    "glass-or-ceramic": 1.50,
}
VALID_CATEGORIES = tuple(sorted(SPECIAL_FACTOR_BY_CATEGORY))

# Categories that fail without a yield plateau, so a yield margin is a
# category error rather than a number.
CATEGORIES_WITHOUT_YIELD_POINT = (
    "fibre-composite",
    "glass-or-ceramic",
    "bonded-joint",
)

# A margin of safety is a quotient of floats minus one, so a case
# dimensioned exactly to its allowable can land a few units in the last
# place either side of zero. This tolerance groups those cases as zero
# rather than reporting a spurious negative.
MARGIN_TOLERANCE = 1.0e-12

VERDICT_POSITIVE = "positive"
VERDICT_ZERO = "zero"
VERDICT_NEGATIVE = "negative"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def _identifier(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def factors_of_safety(verification_approach, material_category):
    """Yield, ultimate and special factors for a route and a category."""
    if verification_approach not in FACTORS_BY_APPROACH:
        raise ValueError(
            "unknown verification_approach %r (expected one of %s)"
            % (verification_approach, ", ".join(VALID_APPROACHES))
        )
    if material_category not in SPECIAL_FACTOR_BY_CATEGORY:
        raise ValueError(
            "unknown material_category %r (expected one of %s)"
            % (material_category, ", ".join(VALID_CATEGORIES))
        )
    route = FACTORS_BY_APPROACH[verification_approach]
    return {
        MODE_YIELD: route[MODE_YIELD],
        MODE_ULTIMATE: route[MODE_ULTIMATE],
        "special": SPECIAL_FACTOR_BY_CATEGORY[material_category],
    }


def category_has_yield_point(material_category):
    """True when a yield margin is a meaningful quantity for the category."""
    if material_category not in SPECIAL_FACTOR_BY_CATEGORY:
        raise ValueError(
            "unknown material_category %r (expected one of %s)"
            % (material_category, ", ".join(VALID_CATEGORIES))
        )
    return material_category not in CATEGORIES_WITHOUT_YIELD_POINT


def margin_of_safety(allowable, design_limit_load, factor_of_safety, special_factor=1.0):
    """Margin of safety of an allowable against a factored design load."""
    allowable = _numeric("allowable", allowable, 0.0)
    if allowable <= 0.0:
        raise ValueError("allowable must be positive")
    load = _numeric("design_limit_load", design_limit_load, 0.0)
    if load <= 0.0:
        raise ValueError("design_limit_load must be positive")
    fos = _numeric("factor_of_safety", factor_of_safety, 1.0)
    special = _numeric("special_factor", special_factor, 1.0)
    return allowable / (load * fos * special) - 1.0


def margin_verdict(margin):
    """Group a margin as positive, zero within tolerance, or negative."""
    margin = _numeric("margin", margin)
    if margin > MARGIN_TOLERANCE:
        return VERDICT_POSITIVE
    if margin < -MARGIN_TOLERANCE:
        return VERDICT_NEGATIVE
    return VERDICT_ZERO


def validate_load_case(case):
    """Validate one margin load case and return a normalized copy."""
    if not isinstance(case, dict):
        raise ValueError("load case must be a mapping")
    case_id = _identifier("load case id", case.get("id"))
    load = _numeric(
        "load case %s design_limit_load" % case_id, case.get("design_limit_load"), 0.0
    )
    if load <= 0.0:
        raise ValueError("load case %s design_limit_load must be positive" % case_id)
    allowables = {}
    for mode in FAILURE_MODES:
        raw = case.get("%s_allowable" % mode)
        if raw is None:
            allowables[mode] = None
            continue
        value = _numeric("load case %s %s_allowable" % (case_id, mode), raw, 0.0)
        if value <= 0.0:
            raise ValueError(
                "load case %s %s_allowable must be positive" % (case_id, mode)
            )
        allowables[mode] = value
    return {
        "id": case_id,
        "design_limit_load": load,
        "yield_allowable": allowables[MODE_YIELD],
        "ultimate_allowable": allowables[MODE_ULTIMATE],
    }


def assess_load_case(case, verification_approach, material_category):
    """Yield and ultimate margins of one load case, with findings."""
    norm = validate_load_case(case)
    factors = factors_of_safety(verification_approach, material_category)
    has_yield = category_has_yield_point(material_category)
    margins = {}
    findings = []
    for mode in FAILURE_MODES:
        allowable = norm["%s_allowable" % mode]
        if mode == MODE_YIELD and not has_yield:
            margins[mode] = None
            if allowable is not None:
                findings.append("yield-allowable-declared-for-category-without-yield")
            continue
        if allowable is None:
            margins[mode] = None
            findings.append("%s-allowable-missing" % mode)
            continue
        margins[mode] = margin_of_safety(
            allowable, norm["design_limit_load"], factors[mode], factors["special"]
        )
        if margin_verdict(margins[mode]) == VERDICT_NEGATIVE:
            findings.append("negative-%s-margin" % mode)
    computed = dict((m, v) for m, v in margins.items() if v is not None)
    governing_mode = None
    governing_margin = None
    if computed:
        governing_mode = min(sorted(computed), key=lambda m: computed[m])
        governing_margin = computed[governing_mode]
    return {
        "id": norm["id"],
        "design_limit_load": norm["design_limit_load"],
        "factors": factors,
        "yield_margin": margins[MODE_YIELD],
        "ultimate_margin": margins[MODE_ULTIMATE],
        "yield_applicable": has_yield,
        "governing_mode": governing_mode,
        "governing_margin": governing_margin,
        "findings": findings,
        "compliant": not findings,
    }


def assess_margins(item):
    """Assess every load case of one mechanism structural item."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    item_id = _identifier("item id", item.get("id"))
    approach = item.get("verification_approach")
    category = item.get("material_category")
    factors_of_safety(approach, category)
    cases = item.get("load_cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("item %s needs a non-empty load_cases list" % item_id)
    results = []
    seen = set()
    for case in cases:
        result = assess_load_case(case, approach, category)
        if result["id"] in seen:
            raise ValueError("duplicate load case id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    rated = [r for r in results if r["governing_margin"] is not None]
    driving = None
    if rated:
        driving = min(rated, key=lambda r: r["governing_margin"])
    failing = [r["id"] for r in results if not r["compliant"]]
    zero_margin = [
        r["id"]
        for r in rated
        if margin_verdict(r["governing_margin"]) == VERDICT_ZERO
    ]
    return {
        "item_id": item_id,
        "verification_approach": approach,
        "material_category": category,
        "cases": results,
        "driving_case_id": None if driving is None else driving["id"],
        "driving_mode": None if driving is None else driving["governing_mode"],
        "governing_margin": None if driving is None else driving["governing_margin"],
        "zero_margin_case_ids": zero_margin,
        "non_compliant_case_ids": failing,
        "compliant": not failing,
    }
