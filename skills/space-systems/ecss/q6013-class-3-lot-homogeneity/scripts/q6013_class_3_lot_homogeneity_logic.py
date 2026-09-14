"""Batch uniformity before reduced sampling at the lowest assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.5.5 (the uniformity conditions a commercial
delivery has to meet before sampling tests are drawn from it at the lowest
assurance class). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Validate the delivered units and refuse a population whose two-digit years
   straddle a century rollover.
2. Stop outright on a decisive supply attribute carrying more than one value.
3. Score the weighted supply attributes as an exact integer ratio of matched
   weight to total weight.
4. Lower the score threshold only where a supplier batch declaration covers
   every unit in the delivery.
5. Take the date-code window in whole weeks and compare it with the limit.
6. Size the reduced sample by exact integer square root of the delivery and
   require the drawn units to reach both ends of the window.
"""

import math

__all__ = [
    "WEEKS_PER_YEAR",
    "DECISIVE_ATTRIBUTES",
    "DEFAULT_ATTRIBUTE_WEIGHTS",
    "DEFAULT_BATCH_POLICY",
    "UNIFORM_BATCH",
    "DECISIVE_ATTRIBUTE_CONFLICT",
    "DATE_CODE_WINDOW_EXCEEDED",
    "UNIFORMITY_BELOW_THRESHOLD",
    "SAMPLE_DOES_NOT_SPAN_WINDOW",
    "validate_attribute_weights",
    "validate_batch_policy",
    "parse_date_code",
    "week_index_of",
    "validate_unit",
    "validate_population",
    "decisive_attribute_conflicts",
    "uniformity_score",
    "validate_declaration",
    "declaration_covers_population",
    "date_code_window_weeks",
    "reduced_sample_size",
    "window_endpoint_coverage",
    "assess_batch_uniformity",
]

# A date code carries two digits of year and two of week. Week 53 is folded onto
# the first week of the following year, which keeps the window in integers.
WEEKS_PER_YEAR = 52

# Attributes that end the question rather than contribute to a score: two values
# in the box means two different articles.
DECISIVE_ATTRIBUTES = ("part_number", "package_code")

# The supply attributes a commercial delivery actually carries, and what each is
# worth to the uniformity judgement. Weights are integers so the score stays an
# exact ratio.
DEFAULT_ATTRIBUTE_WEIGHTS = {
    "manufacturer": 40,
    "country_of_origin": 25,
    "marking_style": 20,
    "distributor_reference": 15,
}

UNIFORM_BATCH = "uniform-batch"
DECISIVE_ATTRIBUTE_CONFLICT = "decisive-attribute-conflict"
DATE_CODE_WINDOW_EXCEEDED = "date-code-window-exceeded"
UNIFORMITY_BELOW_THRESHOLD = "uniformity-below-threshold"
SAMPLE_DOES_NOT_SPAN_WINDOW = "sample-does-not-span-window"

DEFAULT_BATCH_POLICY = {
    # Widest date-code window one batch may cover, in whole weeks.
    "max_date_code_window_weeks": 26,
    # Score thresholds as integer percentages of the total attribute weight.
    "uniformity_threshold_percent": 75,
    "declared_threshold_percent": 50,
    # Bounds on the reduced sample this class permits.
    "min_sample_units": 3,
    "max_sample_units": 20,
    # Whether the drawn units must reach both ends of the date-code window.
    "require_window_endpoints": True,
}


def validate_attribute_weights(weights=None):
    """Return a validated mapping of weighted supply attribute to integer weight."""
    if weights is None:
        return dict(DEFAULT_ATTRIBUTE_WEIGHTS)
    if not isinstance(weights, dict) or not weights:
        raise ValueError("attribute weights must be a non-empty mapping")
    validated = {}
    for name, weight in weights.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("each weighted attribute needs a non-empty name")
        if name.strip() in DECISIVE_ATTRIBUTES:
            raise ValueError(
                "%s is a decisive attribute and is never scored" % (name.strip(),)
            )
        if not isinstance(weight, int) or isinstance(weight, bool):
            raise ValueError("weight for %s must be an integer, got %r" % (name, weight))
        if weight <= 0:
            raise ValueError("weight for %s must be positive" % (name,))
        validated[name.strip()] = weight
    return validated


def validate_batch_policy(policy=None):
    """Return a complete batch sampling policy, defaults filled in."""
    if policy is None:
        return dict(DEFAULT_BATCH_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("batch policy must be a mapping")
    merged = dict(DEFAULT_BATCH_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_BATCH_POLICY:
            raise ValueError("unknown batch policy key %r" % (key,))
        merged[key] = value
    for key in ("max_date_code_window_weeks", "uniformity_threshold_percent",
                "declared_threshold_percent", "min_sample_units", "max_sample_units"):
        value = merged[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (key, value))
    if not isinstance(merged["require_window_endpoints"], bool):
        raise ValueError("require_window_endpoints must be a boolean")
    if merged["max_date_code_window_weeks"] < 0:
        raise ValueError("max_date_code_window_weeks must not be negative")
    for key in ("uniformity_threshold_percent", "declared_threshold_percent"):
        if not 0 <= merged[key] <= 100:
            raise ValueError("%s must lie in 0..100" % key)
    if merged["declared_threshold_percent"] > merged["uniformity_threshold_percent"]:
        raise ValueError(
            "the declared threshold is a relief and must not exceed the plain one"
        )
    if merged["min_sample_units"] <= 0:
        raise ValueError("min_sample_units must be positive")
    if merged["max_sample_units"] < merged["min_sample_units"]:
        raise ValueError("max_sample_units must not fall below min_sample_units")
    return merged


def parse_date_code(code):
    """Return the (year, week) pair a four-digit date code carries."""
    if not isinstance(code, str):
        raise ValueError("date_code must be a four-digit string, got %r" % (code,))
    text = code.strip()
    if len(text) != 4 or not text.isdigit():
        raise ValueError("date_code must read YYWW, got %r" % (code,))
    year = int(text[:2])
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("date_code week must lie in 01..53, got %r" % (code,))
    return (year, week)


def week_index_of(code):
    """Return a monotone integer week index for a date code."""
    year, week = parse_date_code(code)
    return year * WEEKS_PER_YEAR + (week - 1)


def validate_unit(unit, weights=None):
    """Return a normalised unit record, raising on a missing supply attribute."""
    if not isinstance(unit, dict):
        raise ValueError("each unit must be a mapping, got %r" % (type(unit).__name__,))
    scored = validate_attribute_weights(weights)
    identifier = unit.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("each unit needs a non-empty 'id'")
    record = {"id": identifier.strip()}
    for field in DECISIVE_ATTRIBUTES + tuple(sorted(scored)):
        value = unit.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "unit %s carries no '%s'; the uniformity judgement is assembled out "
                "of the supply attributes" % (record["id"], field)
            )
        record[field] = value.strip()
    code = unit.get("date_code")
    record["date_code"] = code.strip() if isinstance(code, str) else code
    record["week_index"] = week_index_of(record["date_code"])
    return record


def validate_population(units, weights=None):
    """Return the validated list of units making up the delivery."""
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("units must be a non-empty sequence of unit records")
    scored = validate_attribute_weights(weights)
    records = []
    seen = set()
    for unit in units:
        record = validate_unit(unit, scored)
        if record["id"] in seen:
            raise ValueError("duplicate unit id %r in the delivery" % (record["id"],))
        seen.add(record["id"])
        records.append(record)
    years = {parse_date_code(r["date_code"])[0] for r in records}
    if any(y >= 90 for y in years) and any(y <= 9 for y in years):
        raise ValueError(
            "date codes straddle a century rollover; the window cannot be taken "
            "from two-digit years alone"
        )
    return records


def decisive_attribute_conflicts(records):
    """Return each decisive attribute carrying more than one value, with its values."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    conflicts = {}
    for field in DECISIVE_ATTRIBUTES:
        values = sorted({record[field] for record in records})
        if len(values) > 1:
            conflicts[field] = values
    return conflicts


def uniformity_score(records, weights=None):
    """Return the matched weight, the total weight and the attributes that held."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    scored = validate_attribute_weights(weights)
    matched = 0
    total = 0
    holding = []
    varying = []
    for field in sorted(scored):
        weight = scored[field]
        total += weight
        values = {record[field] for record in records}
        if len(values) == 1:
            matched += weight
            holding.append(field)
        else:
            varying.append(field)
    return {
        "matched_weight": matched,
        "total_weight": total,
        "attributes_holding": holding,
        "attributes_varying": varying,
        "fraction": float(matched) / float(total),
    }


def validate_declaration(declaration):
    """Return a normalised supplier batch declaration, or None when absent."""
    if declaration is None:
        return None
    if not isinstance(declaration, dict):
        raise ValueError("a supplier batch declaration must be a mapping")
    reference = declaration.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("a supplier batch declaration needs a non-empty 'reference'")
    covered = declaration.get("covers")
    if not isinstance(covered, (list, tuple)) or not covered:
        raise ValueError(
            "declaration %s names no units; a declaration covering nothing is not "
            "relief" % (reference.strip(),)
        )
    names = []
    for name in covered:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("declaration %s names a blank unit" % (reference.strip(),))
        names.append(name.strip())
    return {"reference": reference.strip(), "covers": names}


def declaration_covers_population(declaration, records):
    """Return whether the declaration names every unit, and which it misses."""
    normalised = validate_declaration(declaration)
    if normalised is None:
        return {"covers": False, "missing": [record["id"] for record in records]}
    named = set(normalised["covers"])
    missing = sorted(record["id"] for record in records if record["id"] not in named)
    return {"covers": not missing, "missing": missing, "reference": normalised["reference"]}


def date_code_window_weeks(records):
    """Return the whole-week window between the oldest and newest date code."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("cannot take a date-code window of an empty delivery")
    indices = [record["week_index"] for record in records]
    return max(indices) - min(indices)


def reduced_sample_size(delivery_size, policy=None):
    """Return the reduced sample this class asks for, by exact integer root."""
    settings = validate_batch_policy(policy)
    if not isinstance(delivery_size, int) or isinstance(delivery_size, bool):
        raise ValueError("delivery_size must be an integer, got %r" % (delivery_size,))
    if delivery_size <= 0:
        raise ValueError("delivery_size must be positive, got %d" % delivery_size)
    # math.isqrt is exact integer arithmetic: a delivery sitting on a perfect
    # square gives the same count on every machine, which math.sqrt does not.
    root = math.isqrt(delivery_size)
    size = max(root, settings["min_sample_units"])
    size = min(size, settings["max_sample_units"])
    return min(size, delivery_size)


def window_endpoint_coverage(records, sample_ids):
    """Return how the drawn units sit against the ends of the date-code window."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    if not isinstance(sample_ids, (list, tuple)):
        raise ValueError("sample_ids must be a sequence of unit ids")
    by_id = {record["id"]: record for record in records}
    drawn = []
    seen = set()
    for identifier in sample_ids:
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("every drawn unit needs a non-empty id")
        name = identifier.strip()
        if name in seen:
            raise ValueError("unit %r was drawn twice" % (name,))
        if name not in by_id:
            raise ValueError("drawn unit %r is not part of the delivery" % (name,))
        seen.add(name)
        drawn.append(name)
    indices = [record["week_index"] for record in records]
    oldest = min(indices)
    newest = max(indices)
    drawn_indices = {by_id[name]["week_index"] for name in drawn}
    return {
        "drawn": drawn,
        "oldest_week_index": oldest,
        "newest_week_index": newest,
        "oldest_covered": oldest in drawn_indices,
        "newest_covered": newest in drawn_indices,
    }


def assess_batch_uniformity(case):
    """Run the clause 6.5.5 uniformity assessment over a commercial delivery.

    case keys: units (sequence of unit records), optional sample (unit ids
    already drawn), optional declaration, optional weights, optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "units" not in case:
        raise ValueError("case missing required key 'units'")
    settings = validate_batch_policy(case.get("policy"))
    weights = validate_attribute_weights(case.get("weights"))
    records = validate_population(case["units"], weights)
    delivery_size = len(records)

    findings = []
    conflicts = decisive_attribute_conflicts(records)
    for field, values in sorted(conflicts.items()):
        findings.append(
            "the delivery carries %d values of %s (%s); that is more than one article"
            % (len(values), field, ", ".join(values))
        )

    score = uniformity_score(records, weights)
    coverage = declaration_covers_population(case.get("declaration"), records)
    relief = bool(coverage["covers"])
    threshold = (settings["declared_threshold_percent"] if relief
                 else settings["uniformity_threshold_percent"])
    if case.get("declaration") is not None and not relief:
        findings.append(
            "the supplier batch declaration misses %d unit(s); it is evidence about "
            "a different population" % (len(coverage["missing"]),)
        )
    # Integer comparison against the threshold: a delivery landing exactly on the
    # threshold is admitted, and admitted identically everywhere.
    score_met = score["matched_weight"] * 100 >= threshold * score["total_weight"]
    if not score_met:
        findings.append(
            "uniformity weight %d of %d falls below the %d per cent threshold; %s vary"
            % (score["matched_weight"], score["total_weight"], threshold,
               ", ".join(score["attributes_varying"]) or "no attributes")
        )

    window = date_code_window_weeks(records)
    window_exceeded = window > settings["max_date_code_window_weeks"]
    if window_exceeded:
        findings.append(
            "the delivery spans %d weeks of date code against the %d week limit"
            % (window, settings["max_date_code_window_weeks"])
        )

    required = reduced_sample_size(delivery_size, settings)
    endpoints = window_endpoint_coverage(records, case.get("sample") or [])
    drawn = endpoints["drawn"]
    undersized = len(drawn) < required
    if undersized:
        findings.append(
            "%d units were drawn against the %d this delivery size requires"
            % (len(drawn), required)
        )
    endpoints_missed = []
    if settings["require_window_endpoints"] and drawn:
        if not endpoints["oldest_covered"]:
            endpoints_missed.append("oldest")
        if not endpoints["newest_covered"]:
            endpoints_missed.append("newest")
        for end in endpoints_missed:
            findings.append(
                "no drawn unit sits at the %s date code; that end of the window is "
                "untested" % (end,)
            )

    if conflicts:
        verdict = DECISIVE_ATTRIBUTE_CONFLICT
    elif window_exceeded:
        verdict = DATE_CODE_WINDOW_EXCEEDED
    elif not score_met:
        verdict = UNIFORMITY_BELOW_THRESHOLD
    elif undersized or endpoints_missed:
        verdict = SAMPLE_DOES_NOT_SPAN_WINDOW
    else:
        verdict = UNIFORM_BATCH

    return {
        "verdict": verdict,
        "delivery_size": delivery_size,
        "decisive_conflicts": conflicts,
        "uniformity_matched_weight": score["matched_weight"],
        "uniformity_total_weight": score["total_weight"],
        "uniformity_fraction": score["fraction"],
        "attributes_holding": score["attributes_holding"],
        "attributes_varying": score["attributes_varying"],
        "declaration_relief_applied": relief,
        "declaration_missing_units": coverage["missing"] if not relief else [],
        "threshold_percent": threshold,
        "date_code_window_weeks": window,
        "max_date_code_window_weeks": settings["max_date_code_window_weeks"],
        "required_sample_size": required,
        "sample_size": len(drawn),
        "window_endpoints_missed": endpoints_missed,
        "uniform": verdict == UNIFORM_BATCH,
        "findings": findings,
    }
