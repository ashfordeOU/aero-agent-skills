#!/usr/bin/env python3
"""Overview of the solar cell assembly test programme.

Anchor: ECSS-E-ST-20-08C clause 6.1.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Qualifying a solar cell assembly (SCA) is not a qualification campaign
followed later by an acceptance campaign. The two run as one programme, and
several activities serve both ends at once, so the overview has to answer
three questions per declared activity:

    category    does the activity cover the obligation it owes -- an
                activity owed to both ends is not covered by running it
                for one of them
    specimen    does it run on the right article -- an acceptance
                obligation is discharged on a sample of the flight lot, a
                qualification obligation on a qualification coupon, and an
                activity owed to both needs both
    sample      does it run on enough articles for the category it serves

The programme is then rolled up twice: how much of the required activity
set is actually covered, and what share of the covered activities carries a
qualification obligation at all. The second number is what separates a
combined campaign from an acceptance sweep wearing a qualification label.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TEST_CATEGORIES = ("acceptance", "qualification", "acceptance-and-qualification")

SPECIMEN_KINDS = ("flight-lot-sample", "qualification-coupon")

REQUIRED_SCA_ACTIVITIES = {
    "sca-visual-inspection": "acceptance-and-qualification",
    "sca-electrical-performance-measurement": "acceptance-and-qualification",
    "sca-adherence-measurement": "acceptance-and-qualification",
    "sca-dimensional-measurement": "acceptance",
    "sca-thermal-cycling": "qualification",
    "sca-humidity-exposure": "qualification",
    "sca-electrostatic-discharge": "qualification",
}

ACTIVITY_COVERED = "activity-covered"
ACTIVITY_CATEGORY_SHORTFALL = "activity-category-shortfall"
ACTIVITY_SPECIMEN_MISMATCH = "activity-specimen-mismatch"
ACTIVITY_SAMPLE_SHORTFALL = "activity-sample-shortfall"

PROGRAMME_COMPLETE = "sca-programme-complete"
PROGRAMME_INCOMPLETE = "sca-programme-incomplete"

DEFAULT_SCA_TEST_POLICY = {
    "allow_category_above_requirement": True,
    "min_qualification_share": 0.50,
    "specimen_for_category": {
        "acceptance": ("flight-lot-sample",),
        "qualification": ("qualification-coupon",),
        "acceptance-and-qualification": ("flight-lot-sample", "qualification-coupon"),
    },
    "min_sample_count": {
        "acceptance": 3,
        "qualification": 5,
        "acceptance-and-qualification": 5,
    },
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A programme share is a ratio of two counts and the policy limit is a
    round fraction, so a programme meant to sit exactly on the limit can
    land a few units in the last place below it. The limit is never
    lowered; only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _obligations(category):
    """The ends a category discharges, as a set."""
    if category == "acceptance-and-qualification":
        return {"acceptance", "qualification"}
    return {category}


def validate_sca_test_policy(policy):
    """Check an SCA test programme policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag(
        "allow_category_above_requirement",
        policy.get("allow_category_above_requirement"),
    )
    _require_fraction("min_qualification_share", policy.get("min_qualification_share"))
    specimens = policy.get("specimen_for_category")
    if not isinstance(specimens, dict):
        raise ValueError("policy specimen_for_category must be a mapping")
    counts = policy.get("min_sample_count")
    if not isinstance(counts, dict):
        raise ValueError("policy min_sample_count must be a mapping")
    for category in TEST_CATEGORIES:
        if category not in specimens:
            raise ValueError(
                "policy specimen_for_category is missing category %s" % category
            )
        declared = specimens[category]
        if not isinstance(declared, (list, tuple)) or not declared:
            raise ValueError(
                "policy specimen_for_category[%s] must be a non-empty sequence"
                % category
            )
        for kind in declared:
            _require_choice(
                "policy specimen_for_category[%s]" % category, kind, SPECIMEN_KINDS
            )
        if category not in counts:
            raise ValueError("policy min_sample_count is missing category %s" % category)
        _require_count("policy min_sample_count[%s]" % category, counts[category], 1)
    return policy


def required_sca_activities():
    """The activity set an SCA programme owes, with the category of each."""
    return dict(REQUIRED_SCA_ACTIVITIES)


def required_category(activity):
    """Category the programme owes for one activity."""
    _require_choice("activity", activity, tuple(sorted(REQUIRED_SCA_ACTIVITIES)))
    return REQUIRED_SCA_ACTIVITIES[activity]


def resolve_category_coverage(
    activity, declared_category, policy=DEFAULT_SCA_TEST_POLICY
):
    """Does the declared category cover the obligation the activity owes."""
    validate_sca_test_policy(policy)
    required = required_category(activity)
    declared = _require_choice("declared category", declared_category, TEST_CATEGORIES)
    owed = _obligations(required)
    served = _obligations(declared)
    uncovered = sorted(owed - served)
    extra = sorted(served - owed)
    findings = []
    if uncovered:
        findings.append(
            "%s is declared %s and leaves the %s obligation uncovered"
            % (activity, declared, " and ".join(uncovered))
        )
    if extra and not policy["allow_category_above_requirement"]:
        findings.append(
            "%s is declared %s where only %s is owed"
            % (activity, declared, required)
        )
    return {
        "activity": activity,
        "required_category": required,
        "declared_category": declared,
        "uncovered_obligations": uncovered,
        "additional_obligations": extra,
        "covers_required": not uncovered,
        "accepted": not uncovered
        and (not extra or policy["allow_category_above_requirement"]),
        "findings": findings,
    }


def specimen_suitability(category, specimens, policy=DEFAULT_SCA_TEST_POLICY):
    """Are the declared specimens the right articles for this category."""
    validate_sca_test_policy(policy)
    _require_choice("category", category, TEST_CATEGORIES)
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("specimens must be a non-empty sequence, got %r" % (specimens,))
    declared = []
    for kind in specimens:
        _require_choice("specimen", kind, SPECIMEN_KINDS)
        if kind in declared:
            raise ValueError("specimens repeat %s" % kind)
        declared.append(kind)
    expected = list(policy["specimen_for_category"][category])
    missing = sorted(set(expected) - set(declared))
    surplus = sorted(set(declared) - set(expected))
    findings = []
    if missing:
        findings.append(
            "a %s activity needs %s and none is declared"
            % (category, " and ".join(missing))
        )
    if surplus:
        findings.append(
            "a %s activity also runs on %s, which it does not owe"
            % (category, " and ".join(surplus))
        )
    return {
        "category": category,
        "declared_specimens": declared,
        "expected_specimens": expected,
        "missing_specimens": missing,
        "surplus_specimens": surplus,
        "suitable": not missing,
        "findings": findings,
    }


def sample_size_status(category, sample_count, policy=DEFAULT_SCA_TEST_POLICY):
    """Is the declared sample large enough for the category it serves."""
    validate_sca_test_policy(policy)
    _require_choice("category", category, TEST_CATEGORIES)
    declared = _require_count("sample_count", sample_count, 1)
    required = int(policy["min_sample_count"][category])
    sufficient = declared >= required
    findings = []
    if not sufficient:
        findings.append(
            "a %s activity runs on %d articles against a required %d"
            % (category, declared, required)
        )
    return {
        "category": category,
        "declared_count": declared,
        "required_count": required,
        "sufficient": sufficient,
        "findings": findings,
    }


def assess_test_activity(entry, policy=DEFAULT_SCA_TEST_POLICY):
    """Verdict for one declared activity of the SCA test programme."""
    validate_sca_test_policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %r" % (entry,))
    activity = _require_choice(
        "activity", entry.get("activity"), tuple(sorted(REQUIRED_SCA_ACTIVITIES))
    )
    coverage = resolve_category_coverage(activity, entry.get("category"), policy)
    declared = coverage["declared_category"]
    specimens = specimen_suitability(declared, entry.get("specimens"), policy)
    samples = sample_size_status(declared, entry.get("sample_count"), policy)
    findings = (
        list(coverage["findings"]) + list(specimens["findings"]) + list(samples["findings"])
    )
    record = {
        "activity": activity,
        "required_category": coverage["required_category"],
        "declared_category": declared,
        "carries_qualification": "qualification" in _obligations(declared),
        "coverage": coverage,
        "specimens": specimens,
        "samples": samples,
        "findings": findings,
    }
    if not coverage["accepted"]:
        record["verdict"] = ACTIVITY_CATEGORY_SHORTFALL
    elif not specimens["suitable"]:
        record["verdict"] = ACTIVITY_SPECIMEN_MISMATCH
    elif not samples["sufficient"]:
        record["verdict"] = ACTIVITY_SAMPLE_SHORTFALL
    else:
        record["verdict"] = ACTIVITY_COVERED
    return record


def assess_sca_test_programme(case, policy=DEFAULT_SCA_TEST_POLICY):
    """Full clause 6.1.1 sweep over a declared SCA test programme."""
    validate_sca_test_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    activities = case.get("activities")
    if not isinstance(activities, (list, tuple)) or not activities:
        raise ValueError("case activities must be a non-empty sequence of mappings")
    records = [assess_test_activity(entry, policy) for entry in activities]
    named = [record["activity"] for record in records]
    repeated = sorted({a for a in named if named.count(a) > 1})
    if repeated:
        raise ValueError("case declares an activity twice: %s" % ", ".join(repeated))
    absent = sorted(set(REQUIRED_SCA_ACTIVITIES) - set(named))
    covered = [
        record["activity"] for record in records if record["verdict"] == ACTIVITY_COVERED
    ]
    qualification_bearing = [
        record["activity"]
        for record in records
        if record["verdict"] == ACTIVITY_COVERED and record["carries_qualification"]
    ]
    grouped = {}
    for record in records:
        grouped.setdefault(record["verdict"], []).append(record["activity"])
    findings = []
    for record in records:
        findings.extend(record["findings"])
    for activity in absent:
        findings.append("%s is not declared by the programme at all" % activity)
    coverage_fraction = len(covered) / float(len(REQUIRED_SCA_ACTIVITIES))
    share = (
        len(qualification_bearing) / float(len(covered)) if covered else 0.0
    )
    required_share = float(policy["min_qualification_share"])
    combined = _at_least(share, required_share)
    if not combined:
        findings.append(
            "qualification-bearing share %.4f falls below the required %.4f"
            % (share, required_share)
        )
    open_activities = sorted(
        set(absent) | {a for a in named if a not in covered}
    )
    return {
        "verdict": PROGRAMME_COMPLETE
        if not open_activities and combined
        else PROGRAMME_INCOMPLETE,
        "activity_records": records,
        "grouped_by_verdict": grouped,
        "absent_activities": absent,
        "covered_activities": sorted(covered),
        "coverage_fraction": coverage_fraction,
        "qualification_share": share,
        "required_qualification_share": required_share,
        "combined_campaign": combined,
        "open_activities": open_activities,
        "findings": findings,
    }
