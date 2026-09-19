"""Revision of device data-sheet parameters from layout results.

Anchor: ECSS-E-ST-20-40C clause 5.6.6 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Each data-sheet parameter is bounded in one direction. An
   upper-bounded parameter (propagation delay, setup time, supply
   current) is worst at its largest extracted value; a lower-bounded
   one (maximum clock frequency, noise margin) is worst at its
   smallest.
2. The layout run extracts the parameter at several process-voltage-
   temperature corners. The worst of those, for the parameter's
   direction, is the value the data sheet is allowed to publish.
3. A published figure may be more conservative than the worst corner
   and never more favourable; a figure still equal to the pre-layout
   estimate while extracted results exist was never refreshed.
4. The worst-corner value is graded against the specification limit in
   the sense the direction implies, and the remaining margin is
   reported as a signed fraction of the limit so parameters in
   different units can be ranked together.

Stdlib only, offline, deterministic.
"""

import math

DIRECTION_UPPER_BOUND = "upper-bound"
DIRECTION_LOWER_BOUND = "lower-bound"
VALID_DIRECTIONS = (DIRECTION_UPPER_BOUND, DIRECTION_LOWER_BOUND)

# A worst-corner value and a published value are both the end of a
# float pipeline, so an intentionally equal pair can differ by a few
# units in the last place. This relative tolerance absorbs that without
# relaxing either the published figure or the specification limit.
RELATIVE_TOLERANCE = 1.0e-9

# A parameter extracted at fewer corners than this has a sample, not a
# worst case.
MIN_CORNERS_FOR_WORST_CASE = 2

FINDING_OPTIMISTIC_PUBLISHED_VALUE = "published-value-better-than-worst-corner"
FINDING_NOT_REFRESHED = "published-value-still-the-pre-layout-estimate"
FINDING_LIMIT_VIOLATED = "worst-corner-value-outside-specification-limit"
FINDING_SINGLE_CORNER = "extracted-at-one-corner-only"


def _finite(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def validate_parameter(parameter):
    """Validate one data-sheet parameter record and normalize it."""
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping")
    name = _text("parameter id", parameter.get("id"))
    direction = parameter.get("direction")
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            "parameter %s has unknown direction %r (expected one of %s)"
            % (name, direction, ", ".join(VALID_DIRECTIONS))
        )
    unit = _text("parameter %s unit" % name, parameter.get("unit"))
    limit = _finite("parameter %s specification_limit" % name, parameter.get("specification_limit"))
    if limit == 0.0:
        raise ValueError(
            "parameter %s has a zero specification limit, which carries no "
            "margin fraction" % name
        )
    corners = parameter.get("extracted_by_corner")
    if not isinstance(corners, dict) or not corners:
        raise ValueError("parameter %s needs a non-empty extracted_by_corner map" % name)
    normalized_corners = {}
    for corner, value in corners.items():
        corner_name = _text("parameter %s corner name" % name, corner)
        normalized_corners[corner_name] = _finite(
            "parameter %s corner %s" % (name, corner_name), value
        )
    published = _finite(
        "parameter %s published_value" % name, parameter.get("published_value")
    )
    estimate = parameter.get("pre_layout_estimate")
    if estimate is not None:
        estimate = _finite("parameter %s pre_layout_estimate" % name, estimate)
    return {
        "id": name,
        "direction": direction,
        "unit": unit,
        "specification_limit": limit,
        "extracted_by_corner": normalized_corners,
        "published_value": published,
        "pre_layout_estimate": estimate,
    }


def _close(a, b):
    scale = max(abs(a), abs(b), 1.0)
    return abs(a - b) <= RELATIVE_TOLERANCE * scale


def worst_corner(parameter):
    """Return (corner_name, value) for the worst extracted corner."""
    norm = validate_parameter(parameter)
    items = sorted(norm["extracted_by_corner"].items())
    if norm["direction"] == DIRECTION_UPPER_BOUND:
        return max(items, key=lambda item: (item[1], ))
    return min(items, key=lambda item: (item[1], ))


def margin_fraction(value, limit, direction):
    """Signed remaining margin as a fraction of the limit."""
    value = _finite("value", value)
    limit = _finite("limit", limit)
    if direction not in VALID_DIRECTIONS:
        raise ValueError("unknown direction %r" % (direction,))
    if limit == 0.0:
        raise ValueError("limit must be non-zero to form a margin fraction")
    if direction == DIRECTION_UPPER_BOUND:
        return (limit - value) / abs(limit)
    return (value - limit) / abs(limit)


def is_more_favourable(candidate, reference, direction):
    """True when candidate flatters the device relative to reference."""
    candidate = _finite("candidate", candidate)
    reference = _finite("reference", reference)
    if direction not in VALID_DIRECTIONS:
        raise ValueError("unknown direction %r" % (direction,))
    if _close(candidate, reference):
        return False
    if direction == DIRECTION_UPPER_BOUND:
        return candidate < reference
    return candidate > reference


def meets_limit(value, limit, direction):
    """True when the value satisfies the limit in its own sense."""
    value = _finite("value", value)
    limit = _finite("limit", limit)
    if direction not in VALID_DIRECTIONS:
        raise ValueError("unknown direction %r" % (direction,))
    if _close(value, limit):
        return True
    if direction == DIRECTION_UPPER_BOUND:
        return value < limit
    return value > limit


def assess_parameter(parameter):
    """Assess one data-sheet parameter against clause 5.6.6."""
    norm = validate_parameter(parameter)
    corner_name, corner_value = worst_corner(norm)
    findings = []
    if len(norm["extracted_by_corner"]) < MIN_CORNERS_FOR_WORST_CASE:
        findings.append(FINDING_SINGLE_CORNER)
    if is_more_favourable(norm["published_value"], corner_value, norm["direction"]):
        findings.append(FINDING_OPTIMISTIC_PUBLISHED_VALUE)
    estimate = norm["pre_layout_estimate"]
    if estimate is not None and _close(norm["published_value"], estimate):
        if not _close(estimate, corner_value):
            findings.append(FINDING_NOT_REFRESHED)
    if not meets_limit(corner_value, norm["specification_limit"], norm["direction"]):
        findings.append(FINDING_LIMIT_VIOLATED)
    return {
        "id": norm["id"],
        "unit": norm["unit"],
        "direction": norm["direction"],
        "worst_corner": corner_name,
        "worst_value": corner_value,
        "published_value": norm["published_value"],
        "specification_limit": norm["specification_limit"],
        "margin_fraction": margin_fraction(
            corner_value, norm["specification_limit"], norm["direction"]
        ),
        "findings": findings,
        "compliant": not findings,
    }


def assess_data_sheet_layout_update(parameters):
    """Assess the whole data-sheet revision against clause 5.6.6."""
    if not isinstance(parameters, list) or not parameters:
        raise ValueError("parameters must be a non-empty list")
    results = []
    seen = set()
    for parameter in parameters:
        result = assess_parameter(parameter)
        if result["id"] in seen:
            raise ValueError("duplicate parameter id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    tightest = min(results, key=lambda r: (r["margin_fraction"], r["id"]))
    return {
        "parameters": results,
        "non_compliant_ids": non_compliant,
        "tightest_parameter_id": tightest["id"],
        "tightest_margin_fraction": tightest["margin_fraction"],
        "revision_complete": not non_compliant,
    }
