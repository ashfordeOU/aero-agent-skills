#!/usr/bin/env python3
"""Secondary-arc verification with coupon samples (ECSS-E-ST-20-06C, 7.2.3.2).

Offline, deterministic, stdlib-only implementation of the clause 7.2.3.2
provisions on how array coupon samples are used in a secondary-arc
verification campaign: what a coupon has to reproduce from the flight
array, how the voltage/current test matrix is laid out around the expected
sustained-arc boundary, how many primary arcs each matrix point has to be
driven through, how a recorded arc event is categorized by its duration and
current, and when the campaign as a whole may be declared complete.

No standard text is reproduced; the thresholds are explicit, documented
campaign parameters.
"""

import math

# ---------------------------------------------------------------------------
# Coupon representativeness
# ---------------------------------------------------------------------------

MIN_COUPONS_PER_CAMPAIGN = 2
MIN_STRINGS_PER_COUPON = 2
MIN_CELLS_PER_STRING = 2

# Geometry a coupon may deviate from the flight article by, as a fraction.
DIMENSION_TOLERANCE_FRACTION = 0.05

NUMERIC_REPRESENTATIVE_FIELDS = ("conductor_gap_mm", "coverglass_thickness_um")
EXACT_REPRESENTATIVE_FIELDS = ("interconnect_type", "adhesive_type", "harness_routing")

# ---------------------------------------------------------------------------
# Test matrix
# ---------------------------------------------------------------------------

MAX_MATRIX_VOLTAGE_V = 400.0
MAX_MATRIX_CURRENT_A = 20.0
BASE_TRIGGERED_ARCS_PER_POINT = 10
NEAR_BOUNDARY_BAND_FRACTION = 0.15
NEAR_BOUNDARY_ARC_MULTIPLIER = 2

# ---------------------------------------------------------------------------
# Arc event categorization
# ---------------------------------------------------------------------------

ARC_DETECTION_FLOOR_A = 0.01
NON_SUSTAINED_DURATION_LIMIT_S = 1.0e-3
TEMPORARY_SUSTAINED_LIMIT_S = 1.0

# Representation tolerance: absorbs the few-ULP error of a difference of
# timestamps or a relative deviation. It never widens a campaign limit.
COMPARISON_TOLERANCE = 1e-9


def _almost_le(value, limit, tol=COMPARISON_TOLERANCE):
    """True when value is at or below limit, absorbing float representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=tol, abs_tol=tol)


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _positive(value, label):
    value = _finite(value, label)
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return value


def _non_negative(value, label):
    value = _finite(value, label)
    if value < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def _count(value, label, minimum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an int, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


# ---------------------------------------------------------------------------
# 1. Coupon validation and representativeness
# ---------------------------------------------------------------------------


def validate_coupon(coupon):
    """Normalize one coupon sample; raise ValueError on bad input."""
    if not isinstance(coupon, dict):
        raise ValueError("coupon must be a mapping, got %r" % (coupon,))
    coupon_id = coupon.get("id")
    if not isinstance(coupon_id, str) or not coupon_id.strip():
        raise ValueError("coupon needs a non-empty string 'id'")
    normalized = {
        "id": coupon_id.strip(),
        "strings": _count(
            coupon.get("strings"), "strings of '%s'" % coupon_id, MIN_STRINGS_PER_COUPON
        ),
        "cells_per_string": _count(
            coupon.get("cells_per_string"),
            "cells_per_string of '%s'" % coupon_id,
            MIN_CELLS_PER_STRING,
        ),
    }
    for field in NUMERIC_REPRESENTATIVE_FIELDS:
        normalized[field] = _positive(coupon.get(field), "%s of '%s'" % (field, coupon_id))
    for field in EXACT_REPRESENTATIVE_FIELDS:
        value = coupon.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s of '%s' must be a non-empty string" % (field, coupon_id))
        normalized[field] = value.strip().lower()
    return normalized


def coupon_representativeness_deviations(coupon, flight_reference):
    """Deviations of one coupon from the flight array it stands in for."""
    item = validate_coupon(coupon)
    reference = validate_coupon(flight_reference)
    deviations = []
    for field in NUMERIC_REPRESENTATIVE_FIELDS:
        relative = abs(item[field] - reference[field]) / reference[field]
        if not _almost_le(relative, DIMENSION_TOLERANCE_FRACTION):
            deviations.append(
                {
                    "field": field,
                    "coupon_value": item[field],
                    "reference_value": reference[field],
                    "relative_deviation": relative,
                }
            )
    for field in EXACT_REPRESENTATIVE_FIELDS:
        if item[field] != reference[field]:
            deviations.append(
                {
                    "field": field,
                    "coupon_value": item[field],
                    "reference_value": reference[field],
                    "relative_deviation": None,
                }
            )
    if item["strings"] < reference["strings"]:
        deviations.append(
            {
                "field": "strings",
                "coupon_value": item["strings"],
                "reference_value": reference["strings"],
                "relative_deviation": None,
            }
        )
    return deviations


# ---------------------------------------------------------------------------
# 2. Test matrix and arc budget
# ---------------------------------------------------------------------------


def build_test_matrix(voltage_points_v, current_points_a):
    """Full voltage x current grid of campaign test points."""
    for label, points, ceiling in (
        ("voltage_points_v", voltage_points_v, MAX_MATRIX_VOLTAGE_V),
        ("current_points_a", current_points_a, MAX_MATRIX_CURRENT_A),
    ):
        if not isinstance(points, (list, tuple)) or not points:
            raise ValueError("%s must be a non-empty sequence" % label)
        seen = set()
        for value in points:
            number = _positive(value, "%s entry" % label)
            if number > ceiling:
                raise ValueError("%s entry %r exceeds the campaign ceiling %r" % (label, number, ceiling))
            if number in seen:
                raise ValueError("%s contains the duplicate value %r" % (label, number))
            seen.add(number)
    matrix = []
    for voltage in voltage_points_v:
        for current in current_points_a:
            matrix.append({"voltage_v": float(voltage), "current_a": float(current)})
    return matrix


def required_triggered_arcs(point, expected_boundary_v, base=BASE_TRIGGERED_ARCS_PER_POINT):
    """Primary arcs a single matrix point has to be driven through."""
    if not isinstance(point, dict) or "voltage_v" not in point:
        raise ValueError("point must be a mapping with 'voltage_v', got %r" % (point,))
    voltage = _positive(point["voltage_v"], "point voltage_v")
    boundary = _positive(expected_boundary_v, "expected_boundary_v")
    count = _count(base, "base", 1)
    relative = abs(voltage - boundary) / boundary
    if _almost_le(relative, NEAR_BOUNDARY_BAND_FRACTION):
        return count * NEAR_BOUNDARY_ARC_MULTIPLIER
    return count


def campaign_arc_budget(matrix, expected_boundary_v, base=BASE_TRIGGERED_ARCS_PER_POINT):
    """Total primary arcs the campaign has to trigger across the matrix."""
    if not isinstance(matrix, (list, tuple)) or not matrix:
        raise ValueError("matrix must be a non-empty sequence of test points")
    total = 0
    for point in matrix:
        total += required_triggered_arcs(point, expected_boundary_v, base)
    return total


# ---------------------------------------------------------------------------
# 3. Arc event categorization
# ---------------------------------------------------------------------------


def arc_duration_from_timestamps(start_s, end_s):
    """Duration of a recorded arc event from its two timestamps."""
    start = _non_negative(start_s, "start_s")
    end = _non_negative(end_s, "end_s")
    if end < start:
        raise ValueError("end_s %r precedes start_s %r" % (end, start))
    return end - start


def categorize_arc_event(duration_s, current_a, detection_floor_a=ARC_DETECTION_FLOOR_A):
    """Categorize one recorded arc event by its duration and current."""
    duration = _non_negative(duration_s, "duration_s")
    current = _non_negative(current_a, "current_a")
    floor = _positive(detection_floor_a, "detection_floor_a")
    if current < floor:
        return "below-detection"
    if _almost_le(duration, NON_SUSTAINED_DURATION_LIMIT_S):
        return "non-sustained"
    if _almost_le(duration, TEMPORARY_SUSTAINED_LIMIT_S):
        return "temporary-sustained"
    return "permanent-sustained"


SUSTAINED_CATEGORIES = frozenset({"temporary-sustained", "permanent-sustained"})


def evaluate_point_result(point, events, expected_boundary_v, base=BASE_TRIGGERED_ARCS_PER_POINT):
    """Verdict for one matrix point from the arc events it recorded."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a sequence of arc event mappings")
    required = required_triggered_arcs(point, expected_boundary_v, base)
    counts = {}
    triggered = 0
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("arc event must be a mapping, got %r" % (event,))
        category = categorize_arc_event(
            event.get("duration_s", 0.0),
            event.get("current_a", 0.0),
            event.get("detection_floor_a", ARC_DETECTION_FLOOR_A),
        )
        counts[category] = counts.get(category, 0) + 1
        if category != "below-detection":
            triggered += 1
    sustained = sum(counts.get(name, 0) for name in SUSTAINED_CATEGORIES)
    return {
        "voltage_v": float(point["voltage_v"]),
        "required_arcs": required,
        "triggered_arcs": triggered,
        "category_counts": counts,
        "sustained_events": sustained,
        "arc_count_met": triggered >= required,
        "passed": triggered >= required and sustained == 0,
    }


# ---------------------------------------------------------------------------
# 4. Campaign-level verdict
# ---------------------------------------------------------------------------


def evaluate_campaign(coupons, flight_reference, matrix, results_by_point, expected_boundary_v):
    """Completeness and verdict of a whole secondary-arc coupon campaign."""
    if not isinstance(coupons, (list, tuple)):
        raise ValueError("coupons must be a sequence")
    if len(coupons) < MIN_COUPONS_PER_CAMPAIGN:
        raise ValueError(
            "campaign needs at least %d coupons, got %d"
            % (MIN_COUPONS_PER_CAMPAIGN, len(coupons))
        )
    if not isinstance(matrix, (list, tuple)) or not matrix:
        raise ValueError("matrix must be a non-empty sequence of test points")
    if not isinstance(results_by_point, (list, tuple)):
        raise ValueError("results_by_point must be a sequence of event lists")
    if len(results_by_point) != len(matrix):
        raise ValueError(
            "results_by_point has %d entries for %d matrix points"
            % (len(results_by_point), len(matrix))
        )
    coupon_findings = []
    for coupon in coupons:
        deviations = coupon_representativeness_deviations(coupon, flight_reference)
        coupon_findings.append(
            {
                "id": validate_coupon(coupon)["id"],
                "deviations": deviations,
                "representative": not deviations,
            }
        )
    point_findings = []
    for point, events in zip(matrix, results_by_point):
        point_findings.append(
            evaluate_point_result(point, events, expected_boundary_v)
        )
    non_representative = [f["id"] for f in coupon_findings if not f["representative"]]
    incomplete = [f["voltage_v"] for f in point_findings if not f["arc_count_met"]]
    sustained = [f["voltage_v"] for f in point_findings if f["sustained_events"] > 0]
    findings = []
    if non_representative:
        findings.append("coupon-not-representative")
    if incomplete:
        findings.append("arc-budget-not-reached")
    if sustained:
        findings.append("sustained-arc-recorded")
    return {
        "coupons": coupon_findings,
        "points": point_findings,
        "arc_budget": campaign_arc_budget(matrix, expected_boundary_v),
        "non_representative_coupons": non_representative,
        "incomplete_points_v": incomplete,
        "sustained_points_v": sustained,
        "findings": findings,
        "campaign_passed": not findings,
    }
