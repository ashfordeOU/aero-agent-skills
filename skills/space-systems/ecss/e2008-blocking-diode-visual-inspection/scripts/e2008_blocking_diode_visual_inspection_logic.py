#!/usr/bin/env python3
"""Visual examination of planar blocking diodes for workmanship and surface defects.

Anchor: ECSS-E-ST-20-08C clause 12.6.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A visual examination looks like the cheapest step in a diode acceptance
flow and is the one most often recorded in a way that proves nothing.
Four things decide whether the record is worth anything.

A defect is judged against the part, not in millimetres. A 0.2 mm
scratch across a 1 mm die and the same scratch on a 4 mm die are
different defects, so every observed extent is referred to the smallest
die dimension before it meets a limit.

The limit belongs to the defect type and to where it sits. A scratch in
the active area and the same scratch on the periphery are not the same
finding, and a limit table indexed only by defect type quietly accepts
the worse of the two. A defect type and location with no declared limit
cannot be sentenced at all, and that is a referral, not an acceptance.

Magnification is asymmetric, and this is the part that gets inverted. A
defect seen below the required magnification is still a defect -- the
examination found it, and nothing about a weaker lens un-finds it. A
clean look below the required magnification establishes nothing, because
the defects the requirement exists to catch are exactly the ones that
lens cannot resolve. So a low-magnification examination can reject and
can refer, and it cannot accept.

A diode nobody examined is not a passing diode. The declared population
and the examined population are compared, and a diode whose examination
came back invalid sits with the ones never presented: both are
unestablished, and the lot stays open until each carries a real
disposition.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT = "accept"
REFER_FOR_REVIEW = "refer-for-review"
EXAMINATION_INVALID = "examination-invalid"
REJECT = "reject"

NO_LIMIT_DECLARED = "no-limit-declared-for-defect-and-location"
MAGNIFICATION_BELOW_REQUIREMENT = "magnification-below-requirement"
DEFECT_PAST_REJECT_LIMIT = "defect-past-reject-limit"
DEFECT_PAST_REVIEW_LIMIT = "defect-past-review-limit"

DEFECT_LIMITS_NOT_ESTABLISHED = "surface-defect-limits-not-established"
LOT_FAILS_VISUAL_INSPECTION = "lot-fails-visual-inspection"
LOT_INSPECTION_INCOMPLETE = "lot-visual-inspection-record-incomplete"
LOT_MEETS_INSPECTION_LIMITS = "lot-meets-visual-inspection-limits"

DEFAULT_INSPECTION_POLICY = {
    "required_magnification": 10.0,
    "max_rejected_fraction": 0.05,
    "marginal_headroom_fraction": 0.01,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_inspection_policy(policy):
    """Check the examination policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    magnification = _require_positive(
        "required_magnification", policy.get("required_magnification")
    )
    rejected = _require_non_negative(
        "max_rejected_fraction", policy.get("max_rejected_fraction")
    )
    if rejected > 1.0:
        raise ValueError(
            "max_rejected_fraction %g is above one; an allowance admitting a "
            "lot with no usable diode is not an acceptance policy" % rejected
        )
    headroom = _require_positive(
        "marginal_headroom_fraction", policy.get("marginal_headroom_fraction")
    )
    if headroom > 1.0:
        raise ValueError(
            "marginal_headroom_fraction %g is above one; every accepted diode "
            "would be flagged marginal" % headroom
        )
    return {
        "required_magnification": magnification,
        "max_rejected_fraction": rejected,
        "marginal_headroom_fraction": headroom,
    }


def validate_defect_limit(limit):
    """Read one declared limit pair for a defect type at a location."""
    if not isinstance(limit, dict):
        raise ValueError("limit must be a mapping, got %r" % (limit,))
    defect_type = _require_label("defect_type", limit.get("defect_type"))
    if not defect_type:
        raise ValueError("defect_type must not be blank")
    location = _require_label("location", limit.get("location"))
    if not location:
        raise ValueError("location must not be blank")
    refer = _require_positive(
        "refer_extent_fraction on %s/%s" % (defect_type, location),
        limit.get("refer_extent_fraction"),
    )
    reject = _require_positive(
        "max_extent_fraction on %s/%s" % (defect_type, location),
        limit.get("max_extent_fraction"),
    )
    if reject > 1.0:
        raise ValueError(
            "max_extent_fraction on %s/%s is %g; a defect longer than the die "
            "is not a limit" % (defect_type, location, reject)
        )
    if not _at_most(refer, reject):
        raise ValueError(
            "the review threshold %g on %s/%s sits above the reject threshold "
            "%g, which sentences nothing"
            % (refer, defect_type, location, reject)
        )
    return {
        "defect_type": defect_type,
        "location": location,
        "refer_extent_fraction": refer,
        "max_extent_fraction": reject,
    }


def validate_defect_limits(limits):
    """Index the declared limit table by defect type and location."""
    if not isinstance(limits, (list, tuple)):
        raise ValueError("limits must be a sequence of declared limit entries")
    table = {}
    for limit in limits:
        checked = validate_defect_limit(limit)
        key = (checked["defect_type"], checked["location"])
        if key in table:
            raise ValueError(
                "a limit for %s at %s is declared twice" % (key[0], key[1])
            )
        table[key] = checked
    return table


def validate_observation(observation):
    """Read one observed defect on a diode."""
    if not isinstance(observation, dict):
        raise ValueError("observation must be a mapping, got %r" % (observation,))
    defect_type = _require_label("defect_type", observation.get("defect_type"))
    if not defect_type:
        raise ValueError("defect_type must not be blank")
    location = _require_label("location", observation.get("location"))
    if not location:
        raise ValueError("location must not be blank")
    extent = _require_non_negative("extent_mm", observation.get("extent_mm"))
    return {"defect_type": defect_type, "location": location, "extent_mm": extent}


def validate_diode_record(diode):
    """Read one examined planar blocking diode."""
    if not isinstance(diode, dict):
        raise ValueError("diode must be a mapping, got %r" % (diode,))
    identifier = _require_label("diode id", diode.get("id"))
    if not identifier:
        raise ValueError("diode id must not be blank")
    dimension = _require_positive(
        "die_min_dimension_mm on %s" % identifier,
        diode.get("die_min_dimension_mm"),
    )
    magnification = _require_positive(
        "magnification on %s" % identifier, diode.get("magnification")
    )
    raw = diode.get("observations", [])
    if not isinstance(raw, (list, tuple)):
        raise ValueError(
            "observations on %s must be a sequence of observed defects"
            % identifier
        )
    observations = tuple(validate_observation(item) for item in raw)
    return {
        "id": identifier,
        "die_min_dimension_mm": dimension,
        "magnification": magnification,
        "observations": observations,
    }


def defect_extent_fraction(extent_mm, die_min_dimension_mm):
    """An observed extent referred to the smallest die dimension."""
    extent = _require_non_negative("extent_mm", extent_mm)
    dimension = _require_positive("die_min_dimension_mm", die_min_dimension_mm)
    return extent / dimension


def observation_disposition(observation, die_min_dimension_mm, limit_table):
    """Sentence one observed defect against the limit its type and place carry."""
    if not isinstance(limit_table, dict):
        raise ValueError("limit_table must be the indexed limit mapping")
    checked = validate_observation(observation)
    fraction = defect_extent_fraction(
        checked["extent_mm"], die_min_dimension_mm
    )
    key = (checked["defect_type"], checked["location"])
    limit = limit_table.get(key)
    if limit is None:
        return {
            "defect_type": checked["defect_type"],
            "location": checked["location"],
            "extent_fraction": fraction,
            "refer_extent_fraction": None,
            "max_extent_fraction": None,
            "headroom_fraction": None,
            "disposition": REFER_FOR_REVIEW,
            "reason": NO_LIMIT_DECLARED,
        }
    if not _at_most(fraction, limit["max_extent_fraction"]):
        disposition = REJECT
        reason = DEFECT_PAST_REJECT_LIMIT
    elif not _at_most(fraction, limit["refer_extent_fraction"]):
        disposition = REFER_FOR_REVIEW
        reason = DEFECT_PAST_REVIEW_LIMIT
    else:
        disposition = ACCEPT
        reason = None
    return {
        "defect_type": checked["defect_type"],
        "location": checked["location"],
        "extent_fraction": fraction,
        "refer_extent_fraction": limit["refer_extent_fraction"],
        "max_extent_fraction": limit["max_extent_fraction"],
        "headroom_fraction": limit["refer_extent_fraction"] - fraction,
        "disposition": disposition,
        "reason": reason,
    }


def diode_disposition(diode, limit_table, policy=DEFAULT_INSPECTION_POLICY):
    """Sentence one examined diode from every defect observed on it.

    A defect seen below the required magnification still stands; a clean
    look below it accepts nothing.
    """
    checked_policy = validate_inspection_policy(policy)
    record = validate_diode_record(diode)
    results = tuple(
        observation_disposition(
            observation, record["die_min_dimension_mm"], limit_table
        )
        for observation in record["observations"]
    )
    magnification_adequate = _at_least(
        record["magnification"], checked_policy["required_magnification"]
    )

    reasons = []
    worst = None
    smallest_headroom = None
    for result in results:
        if result["reason"] is not None and result["reason"] not in reasons:
            reasons.append(result["reason"])
        if worst is None or result["extent_fraction"] > worst["extent_fraction"]:
            worst = result
        if result["headroom_fraction"] is not None:
            if smallest_headroom is None or (
                result["headroom_fraction"] < smallest_headroom
            ):
                smallest_headroom = result["headroom_fraction"]

    if any(result["disposition"] == REJECT for result in results):
        disposition = REJECT
    elif any(result["disposition"] == REFER_FOR_REVIEW for result in results):
        disposition = REFER_FOR_REVIEW
    elif not magnification_adequate:
        disposition = EXAMINATION_INVALID
    else:
        disposition = ACCEPT

    if not magnification_adequate:
        reasons.append(MAGNIFICATION_BELOW_REQUIREMENT)

    return {
        "id": record["id"],
        "disposition": disposition,
        "magnification": record["magnification"],
        "magnification_adequate": magnification_adequate,
        "worst_defect_type": worst["defect_type"] if worst else None,
        "worst_defect_location": worst["location"] if worst else None,
        "worst_extent_fraction": worst["extent_fraction"] if worst else 0.0,
        "smallest_headroom_fraction": smallest_headroom,
        "observation_results": results,
        "reasons": tuple(reasons),
    }


def lot_dispositions(diodes, limit_table, policy=DEFAULT_INSPECTION_POLICY):
    """Sentence every examined diode, in record order."""
    if not isinstance(diodes, (list, tuple)):
        raise ValueError("diodes must be a sequence of examined records")
    if not diodes:
        raise ValueError(
            "no diode was examined, so there is nothing to sentence against the "
            "workmanship limits"
        )
    results = []
    seen = set()
    for diode in diodes:
        result = diode_disposition(diode, limit_table, policy)
        if result["id"] in seen:
            raise ValueError("duplicate diode id %r in the record" % result["id"])
        seen.add(result["id"])
        results.append(result)
    return tuple(results)


def rejected_fraction(dispositions):
    """Share of the examined diodes sentenced as rejected."""
    if not isinstance(dispositions, (list, tuple)) or not dispositions:
        raise ValueError("dispositions must be a non-empty sequence")
    rejected = sum(1 for item in dispositions if item["disposition"] == REJECT)
    return rejected / len(dispositions)


def unestablished_diodes(declared_ids, dispositions):
    """Declared diodes that carry no usable disposition.

    A diode never presented and a diode whose examination came back
    invalid sit together: neither has been shown to meet the limits.
    """
    if not isinstance(declared_ids, (list, tuple)):
        raise ValueError("declared_ids must be a sequence of declared diode ids")
    if not isinstance(dispositions, (list, tuple)):
        raise ValueError("dispositions must be a sequence")
    examined = {item["id"] for item in dispositions}
    missing = [
        _require_label("declared id", identifier)
        for identifier in declared_ids
        if _require_label("declared id", identifier) not in examined
    ]
    invalid = [
        item["id"]
        for item in dispositions
        if item["disposition"] == EXAMINATION_INVALID
    ]
    return tuple(sorted(set(missing) | set(invalid)))


def worst_diode(dispositions):
    """The examined diode carrying the largest defect relative to its die."""
    if not isinstance(dispositions, (list, tuple)) or not dispositions:
        raise ValueError("dispositions must be a non-empty sequence")
    return max(dispositions, key=lambda item: item["worst_extent_fraction"])


def marginal_diode_advisories(dispositions, policy=DEFAULT_INSPECTION_POLICY):
    """Name accepted diodes sitting just under a review threshold.

    These do not move the verdict -- an accepted diode is accepted -- but a
    diode that clears the review threshold by a hair will land the other
    side of it on the next reading of the same feature, and that is worth
    saying once here.
    """
    checked_policy = validate_inspection_policy(policy)
    if not isinstance(dispositions, (list, tuple)):
        raise ValueError("dispositions must be a sequence")
    band = checked_policy["marginal_headroom_fraction"]
    advisories = []
    for item in dispositions:
        if item["disposition"] != ACCEPT:
            continue
        headroom = item["smallest_headroom_fraction"]
        if headroom is None:
            continue
        if _at_most(headroom, band):
            advisories.append(
                "diode %s is accepted with a %s at %.4g per cent of its die, "
                "only %.4g per cent under the review threshold; the same "
                "feature read again could sit the other side of it"
                % (
                    item["id"],
                    item["worst_defect_type"],
                    item["worst_extent_fraction"] * 100.0,
                    headroom * 100.0,
                )
            )
    return tuple(advisories)


def assess_planar_blocking_diode_inspection(
    case, policy=DEFAULT_INSPECTION_POLICY
):
    """Full clause 12.6.1 visual examination decision for one diode lot."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_inspection_policy(policy)

    findings = []
    advisories = []
    result = {
        "diode_dispositions": (),
        "accepted_diodes": (),
        "referred_diodes": (),
        "rejected_diodes": (),
        "unestablished_diodes": (),
        "rejected_fraction": None,
        "worst_diode_id": None,
        "worst_extent_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    limits = case.get("defect_limits")
    if limits is None:
        findings.append(
            "no workmanship or surface defect limit is declared, so nothing "
            "observed on these diodes can be sentenced"
        )
        result["verdict"] = DEFECT_LIMITS_NOT_ESTABLISHED
        return result
    limit_table = validate_defect_limits(limits)
    if not limit_table:
        findings.append(
            "the declared limit table is empty; an examination with no limit "
            "behind it records observations and sentences nothing"
        )
        result["verdict"] = DEFECT_LIMITS_NOT_ESTABLISHED
        return result

    dispositions = lot_dispositions(case.get("diodes"), limit_table, policy)
    result["diode_dispositions"] = dispositions
    result["accepted_diodes"] = tuple(
        item["id"] for item in dispositions if item["disposition"] == ACCEPT
    )
    result["referred_diodes"] = tuple(
        item["id"]
        for item in dispositions
        if item["disposition"] == REFER_FOR_REVIEW
    )
    result["rejected_diodes"] = tuple(
        item["id"] for item in dispositions if item["disposition"] == REJECT
    )
    result["rejected_fraction"] = rejected_fraction(dispositions)

    declared = case.get("declared_diode_ids")
    if declared is None:
        declared = [item["id"] for item in dispositions]
    result["unestablished_diodes"] = unestablished_diodes(declared, dispositions)

    worst = worst_diode(dispositions)
    result["worst_diode_id"] = worst["id"]
    result["worst_extent_fraction"] = worst["worst_extent_fraction"]

    for item in dispositions:
        if item["disposition"] == ACCEPT:
            continue
        findings.append(
            "diode %s is sentenced %s on a %s at %s of %.4g per cent of its die "
            "(%s)"
            % (
                item["id"],
                item["disposition"],
                item["worst_defect_type"] or "no observed defect",
                item["worst_defect_location"] or "no recorded location",
                item["worst_extent_fraction"] * 100.0,
                ", ".join(item["reasons"]) or "no limit exceeded",
            )
        )

    advisories.extend(marginal_diode_advisories(dispositions, policy))

    if not _at_most(
        result["rejected_fraction"], float(policy["max_rejected_fraction"])
    ):
        findings.append(
            "%.4g per cent of the examined diodes are rejected, above the %.4g "
            "per cent the policy allows"
            % (
                result["rejected_fraction"] * 100.0,
                float(policy["max_rejected_fraction"]) * 100.0,
            )
        )
        result["verdict"] = LOT_FAILS_VISUAL_INSPECTION
        return result

    if result["unestablished_diodes"] or result["referred_diodes"]:
        if result["unestablished_diodes"]:
            findings.append(
                "%d declared diode(s) carry no usable disposition (%s); the lot "
                "stays open until each is examined at the required magnification"
                % (
                    len(result["unestablished_diodes"]),
                    ", ".join(result["unestablished_diodes"]),
                )
            )
        if result["referred_diodes"]:
            findings.append(
                "%d diode(s) are referred for review (%s); a referral is not a "
                "final disposition and the lot cannot close on one"
                % (
                    len(result["referred_diodes"]),
                    ", ".join(result["referred_diodes"]),
                )
            )
        result["verdict"] = LOT_INSPECTION_INCOMPLETE
        return result

    result["verdict"] = LOT_MEETS_INSPECTION_LIMITS
    return result
