#!/usr/bin/env python3
"""Mechanical property verification from witness coupons of an additive build.

Anchor: ECSS-Q-ST-70-80 quality clause on verifying the mechanical properties
of additively manufactured material, build by build and batch by batch. The
procedure below is a paraphrase into implementable steps; no standard text is
reproduced.

What the clause actually decides
--------------------------------
The part is not tested; coupons built beside it are, and the coupons are
evidence only while they share what made the part what it is. Four things
decide the batch:

provenance     a coupon is evidence for this build and this furnace lot, not
               for a similar one. A coupon from another build or another
               heat-treatment lot is excluded and named, not averaged in.
coverage       the build direction is the weak direction. A population that
               samples only the in-plane orientations cannot see the
               property that governs the part.
minima         every coupon is graded against the minimum, not the mean of
               the population, because the mean hides the corner of the
               plate that ran cold.
anisotropy     the ratio of the weakest orientation mean to the strongest is
               a property of the process, and a collapse in it is a process
               finding even when every coupon is above its minimum.

The verdict is the worst of the four and the driving property is named.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Build orientations of a tensile coupon: two in-plane and the vertical one
# along the build direction, which is the weak direction of the process.
ORIENTATIONS = ("xy", "xz", "zx")
BUILD_DIRECTION_ORIENTATION = "zx"

PROPERTIES = ("uts_mpa", "ys_mpa", "elongation_pct")

VERDICT_ACCEPT = "accept"
VERDICT_REVIEW = "review"
VERDICT_REJECT = "reject"

_VERDICT_RANK = {VERDICT_ACCEPT: 0, VERDICT_REVIEW: 1, VERDICT_REJECT: 2}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

DEFAULT_MIN_PER_ORIENTATION = 3


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(verdicts):
    worst = VERDICT_ACCEPT
    for verdict in verdicts:
        if _VERDICT_RANK[verdict] > _VERDICT_RANK[worst]:
            worst = verdict
    return worst


def validate_coupon(coupon):
    """Return one witness coupon record with its properties as floats."""
    if not isinstance(coupon, dict):
        raise ValueError("coupon must be a mapping, got %r" % (coupon,))
    identifier = coupon.get("id", "coupon")
    orientation = _require_choice(
        "coupon %s orientation" % identifier, coupon.get("orientation"), ORIENTATIONS
    )
    record = {
        "id": identifier,
        "orientation": orientation,
        "build_id": coupon.get("build_id"),
        "heat_treat_lot": coupon.get("heat_treat_lot"),
    }
    for name in PROPERTIES:
        record[name] = _require_positive("coupon %s %s" % (identifier, name),
                                         coupon.get(name))
    return record


def select_witness_coupons(coupons, build_id, heat_treat_lot):
    """Split coupons into evidence for this build and lot, and everything else.

    A coupon built on another plate, or taken through another furnace lot, is
    evidence about that build. It is excluded by name rather than averaged in.
    """
    if not isinstance(coupons, (list, tuple)) or not coupons:
        raise ValueError("coupons must be a non-empty sequence of coupon records")
    accepted = []
    excluded = []
    for coupon in coupons:
        record = validate_coupon(coupon)
        if record["build_id"] != build_id:
            excluded.append(
                {
                    "id": record["id"],
                    "reason": "built on %r, not on %r" % (record["build_id"], build_id),
                }
            )
        elif record["heat_treat_lot"] != heat_treat_lot:
            excluded.append(
                {
                    "id": record["id"],
                    "reason": "heat-treated in lot %r, not in %r"
                    % (record["heat_treat_lot"], heat_treat_lot),
                }
            )
        else:
            accepted.append(record)
    if not accepted:
        raise ValueError(
            "no coupon belongs to build %r and lot %r; the batch has no "
            "property evidence of its own" % (build_id, heat_treat_lot)
        )
    return {"accepted": accepted, "excluded": excluded}


def orientation_coverage(records, required_orientations=ORIENTATIONS,
                         min_per_orientation=DEFAULT_MIN_PER_ORIENTATION):
    """Grade how well the coupon population samples the required orientations."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    if not isinstance(required_orientations, (list, tuple)) or not required_orientations:
        raise ValueError("required_orientations must be a non-empty sequence")
    minimum = _require_count("min_per_orientation", min_per_orientation, minimum=1)
    counts = {}
    for orientation in required_orientations:
        _require_choice("required orientation", orientation, ORIENTATIONS)
        counts[orientation] = 0
    for record in records:
        orientation = record["orientation"]
        if orientation in counts:
            counts[orientation] += 1
    findings = []
    verdicts = [VERDICT_ACCEPT]
    for orientation in required_orientations:
        if counts[orientation] == 0:
            verdicts.append(VERDICT_REJECT)
            severity = "no coupon"
            if orientation == BUILD_DIRECTION_ORIENTATION:
                severity = "no build-direction coupon"
            findings.append(
                "%s in the %s orientation; that direction is unverified"
                % (severity, orientation)
            )
        elif counts[orientation] < minimum:
            verdicts.append(VERDICT_REVIEW)
            findings.append(
                "%d coupon(s) in the %s orientation against the %d expected"
                % (counts[orientation], orientation, minimum)
            )
    return {
        "counts": counts,
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def grade_coupon(record, minima):
    """Grade one coupon against the minimum of every declared property."""
    if not isinstance(minima, dict) or not minima:
        raise ValueError("minima must map a property name to its minimum")
    findings = []
    verdicts = [VERDICT_ACCEPT]
    for name, limit in minima.items():
        if name not in PROPERTIES:
            raise ValueError(
                "%r is not a graded property; expected one of %s"
                % (name, ", ".join(PROPERTIES))
            )
        bound = _require_positive("minimum %s" % name, limit)
        value = record[name]
        if not _at_least(value, bound):
            verdicts.append(VERDICT_REJECT)
            findings.append(
                "coupon %s (%s) %s %.1f is below the %.1f minimum"
                % (record["id"], record["orientation"], name, value, bound)
            )
    return {
        "id": record["id"],
        "orientation": record["orientation"],
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def property_statistics(values):
    """Count, mean, extremes and sample standard deviation of one property."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence")
    numbers = [_require_number("value %d" % index, value)
               for index, value in enumerate(values)]
    count = len(numbers)
    mean = sum(numbers) / count
    if count > 1:
        variance = sum((value - mean) ** 2 for value in numbers) / (count - 1)
        deviation = math.sqrt(variance)
    else:
        deviation = 0.0
    return {
        "count": count,
        "mean": mean,
        "minimum": min(numbers),
        "maximum": max(numbers),
        "std_dev": deviation,
    }


def orientation_means(records, property_name):
    """Mean of one property per build orientation present in the population."""
    if property_name not in PROPERTIES:
        raise ValueError(
            "%r is not a graded property; expected one of %s"
            % (property_name, ", ".join(PROPERTIES))
        )
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    grouped = {}
    for record in records:
        grouped.setdefault(record["orientation"], []).append(record[property_name])
    return {
        orientation: sum(values) / len(values)
        for orientation, values in grouped.items()
    }


def anisotropy_ratio(means, min_ratio):
    """Ratio of the weakest orientation mean to the strongest, graded."""
    if not isinstance(means, dict) or not means:
        raise ValueError("means must be a non-empty mapping of orientation to mean")
    floor = _require_positive("min_ratio", min_ratio)
    if floor > 1.0:
        raise ValueError("min_ratio must not exceed 1.0, got %r" % (min_ratio,))
    for orientation, value in means.items():
        _require_choice("orientation", orientation, ORIENTATIONS)
        _require_positive("mean for %s" % orientation, value)
    if len(means) < 2:
        return {
            "ratio": 1.0,
            "weakest": sorted(means)[0],
            "strongest": sorted(means)[0],
            "verdict": VERDICT_REVIEW,
            "findings": [
                "only the %s orientation is populated; no anisotropy ratio can "
                "be formed from one direction" % sorted(means)[0]
            ],
        }
    weakest = min(means, key=lambda key: means[key])
    strongest = max(means, key=lambda key: means[key])
    ratio = means[weakest] / means[strongest]
    findings = []
    acceptable = _at_least(ratio, floor)
    if not acceptable:
        findings.append(
            "the %s orientation holds %.3f of the %s mean, below the %.3f "
            "floor; the process anisotropy has moved"
            % (weakest, ratio, strongest, floor)
        )
    return {
        "ratio": ratio,
        "weakest": weakest,
        "strongest": strongest,
        "verdict": VERDICT_ACCEPT if acceptable else VERDICT_REJECT,
        "findings": findings,
    }


def assess_material_properties(case):
    """Full witness-coupon verdict for one build or batch."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    selection = select_witness_coupons(
        case.get("coupons"), case.get("build_id"), case.get("heat_treat_lot")
    )
    records = selection["accepted"]
    coverage = orientation_coverage(
        records,
        case.get("required_orientations", ORIENTATIONS),
        case.get("min_per_orientation", DEFAULT_MIN_PER_ORIENTATION),
    )
    minima = case.get("minima")
    graded = [grade_coupon(record, minima) for record in records]
    coupon_verdict = _worst([record["verdict"] for record in graded])
    statistics = {
        name: property_statistics([record[name] for record in records])
        for name in PROPERTIES
    }
    anisotropy = anisotropy_ratio(
        orientation_means(records, "uts_mpa"), case.get("min_anisotropy_ratio", 0.85)
    )
    parts = {
        "coupon-minima": {"verdict": coupon_verdict},
        "orientation-coverage": coverage,
        "anisotropy": anisotropy,
    }
    verdict = _worst(part["verdict"] for part in parts.values())
    driving = sorted(
        name
        for name, part in parts.items()
        if _VERDICT_RANK[part["verdict"]] == _VERDICT_RANK[verdict]
        and verdict != VERDICT_ACCEPT
    )
    findings = []
    for record in graded:
        findings.extend("coupon-minima: %s" % text for text in record["findings"])
    findings.extend("orientation-coverage: %s" % text for text in coverage["findings"])
    findings.extend("anisotropy: %s" % text for text in anisotropy["findings"])
    for item in selection["excluded"]:
        findings.append(
            "provenance: coupon %s excluded, %s" % (item["id"], item["reason"])
        )
    return {
        "verdict": verdict,
        "driving_properties": driving,
        "accepted_coupons": len(records),
        "excluded_coupons": selection["excluded"],
        "coupons": graded,
        "coverage": coverage,
        "statistics": statistics,
        "anisotropy": anisotropy,
        "findings": findings,
    }
