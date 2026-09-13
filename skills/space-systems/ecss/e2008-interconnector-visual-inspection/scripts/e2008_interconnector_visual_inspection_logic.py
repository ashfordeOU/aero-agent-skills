#!/usr/bin/env python3
"""Defect allowances applied to interconnectors at the end of acceptance testing.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.10. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An interconnector carries current between adjacent cells over several
parallel legs and a set of welds, and it is the part that absorbs the
differential movement the array sees. The allowances in this clause are
applied when acceptance testing concludes, so each item is graded on
the state it is in at the end of the programme and, separately, on how
much of that state the testing itself produced.

Three quantities are computed per item:

    intact legs        how many current paths are left
    defect fractions   broken and cracked legs against the leg count,
                       lifted welds against the weld count
    induced defects    what appeared between the pre-test baseline and
                       the post-test state

An item can sit inside every allowance and still matter at coupon
level, because a defect the acceptance programme created is evidence
about the design or the process rather than about that one joint.

Dispositions are accept, refer-for-review and reject. The allowances
below are a declared coupon allowance set, not a physical constant; a
project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
INTERCONNECTOR_DISPOSITIONS = (ACCEPT, REFER, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

LEG_DEFECT_FIELDS = ("broken_legs", "cracked_legs")
WELD_DEFECT_FIELDS = ("lifted_welds",)

DEFAULT_INTERCONNECTOR_ALLOWANCES = {
    "max_broken_leg_fraction": 0.25,
    "max_cracked_leg_fraction": 0.50,
    "max_lifted_weld_fraction": 0.20,
    "min_intact_legs": 2,
    "max_affected_interconnector_fraction": 0.05,
    "max_test_induced_fraction": 0.02,
    "review_margin_factor": 2.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return float(value)


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    count = _require_count(name, value)
    if count == 0:
        raise ValueError("%s must be greater than zero" % name)
    return count


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An allowance is a product of a declared fraction and a counted
    number of legs, welds or items, so a count sitting exactly on the
    allowance can evaluate a few units in the last place above it. The
    allowance is never raised; only the comparison tolerates the
    representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_interconnector_allowances(allowances):
    """Check an interconnector allowance set is complete and self-consistent."""
    if not isinstance(allowances, dict):
        raise ValueError("allowances must be a mapping, got %r" % (allowances,))
    for key in (
        "max_broken_leg_fraction",
        "max_cracked_leg_fraction",
        "max_lifted_weld_fraction",
        "max_affected_interconnector_fraction",
        "max_test_induced_fraction",
    ):
        _require_fraction("allowances %s" % key, allowances.get(key))
    _require_positive_count(
        "allowances min_intact_legs", allowances.get("min_intact_legs")
    )
    factor = allowances.get("review_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "allowances review_margin_factor must be at least one, got %r" % (factor,)
        )
    if allowances["max_broken_leg_fraction"] > allowances["max_cracked_leg_fraction"]:
        raise ValueError(
            "allowances permit a larger fraction of broken legs than of cracked "
            "ones; a broken leg is the worse of the pair, so the two allowances "
            "contradict each other"
        )
    return allowances


def _read_state(record, prefix, leg_count, weld_count):
    state = {}
    for field in LEG_DEFECT_FIELDS:
        key = "%s_%s" % (prefix, field)
        count = _require_count(key, record.get(key, 0))
        if count > leg_count:
            raise ValueError(
                "%s is %d on an interconnector with %d legs" % (key, count, leg_count)
            )
        state[field] = count
    for field in WELD_DEFECT_FIELDS:
        key = "%s_%s" % (prefix, field)
        count = _require_count(key, record.get(key, 0))
        if count > weld_count:
            raise ValueError(
                "%s is %d on an interconnector with %d welds"
                % (key, count, weld_count)
            )
        state[field] = count
    if state["broken_legs"] + state["cracked_legs"] > leg_count:
        raise ValueError(
            "%s broken and cracked legs add up to more legs than the "
            "interconnector has" % prefix
        )
    return state


def interconnector_state(record, allowances=DEFAULT_INTERCONNECTOR_ALLOWANCES):
    """Pre-test and post-test condition of one interconnector.

    A leg that was broken before acceptance testing cannot be whole
    after it, so a post-test count below its baseline is refused as a
    record fault rather than read as a repair.
    """
    validate_interconnector_allowances(allowances)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    interconnector_id = record.get("interconnector_id")
    if not isinstance(interconnector_id, str) or not interconnector_id.strip():
        raise ValueError("each record needs a non-empty interconnector_id")
    leg_count = _require_positive_count(
        "leg_count on %s" % interconnector_id, record.get("leg_count")
    )
    weld_count = _require_positive_count(
        "weld_count on %s" % interconnector_id, record.get("weld_count")
    )
    if allowances["min_intact_legs"] > leg_count:
        raise ValueError(
            "the allowance asks for %d intact legs on %s, which has %d"
            % (allowances["min_intact_legs"], interconnector_id, leg_count)
        )
    pre = _read_state(record, "pre_test", leg_count, weld_count)
    post = _read_state(record, "post_test", leg_count, weld_count)
    induced = {}
    for field in LEG_DEFECT_FIELDS + WELD_DEFECT_FIELDS:
        if post[field] < pre[field]:
            raise ValueError(
                "post_test_%s fell from %d to %d on %s; a defect recorded before "
                "acceptance testing cannot be absent after it"
                % (field, pre[field], post[field], interconnector_id)
            )
        induced[field] = post[field] - pre[field]
    return {
        "interconnector_id": interconnector_id,
        "leg_count": leg_count,
        "weld_count": weld_count,
        "pre_test": pre,
        "post_test": post,
        "induced": induced,
        "intact_legs": leg_count - post["broken_legs"],
        "induced_total": sum(induced.values()),
        "post_test_total": sum(post.values()),
    }


def assess_interconnector(record, allowances=DEFAULT_INTERCONNECTOR_ALLOWANCES):
    """Apply the item allowances to one interconnector at end of testing."""
    validate_interconnector_allowances(allowances)
    state = interconnector_state(record, allowances)
    leg_count = state["leg_count"]
    weld_count = state["weld_count"]
    post = state["post_test"]

    fractions = {
        "broken_legs": post["broken_legs"] / float(leg_count),
        "cracked_legs": post["cracked_legs"] / float(leg_count),
        "lifted_welds": post["lifted_welds"] / float(weld_count),
    }
    findings = []
    dispositions = [ACCEPT]

    if state["intact_legs"] <= 0:
        dispositions.append(REJECT)
        findings.append(
            "every leg is broken; the interconnector is open and carries no "
            "current between the cells"
        )
    elif state["intact_legs"] < allowances["min_intact_legs"]:
        dispositions.append(REJECT)
        findings.append(
            "%d intact legs against the %d the allowance keeps in reserve"
            % (state["intact_legs"], allowances["min_intact_legs"])
        )

    limits = (
        ("broken_legs", "max_broken_leg_fraction", leg_count),
        ("cracked_legs", "max_cracked_leg_fraction", leg_count),
        ("lifted_welds", "max_lifted_weld_fraction", weld_count),
    )
    over_allowance = []
    for field, key, population in limits:
        allowed = allowances[key] * population
        if _at_most(post[field], allowed):
            continue
        over_allowance.append(field)
        if _at_most(post[field], allowed * allowances["review_margin_factor"]):
            dispositions.append(REFER)
            findings.append(
                "%d %s of %d, past the %.2f the allowance permits"
                % (post[field], field.replace("_", " "), population, allowed)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d %s of %d, past the review margin of %.2f"
                % (
                    post[field],
                    field.replace("_", " "),
                    population,
                    allowed * allowances["review_margin_factor"],
                )
            )

    if state["induced_total"] > 0:
        findings.append(
            "%d of the defects on this interconnector appeared during "
            "acceptance testing" % state["induced_total"]
        )

    return {
        "interconnector_id": state["interconnector_id"],
        "verdict": _worst(dispositions),
        "intact_legs": state["intact_legs"],
        "defect_fractions": fractions,
        "fields_over_allowance": over_allowance,
        "post_test_defect_total": state["post_test_total"],
        "induced_defect_total": state["induced_total"],
        "test_induced": state["induced_total"] > 0,
        "state": state,
        "findings": findings,
    }


def apply_acceptance_allowances(
    coupon, allowances=DEFAULT_INTERCONNECTOR_ALLOWANCES
):
    """Clause 5.5.3.2.10 allowances over the interconnectors of one coupon."""
    validate_interconnector_allowances(allowances)
    if not isinstance(coupon, dict):
        raise ValueError("coupon must be a mapping, got %r" % (coupon,))
    coupon_id = coupon.get("coupon_id")
    if not isinstance(coupon_id, str) or not coupon_id.strip():
        raise ValueError("coupon needs a non-empty coupon_id")
    declared = coupon.get("declared_interconnector_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_interconnector_count must be a positive integer, got %r"
            % (declared,)
        )
    records = coupon.get("interconnectors")
    if not isinstance(records, (list, tuple)):
        raise ValueError("interconnectors must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d interconnector records against a declared count of %d on %s"
            % (len(records), declared, coupon_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = assess_interconnector(record, allowances)
        marker = result["interconnector_id"]
        if marker in seen:
            raise ValueError(
                "duplicate interconnector id %r on coupon %s" % (marker, coupon_id)
            )
        seen.add(marker)
        screened.append(result)

    inspected = len(screened)
    findings = []
    dispositions = [result["verdict"] for result in screened] or [ACCEPT]
    counts = dict((state, 0) for state in INTERCONNECTOR_DISPOSITIONS)
    affected = 0
    induced_items = 0
    induced_defects = 0
    for result in screened:
        counts[result["verdict"]] += 1
        if result["post_test_defect_total"] > 0:
            affected += 1
        if result["test_induced"]:
            induced_items += 1
        induced_defects += result["induced_defect_total"]
        for finding in result["findings"]:
            findings.append("%s %s" % (result["interconnector_id"], finding))

    affected_allowed = allowances["max_affected_interconnector_fraction"] * inspected
    induced_allowed = allowances["max_test_induced_fraction"] * inspected
    factor = allowances["review_margin_factor"]

    if inspected and not _at_most(affected, affected_allowed):
        if _at_most(affected, affected_allowed * factor):
            dispositions.append(REFER)
            findings.append(
                "%d of %d interconnectors carry a defect at the end of "
                "acceptance testing, past the %.2f the coupon allowance permits"
                % (affected, inspected, affected_allowed)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d of %d interconnectors carry a defect at the end of "
                "acceptance testing, past the review margin of %.2f"
                % (affected, inspected, affected_allowed * factor)
            )
    if inspected and not _at_most(induced_items, induced_allowed):
        dispositions.append(REFER)
        findings.append(
            "%d of %d interconnectors picked up a defect during acceptance "
            "testing, past the %.2f the coupon allowance permits; the "
            "programme is producing them" % (induced_items, inspected, induced_allowed)
        )

    verdict = _worst(dispositions)
    missing = declared - inspected
    complete = missing == 0
    if not complete:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of %d interconnectors carry no end-of-test record; an allowance "
            "applied to a short set is applied to the wrong population"
            % (missing, declared)
        )
    return {
        "coupon_id": coupon_id,
        "verdict": verdict,
        "inspection_complete": complete,
        "missing_record_count": missing,
        "inspected_count": inspected,
        "disposition_counts": counts,
        "affected_count": affected,
        "affected_fraction": affected / float(inspected) if inspected else 0.0,
        "affected_allowance": affected_allowed,
        "remaining_affected_allowance": affected_allowed - affected,
        "test_induced_count": induced_items,
        "test_induced_defect_total": induced_defects,
        "test_induced_allowance": induced_allowed,
        "remaining_test_induced_allowance": induced_allowed - induced_items,
        "not_accepted_ids": [
            result["interconnector_id"]
            for result in screened
            if result["verdict"] != ACCEPT
        ],
        "interconnectors": screened,
        "findings": findings,
    }
