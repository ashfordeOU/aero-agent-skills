#!/usr/bin/env python3
"""Minimum sample quantities and test coverage of a blocking diode qualification.

Anchor: ECSS-E-ST-20-08C clause 12.5.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Qualification of a blocking diode is a set of tests, and each of those
tests owes a minimum number of samples. That second half is the part
campaigns lose. A test run on fewer parts than its minimum has been run,
and it has produced data, and it has not qualified anything -- the whole
point of the minimum is that one part passing is an anecdote about one
part.

Four things follow.

A minimum that was never declared is not a minimum of zero. A test plan
that books tests without stating how many samples each one owes cannot be
graded at all, and the assessment closes on that rather than passing a
campaign whose sizing nobody wrote down.

Allocation is judged per test, not in total. A campaign with plenty of
samples overall, and one test underfed, has left that test unqualified,
and the surplus somewhere else does not reach it.

Destructive and non-destructive tests draw on the qualification lot
differently, and this is the arithmetic that most often goes wrong. A
sample consumed by a destructive test is gone; those allocations add up.
A sample that survives a non-destructive test can be presented to the
next non-destructive test, so those allocations do not add up -- the lot
only has to carry the largest of them at once. Summing everything
overstates the lot needed; summing nothing understates it. The honest
figure is the destructive total plus the largest single non-destructive
draw.

An owed test with no allocation at all is a coverage hole rather than a
shortfall of some size, and it is reported as its own kind of finding so
that a plan missing a test is not mistaken for a plan that merely
underfed one.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

OWED_TEST_NOT_BOOKED = "owed-test-not-booked"
SAMPLE_QUANTITY_SHORT = "sample-quantity-short-of-minimum"
ALLOCATION_BOOKED_TO_UNOWED_TEST = "allocation-booked-to-unowed-test"

MINIMUM_QUANTITIES_NOT_DECLARED = "minimum-sample-quantities-not-declared"
QUALIFICATION_SAMPLE_SHORTFALL = "qualification-sample-quantity-shortfall"
QUALIFICATION_LOT_NOT_DECLARED = "qualification-lot-size-not-declared"
QUALIFICATION_LOT_INSUFFICIENT = "qualification-lot-cannot-feed-the-campaign"
TESTING_MEETS_MINIMUMS = "qualification-testing-meets-minimum-quantities"

DEFAULT_QUALIFICATION_POLICY = {
    "lot_reserve_fraction": 0.1,
    "marginal_allocation_margin": 1,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number of samples, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_qualification_policy(policy):
    """Check the campaign sizing policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    reserve = _require_non_negative(
        "lot_reserve_fraction", policy.get("lot_reserve_fraction")
    )
    if reserve > 1.0:
        raise ValueError(
            "lot_reserve_fraction %g is above one; a reserve that doubles the "
            "lot is a sizing error, not a policy" % reserve
        )
    margin = _require_count(
        "marginal_allocation_margin", policy.get("marginal_allocation_margin")
    )
    return {"lot_reserve_fraction": reserve, "marginal_allocation_margin": margin}


def validate_test_requirement(requirement):
    """Read one owed qualification test and the sample quantity it asks for."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    name = _require_label("test name", requirement.get("test"))
    if not name:
        raise ValueError("test name must not be blank")
    minimum = _require_count("minimum_samples on %s" % name, requirement.get("minimum_samples"))
    if minimum < 1:
        raise ValueError(
            "minimum_samples on %s is %d; a test owing no sample is not a "
            "qualification test" % (name, minimum)
        )
    destructive = _require_flag(
        "destructive on %s" % name, requirement.get("destructive")
    )
    return {"test": name, "minimum_samples": minimum, "destructive": destructive}


def validate_requirements(requirements):
    """Read the owed test set, refusing an empty or duplicated one."""
    if not isinstance(requirements, (list, tuple)):
        raise ValueError("requirements must be a sequence of owed tests")
    if not requirements:
        raise ValueError(
            "no qualification test is owed, so there is no minimum quantity to "
            "grade the campaign against"
        )
    checked = []
    seen = set()
    for requirement in requirements:
        entry = validate_test_requirement(requirement)
        if entry["test"] in seen:
            raise ValueError("test %r is owed twice in the plan" % entry["test"])
        seen.add(entry["test"])
        checked.append(entry)
    return tuple(checked)


def validate_allocation(allocation):
    """Read one booked allocation of samples to a test."""
    if not isinstance(allocation, dict):
        raise ValueError("allocation must be a mapping, got %r" % (allocation,))
    name = _require_label("test name", allocation.get("test"))
    if not name:
        raise ValueError("test name must not be blank")
    allocated = _require_count(
        "allocated_samples on %s" % name, allocation.get("allocated_samples")
    )
    return {"test": name, "allocated_samples": allocated}


def allocation_map(allocations):
    """Index the booked allocations by test, refusing a test booked twice."""
    if not isinstance(allocations, (list, tuple)):
        raise ValueError("allocations must be a sequence of booked allocations")
    booked = {}
    for allocation in allocations:
        entry = validate_allocation(allocation)
        if entry["test"] in booked:
            raise ValueError(
                "test %r is booked twice; merge the allocations before grading "
                "them" % entry["test"]
            )
        booked[entry["test"]] = entry["allocated_samples"]
    return booked


def allocation_shortfall(minimum_samples, allocated_samples):
    """How many samples a test is short of its declared minimum."""
    minimum = _require_count("minimum_samples", minimum_samples)
    allocated = _require_count("allocated_samples", allocated_samples)
    return max(0, minimum - allocated)


def test_allocation_verdicts(requirements, allocations):
    """Grade every owed test on the samples the campaign books for it."""
    owed = validate_requirements(requirements)
    booked = allocation_map(allocations)
    verdicts = []
    for entry in owed:
        allocated = booked.get(entry["test"], 0)
        shortfall = allocation_shortfall(entry["minimum_samples"], allocated)
        reasons = []
        if entry["test"] not in booked:
            reasons.append(OWED_TEST_NOT_BOOKED)
        elif shortfall > 0:
            reasons.append(SAMPLE_QUANTITY_SHORT)
        verdicts.append(
            {
                "test": entry["test"],
                "minimum_samples": entry["minimum_samples"],
                "allocated_samples": allocated,
                "shortfall": shortfall,
                "destructive": entry["destructive"],
                "booked": entry["test"] in booked,
                "reasons": tuple(reasons),
                "meets_minimum": shortfall == 0,
            }
        )
    return tuple(verdicts)


def unowed_allocations(requirements, allocations):
    """Name allocations booked to a test the qualification never owed."""
    owed = {entry["test"] for entry in validate_requirements(requirements)}
    booked = allocation_map(allocations)
    return tuple(sorted(name for name in booked if name not in owed))


def destructive_sample_demand(verdicts):
    """Samples the destructive tests consume; these add up because they are gone."""
    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("verdicts must be a sequence")
    return sum(v["allocated_samples"] for v in verdicts if v["destructive"])


def shared_sample_demand(verdicts):
    """Samples the non-destructive tests need at once.

    A part that survives one non-destructive test can be presented to the
    next, so these do not add up: the lot only has to carry the largest
    single draw.
    """
    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("verdicts must be a sequence")
    draws = [v["allocated_samples"] for v in verdicts if not v["destructive"]]
    return max(draws) if draws else 0


def required_lot_size(verdicts):
    """Smallest qualification lot that can actually feed the booked campaign."""
    return destructive_sample_demand(verdicts) + shared_sample_demand(verdicts)


def required_lot_with_reserve(verdicts, policy=DEFAULT_QUALIFICATION_POLICY):
    """Required lot size carrying the declared reserve for reruns and spares."""
    checked = validate_qualification_policy(policy)
    return required_lot_size(verdicts) * (1.0 + checked["lot_reserve_fraction"])


def lot_is_sufficient(lot_size, verdicts, policy=DEFAULT_QUALIFICATION_POLICY):
    """True when the declared lot covers the campaign plus its reserve."""
    size = _require_count("lot_size", lot_size)
    return _at_least(float(size), required_lot_with_reserve(verdicts, policy))


def minimum_quantity_coverage(verdicts):
    """Share of the owed tests that actually reach their minimum quantity."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    met = sum(1 for v in verdicts if v["meets_minimum"])
    return met / len(verdicts)


def worst_shortfall_test(verdicts):
    """The owed test furthest short of its minimum sample quantity."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    return max(verdicts, key=lambda v: v["shortfall"])


def marginal_allocation_advisories(
    verdicts, policy=DEFAULT_QUALIFICATION_POLICY
):
    """Name tests booked so close to their minimum that one loss undoes them.

    These do not move the verdict -- a test at its minimum meets its
    minimum -- but a single part damaged in handling then takes the test
    below the quantity that qualifies it, and that is worth saying while
    the plan can still be changed.
    """
    checked = validate_qualification_policy(policy)
    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("verdicts must be a sequence")
    margin = checked["marginal_allocation_margin"]
    advisories = []
    for verdict in verdicts:
        if not verdict["meets_minimum"]:
            continue
        headroom = verdict["allocated_samples"] - verdict["minimum_samples"]
        if headroom <= margin:
            advisories.append(
                "test %s is booked %d sample(s) above its minimum of %d, inside "
                "the %d sample marginal margin; one part lost in handling takes "
                "it below the quantity that qualifies it"
                % (
                    verdict["test"],
                    headroom,
                    verdict["minimum_samples"],
                    margin,
                )
            )
    return tuple(advisories)


def assess_qualification_testing(case, policy=DEFAULT_QUALIFICATION_POLICY):
    """Full clause 12.5.5 sizing and coverage decision for one campaign plan."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_qualification_policy(policy)

    findings = []
    advisories = []
    result = {
        "test_verdicts": (),
        "tests_meeting_minimum": (),
        "tests_short": (),
        "unowed_allocations": (),
        "minimum_quantity_coverage": None,
        "destructive_sample_demand": None,
        "shared_sample_demand": None,
        "required_lot_size": None,
        "required_lot_with_reserve": None,
        "declared_lot_size": None,
        "worst_shortfall_test": None,
        "worst_shortfall": None,
        "findings": findings,
        "advisories": advisories,
    }

    requirements = case.get("test_requirements")
    if requirements is None:
        findings.append(
            "the plan states no minimum sample quantity for any test, so the "
            "campaign cannot be graded; an undeclared minimum is not a minimum "
            "of zero"
        )
        result["verdict"] = MINIMUM_QUANTITIES_NOT_DECLARED
        return result

    verdicts = test_allocation_verdicts(requirements, case.get("allocations", []))
    result["test_verdicts"] = verdicts
    result["tests_meeting_minimum"] = tuple(
        v["test"] for v in verdicts if v["meets_minimum"]
    )
    result["tests_short"] = tuple(
        v["test"] for v in verdicts if not v["meets_minimum"]
    )
    result["unowed_allocations"] = unowed_allocations(
        requirements, case.get("allocations", [])
    )
    result["minimum_quantity_coverage"] = minimum_quantity_coverage(verdicts)
    result["destructive_sample_demand"] = destructive_sample_demand(verdicts)
    result["shared_sample_demand"] = shared_sample_demand(verdicts)
    result["required_lot_size"] = required_lot_size(verdicts)
    result["required_lot_with_reserve"] = required_lot_with_reserve(verdicts, policy)

    worst = worst_shortfall_test(verdicts)
    result["worst_shortfall_test"] = worst["test"]
    result["worst_shortfall"] = worst["shortfall"]

    for name in result["unowed_allocations"]:
        findings.append(
            "samples are booked to %s, which this qualification never owed (%s)"
            % (name, ALLOCATION_BOOKED_TO_UNOWED_TEST)
        )

    for verdict in verdicts:
        if verdict["meets_minimum"]:
            continue
        if OWED_TEST_NOT_BOOKED in verdict["reasons"]:
            findings.append(
                "owed test %s is not booked at all; the campaign has a coverage "
                "hole rather than a quantity shortfall" % verdict["test"]
            )
        else:
            findings.append(
                "test %s is booked %d sample(s) against a minimum of %d, short "
                "by %d"
                % (
                    verdict["test"],
                    verdict["allocated_samples"],
                    verdict["minimum_samples"],
                    verdict["shortfall"],
                )
            )

    advisories.extend(marginal_allocation_advisories(verdicts, policy))

    if result["tests_short"]:
        result["verdict"] = QUALIFICATION_SAMPLE_SHORTFALL
        return result

    lot_size = case.get("qualification_lot_size")
    if lot_size is None:
        findings.append(
            "no qualification lot size is declared, so nobody can say the "
            "booked campaign can actually be fed"
        )
        result["verdict"] = QUALIFICATION_LOT_NOT_DECLARED
        return result
    result["declared_lot_size"] = _require_count("qualification_lot_size", lot_size)

    if not lot_is_sufficient(lot_size, verdicts, policy):
        findings.append(
            "the declared lot of %d part(s) cannot feed a campaign needing %d "
            "plus reserve (%.4g); the destructive tests alone consume %d"
            % (
                result["declared_lot_size"],
                result["required_lot_size"],
                result["required_lot_with_reserve"],
                result["destructive_sample_demand"],
            )
        )
        result["verdict"] = QUALIFICATION_LOT_INSUFFICIENT
        return result

    result["verdict"] = TESTING_MEETS_MINIMUMS
    return result
