#!/usr/bin/env python3
"""Load points a current telemetry accuracy verification has to exercise.

Anchor: ECSS-E-ST-20-20C clause 5.2.8.7.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The accuracy claimed for a current telemetry channel is only verified
where it was measured. The clause fixes that the reporting accuracy is
demonstrated at load points spread across the range rather than at a
single convenient one, so the job here is to grade a proposed test
matrix against the points the range and the mission actually demand.

Required points come from two places:
    range points     declared fractions of the channel full scale,
                     including no-load and full load
    mission points   the load currents the equipment is declared to
                     operate at, which are required whether or not
                     they coincide with a range fraction

A proposed point covers a required point when it sits within a stated
tolerance, expressed as a fraction of full scale, of that required
value. The low end carries its own rule: the fixed part of the error
governs there, so a matrix with no point near no-load has not verified
the accuracy figure where it is hardest to meet.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

POINTS_COMPLETE = "verification-points-complete"
POINTS_INCOMPLETE = "verification-points-incomplete"

DEFAULT_VERIFICATION_POLICY = {
    "required_fractions": (0.0, 0.10, 0.25, 0.50, 0.75, 1.00),
    "match_tolerance_fraction": 0.02,
    "min_distinct_points": 5,
    "low_end_fraction": 0.10,
    "require_no_load_point": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A proposed point placed exactly on the tolerance edge, or exactly at
    full scale, can land a few units in the last place outside the bound
    once the fraction has been multiplied out. The tolerance itself is
    never widened; only the comparison absorbs the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_verification_policy(policy):
    """Check a verification-point policy is usable before it is applied."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    fractions = policy.get("required_fractions")
    if not isinstance(fractions, (list, tuple)) or not fractions:
        raise ValueError("policy required_fractions must be a non-empty sequence")
    for fraction in fractions:
        value = _require_non_negative("policy required_fractions entry", fraction)
        if value > 1.0:
            raise ValueError(
                "policy required_fractions entry %g is above full scale" % value
            )
    tolerance = _require_positive(
        "policy match_tolerance_fraction", policy.get("match_tolerance_fraction")
    )
    if tolerance >= 1.0:
        raise ValueError("policy match_tolerance_fraction of a whole range matches everything")
    minimum = policy.get("min_distinct_points")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("policy min_distinct_points must be a positive integer")
    low_end = _require_positive("policy low_end_fraction", policy.get("low_end_fraction"))
    if low_end > 1.0:
        raise ValueError("policy low_end_fraction is above full scale")
    if not isinstance(policy.get("require_no_load_point"), bool):
        raise ValueError("policy require_no_load_point must be a boolean")
    return policy


def _clean_points(name, points, full_scale_a, allow_empty=False):
    if points is None:
        points = []
    if not isinstance(points, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (name, points))
    if not points and not allow_empty:
        raise ValueError("%s is empty; there is nothing to assess" % name)
    cleaned = []
    for point in points:
        value = _require_non_negative("%s entry" % name, point)
        if value > full_scale_a and not math.isclose(
            value, full_scale_a, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            raise ValueError(
                "%s entry %g A is outside the channel range of %g A"
                % (name, value, full_scale_a)
            )
        cleaned.append(min(value, full_scale_a))
    return cleaned


def required_points_a(full_scale_a, operating_points_a=None, policy=DEFAULT_VERIFICATION_POLICY):
    """Load points the verification has to reach, range and mission together."""
    validate_verification_policy(policy)
    full_scale = _require_positive("full_scale_a", full_scale_a)
    tolerance = float(policy["match_tolerance_fraction"]) * full_scale
    required = []
    for fraction in policy["required_fractions"]:
        required.append(
            {"current_a": float(fraction) * full_scale, "origin": "range-fraction"}
        )
    for point in _clean_points(
        "operating_points_a", operating_points_a, full_scale, allow_empty=True
    ):
        if any(
            _at_most(abs(point - entry["current_a"]), tolerance) for entry in required
        ):
            continue
        required.append({"current_a": point, "origin": "mission-load-point"})
    required.sort(key=lambda entry: entry["current_a"])
    return required


def nearest_point_a(target_a, proposed_points_a):
    """Proposed point closest to a target, with its distance."""
    if not proposed_points_a:
        raise ValueError("proposed_points_a is empty; there is nothing to match against")
    target = _require_non_negative("target_a", target_a)
    best = min(proposed_points_a, key=lambda point: abs(point - target))
    return {"current_a": best, "distance_a": abs(best - target)}


def duplicate_points_a(proposed_points_a, full_scale_a, policy=DEFAULT_VERIFICATION_POLICY):
    """Proposed points sitting inside the match tolerance of an earlier one."""
    validate_verification_policy(policy)
    full_scale = _require_positive("full_scale_a", full_scale_a)
    tolerance = float(policy["match_tolerance_fraction"]) * full_scale
    points = _clean_points("proposed_points_a", proposed_points_a, full_scale)
    kept = []
    duplicates = []
    for point in sorted(points):
        if any(_at_most(abs(point - other), tolerance) for other in kept):
            duplicates.append(point)
        else:
            kept.append(point)
    return {"distinct_points_a": kept, "duplicate_points_a": duplicates}


def coverage_report(plan, policy=DEFAULT_VERIFICATION_POLICY):
    """Match every required point against the proposed matrix."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    validate_verification_policy(policy)
    full_scale = _require_positive("full_scale_a", plan.get("full_scale_a"))
    tolerance = float(policy["match_tolerance_fraction"]) * full_scale
    proposed = _clean_points("proposed_points_a", plan.get("proposed_points_a"), full_scale)
    required = required_points_a(full_scale, plan.get("operating_points_a"), policy)
    matched = []
    missing = []
    for entry in required:
        nearest = nearest_point_a(entry["current_a"], proposed)
        record = {
            "required_a": entry["current_a"],
            "origin": entry["origin"],
            "nearest_proposed_a": nearest["current_a"],
            "distance_a": nearest["distance_a"],
        }
        if _at_most(nearest["distance_a"], tolerance):
            matched.append(record)
        else:
            missing.append(record)
    return {
        "required": required,
        "matched": matched,
        "missing": missing,
        "coverage_fraction": float(len(matched)) / float(len(required)),
        "match_tolerance_a": tolerance,
    }


def low_end_points_a(plan, policy=DEFAULT_VERIFICATION_POLICY):
    """Proposed points above no-load but at or under the low-end fraction."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    validate_verification_policy(policy)
    full_scale = _require_positive("full_scale_a", plan.get("full_scale_a"))
    tolerance = float(policy["match_tolerance_fraction"]) * full_scale
    ceiling = float(policy["low_end_fraction"]) * full_scale
    proposed = _clean_points("proposed_points_a", plan.get("proposed_points_a"), full_scale)
    return [
        point
        for point in sorted(proposed)
        if not _at_most(point, tolerance) and _at_most(point, ceiling)
    ]


def assess_verification_points(plan, policy=DEFAULT_VERIFICATION_POLICY):
    """Full clause 5.2.8.7.1 grading of a proposed test matrix."""
    coverage = coverage_report(plan, policy)
    full_scale = float(plan["full_scale_a"])
    tolerance = coverage["match_tolerance_a"]
    grouped = duplicate_points_a(plan["proposed_points_a"], full_scale, policy)
    distinct = grouped["distinct_points_a"]
    low_end = low_end_points_a(plan, policy)
    findings = []
    duties = []
    for record in coverage["missing"]:
        findings.append(
            "no proposed point within %.6g A of the required %.6g A (%s); nearest is "
            "%.6g A"
            % (
                tolerance,
                record["required_a"],
                record["origin"],
                record["nearest_proposed_a"],
            )
        )
        duties.append("add a verification point at %.6g A" % record["required_a"])
    if grouped["duplicate_points_a"]:
        findings.append(
            "%d proposed point(s) fall inside the match tolerance of another and add "
            "no coverage" % len(grouped["duplicate_points_a"])
        )
    has_no_load = any(_at_most(point, tolerance) for point in distinct)
    if policy["require_no_load_point"] and not has_no_load:
        findings.append(
            "no no-load point; the fixed part of the error is never separated from "
            "the part that scales with the reading"
        )
        duties.append("add a no-load verification point")
    if not low_end:
        findings.append(
            "no loaded point at or below %.6g A; the accuracy figure stays unverified "
            "where the fixed error dominates it"
            % (float(policy["low_end_fraction"]) * full_scale)
        )
        duties.append(
            "add a loaded point at or below %.6g A"
            % (float(policy["low_end_fraction"]) * full_scale)
        )
    if len(distinct) < int(policy["min_distinct_points"]):
        findings.append(
            "only %d distinct points against a minimum of %d"
            % (len(distinct), int(policy["min_distinct_points"]))
        )
        duties.append(
            "raise the matrix to %d distinct points" % int(policy["min_distinct_points"])
        )
    complete = not coverage["missing"] and not findings
    return {
        "verdict": POINTS_COMPLETE if complete else POINTS_INCOMPLETE,
        "coverage_fraction": coverage["coverage_fraction"],
        "required_points_a": [entry["current_a"] for entry in coverage["required"]],
        "missing_points_a": [record["required_a"] for record in coverage["missing"]],
        "distinct_points_a": distinct,
        "duplicate_points_a": grouped["duplicate_points_a"],
        "low_end_points_a": low_end,
        "match_tolerance_a": tolerance,
        "findings": findings,
        "duties": duties,
    }
