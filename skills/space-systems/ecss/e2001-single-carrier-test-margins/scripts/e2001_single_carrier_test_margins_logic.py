#!/usr/bin/env python3
"""Single-carrier multipactor test margins (ECSS-E-ST-20-01C clause 4.6.3.1).

Deterministic, offline, stdlib-only implementation of the procedure that sets
the test margin for a single-carrier multipactor verification campaign from the
type of the article under test (equipment level or component level) and its
multipactor design heritage, then checks a measured multipactor threshold
against the power level that margin demands.

The numeric policy table below is the default margin policy carried by this
leaf; a project may override it with its own table via the ``policy`` argument
of :func:`required_test_margin_db`. The clause is the anchor for the procedure,
not a reproduction of the standard's text.
"""

import math

# Representation-error absorption only. A margin computed as a ratio of powers
# in decibels can land a few units in the last place under an exactly compliant
# limit; this tolerance absorbs that without widening the engineering limit.
MARGIN_TOLERANCE_DB = 1e-9

HARDWARE_ALIASES = {
    "equipment": "equipment",
    "equipment-level": "equipment",
    "unit": "equipment",
    "unit-level": "equipment",
    "component": "component",
    "component-level": "component",
    "part": "component",
    "sub-assembly": "component",
    "subassembly": "component",
}

HERITAGE_ALIASES = {
    "recurrent": "recurrent",
    "recurring": "recurrent",
    "identical-build": "recurrent",
    "qualified-design": "recurrent",
    "modified": "modified",
    "modified-design": "modified",
    "derivative": "modified",
    "first-of-kind": "first-of-kind",
    "new-design": "first-of-kind",
    "new": "first-of-kind",
    "no-heritage": "first-of-kind",
}

# (hardware category, heritage category) -> base test margin in decibels.
BASE_TEST_MARGIN_DB = {
    ("equipment", "recurrent"): 3.0,
    ("equipment", "modified"): 4.0,
    ("equipment", "first-of-kind"): 6.0,
    ("component", "recurrent"): 4.0,
    ("component", "modified"): 5.0,
    ("component", "first-of-kind"): 6.0,
}

# Uplift applied when a single article carries the whole demonstration: one
# sample gives no evidence about build-to-build spread of the threshold.
SINGLE_ARTICLE_UPLIFT_DB = 1.0
# Uplift applied when the threshold is transposed from a test at a different
# frequency or gap rather than measured on the article itself.
EXTRAPOLATED_THRESHOLD_UPLIFT_DB = 1.0

REQUIRED_UNIT_KEYS = ("id", "hardware_category", "heritage", "max_operating_power_w")


def _check_positive_power(value, label):
    """Return ``value`` as a finite, strictly positive float in watts."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be strictly positive watts, got %r" % (label, value))
    return value


def normalize_hardware_category(value):
    """Map a free-form article type onto 'equipment' or 'component'."""
    if not isinstance(value, str):
        raise ValueError("hardware category must be a string, got %r" % (value,))
    key = value.strip().lower()
    if not key:
        raise ValueError("hardware category must not be empty")
    if key not in HARDWARE_ALIASES:
        raise ValueError(
            "unrecognized hardware category %r (known: %s)"
            % (value, ", ".join(sorted(set(HARDWARE_ALIASES.values()))))
        )
    return HARDWARE_ALIASES[key]


def normalize_heritage(value):
    """Map a free-form heritage statement onto a canonical heritage category."""
    if not isinstance(value, str):
        raise ValueError("heritage must be a string, got %r" % (value,))
    key = value.strip().lower()
    if not key:
        raise ValueError("heritage must not be empty")
    if key not in HERITAGE_ALIASES:
        raise ValueError(
            "unrecognized heritage %r (known: %s)"
            % (value, ", ".join(sorted(set(HERITAGE_ALIASES.values()))))
        )
    return HERITAGE_ALIASES[key]


def required_test_margin_db(
    hardware_category,
    heritage,
    articles_tested=1,
    threshold_extrapolated=False,
    policy=None,
):
    """Return the decibel margin the single-carrier campaign must demonstrate."""
    hw = normalize_hardware_category(hardware_category)
    her = normalize_heritage(heritage)
    if isinstance(articles_tested, bool) or not isinstance(articles_tested, int):
        raise ValueError("articles_tested must be an integer, got %r" % (articles_tested,))
    if articles_tested < 1:
        raise ValueError("articles_tested must be at least 1, got %d" % articles_tested)
    if not isinstance(threshold_extrapolated, bool):
        raise ValueError(
            "threshold_extrapolated must be a boolean, got %r" % (threshold_extrapolated,)
        )
    table = BASE_TEST_MARGIN_DB if policy is None else policy
    if not isinstance(table, dict):
        raise ValueError("policy must be a mapping of (category, heritage) to decibels")
    if (hw, her) not in table:
        raise ValueError("policy carries no entry for (%s, %s)" % (hw, her))
    base = table[(hw, her)]
    if isinstance(base, bool) or not isinstance(base, (int, float)):
        raise ValueError("policy entry for (%s, %s) must be a number" % (hw, her))
    base = float(base)
    if base < 0.0 or not math.isfinite(base):
        raise ValueError("policy entry for (%s, %s) must be a finite margin >= 0" % (hw, her))
    margin = base
    if articles_tested == 1:
        margin += SINGLE_ARTICLE_UPLIFT_DB
    if threshold_extrapolated:
        margin += EXTRAPOLATED_THRESHOLD_UPLIFT_DB
    return margin


def power_ratio_db(numerator_w, denominator_w):
    """Return the power ratio of two watt values expressed in decibels."""
    num = _check_positive_power(numerator_w, "numerator")
    den = _check_positive_power(denominator_w, "denominator")
    return 10.0 * math.log10(num / den)


def required_test_power_w(max_operating_power_w, margin_db):
    """Return the power level the multipactor test must actually apply."""
    peak = _check_positive_power(max_operating_power_w, "max_operating_power_w")
    if isinstance(margin_db, bool) or not isinstance(margin_db, (int, float)):
        raise ValueError("margin_db must be a number, got %r" % (margin_db,))
    margin = float(margin_db)
    if not math.isfinite(margin):
        raise ValueError("margin_db must be finite, got %r" % (margin_db,))
    if margin < 0.0:
        raise ValueError("margin_db must not be negative, got %r" % (margin_db,))
    return peak * (10.0 ** (margin / 10.0))


def achieved_margin_db(threshold_w, max_operating_power_w):
    """Return the margin a measured multipactor threshold actually delivers."""
    return power_ratio_db(threshold_w, max_operating_power_w)


def margin_is_met(achieved_db, required_db):
    """True when the achieved margin reaches the required one."""
    for label, value in (("achieved_db", achieved_db), ("required_db", required_db)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a number, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite, got %r" % (label, value))
    return float(achieved_db) >= float(required_db) - MARGIN_TOLERANCE_DB


def evaluate_unit(unit):
    """Evaluate one article: required margin, achieved margin, findings."""
    if not isinstance(unit, dict):
        raise ValueError("unit record must be a mapping, got %r" % (unit,))
    for key in REQUIRED_UNIT_KEYS:
        if key not in unit:
            raise ValueError("unit record missing required key %r" % (key,))
    identifier = unit["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("unit id must be a non-empty string, got %r" % (identifier,))
    hw = normalize_hardware_category(unit["hardware_category"])
    her = normalize_heritage(unit["heritage"])
    peak = _check_positive_power(unit["max_operating_power_w"], "max_operating_power_w")
    required = required_test_margin_db(
        hw,
        her,
        articles_tested=unit.get("articles_tested", 1),
        threshold_extrapolated=unit.get("threshold_extrapolated", False),
        policy=unit.get("policy"),
    )
    demand_w = required_test_power_w(peak, required)
    findings = []
    threshold = unit.get("measured_threshold_w")
    if threshold is None:
        findings.append("no measured multipactor threshold on record")
        achieved = None
        compliant = False
    else:
        threshold = _check_positive_power(threshold, "measured_threshold_w")
        achieved = achieved_margin_db(threshold, peak)
        compliant = margin_is_met(achieved, required)
        if not compliant:
            findings.append(
                "achieved margin %.3f dB is below the required %.3f dB"
                % (achieved, required)
            )
    return {
        "id": identifier.strip(),
        "hardware_category": hw,
        "heritage": her,
        "required_margin_db": required,
        "required_test_power_w": demand_w,
        "achieved_margin_db": achieved,
        "deficit_db": None if achieved is None else max(0.0, required - achieved),
        "compliant": compliant,
        "findings": findings,
    }


def assess_units(units):
    """Evaluate a campaign of articles, rejecting duplicates and empty input."""
    if not isinstance(units, (list, tuple)):
        raise ValueError("units must be a list of unit records")
    if len(units) == 0:
        raise ValueError("units must not be empty")
    seen = set()
    results = []
    for unit in units:
        result = evaluate_unit(unit)
        if result["id"] in seen:
            raise ValueError("duplicate unit id %r in campaign" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    return results


def summarize_assessment(results):
    """Aggregate per-article results into a campaign verdict."""
    if not isinstance(results, (list, tuple)) or len(results) == 0:
        raise ValueError("results must be a non-empty list")
    deficits = [r["deficit_db"] for r in results if r.get("deficit_db") is not None]
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    return {
        "articles": len(results),
        "compliant": len(results) - len(non_compliant),
        "non_compliant_ids": non_compliant,
        "worst_deficit_db": max(deficits) if deficits else 0.0,
        "campaign_compliant": not non_compliant,
    }
