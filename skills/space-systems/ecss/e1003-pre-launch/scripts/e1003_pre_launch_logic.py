#!/usr/bin/env python3
"""ECSS-E-ST-10C §7 pre-launch testing at launch site (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system-testing standard's §7 pre-launch clause requires, after spacecraft
delivery to the launch site, health checks across structural, electrical,
thermal, propulsion, software, and mechanical categories; leak-rate
measurements on every pressurized system compared against system-specific
allowable limits; functional tests of each subsystem in launch configuration
with critical failures treated as launch holds; and continuous monitoring
that campaign environmental and temporal constraints (temperature, humidity,
battery charge duration, shelf life, cleanliness class) remain within
approved bounds. This module implements health-check categorization and
result evaluation, leak-rate comparison, functional-test outcome assessment,
and campaign-constraint bound-checking; it does not implement the mechanical
transport-damage model or launch-vehicle interface verification.
"""

HEALTH_CHECK_CATEGORIES = frozenset({
    "structural",
    "electrical",
    "thermal",
    "propulsion",
    "software",
    "mechanical",
})

HEALTH_CHECK_RESULTS = frozenset({"pass", "fail", "marginal"})

LEAK_CHECK_TYPES = frozenset({
    "propulsion_system",
    "pressurized_vessel",
    "pneumatic_line",
    "thruster_valve",
})

CAMPAIGN_CONSTRAINT_TYPES = frozenset({
    "temperature_c",
    "relative_humidity_pct",
    "battery_charge_duration_h",
    "shelf_life_days",
    "cleanliness_level_numeric",
})


def categorize_health_check(check_category):
    """Category string for a health check.  Returns check_category when it
    is one of the six recognized categories; raises ValueError otherwise."""
    if check_category in HEALTH_CHECK_CATEGORIES:
        return check_category
    raise ValueError(
        "unrecognized health check category %r under "
        "ECSS-E-ST-10C §7" % (check_category,)
    )


def evaluate_health_check(check_id, check_category, result):
    """Violation list (empty if the check is clear) for one health check.

    check_category must be a recognized category; result must be one of
    "pass", "fail", or "marginal". A "fail" result produces a launch_hold
    finding. A "marginal" result produces an advisory finding requiring
    disposition before campaign advancement. Raises ValueError for an
    unrecognized category or result."""
    categorize_health_check(check_category)
    if result not in HEALTH_CHECK_RESULTS:
        raise ValueError(
            "unrecognized health check result %r; expected one of %s"
            % (result, sorted(HEALTH_CHECK_RESULTS))
        )
    if result == "fail":
        return [
            {
                "issue": "health_check_failed_launch_hold",
                "check_id": check_id,
                "check_category": check_category,
            }
        ]
    if result == "marginal":
        return [
            {
                "issue": "health_check_marginal_advisory",
                "check_id": check_id,
                "check_category": check_category,
            }
        ]
    return []


def evaluate_leak_check(check_id, leak_type, measured_rate_sccm, allowable_rate_sccm):
    """Violation list (empty if within limits) for one pressurized-system
    leak check.  measured_rate_sccm is compared against allowable_rate_sccm;
    an exceedance produces a launch_hold finding.  Raises ValueError if
    leak_type is unrecognized or either rate is negative."""
    if leak_type not in LEAK_CHECK_TYPES:
        raise ValueError(
            "unrecognized leak check type %r under ECSS-E-ST-10C §7"
            % (leak_type,)
        )
    if measured_rate_sccm < 0:
        raise ValueError("measured_rate_sccm must be >= 0")
    if allowable_rate_sccm < 0:
        raise ValueError("allowable_rate_sccm must be >= 0")
    if measured_rate_sccm > allowable_rate_sccm:
        return [
            {
                "issue": "leak_rate_exceeded_launch_hold",
                "check_id": check_id,
                "leak_type": leak_type,
                "measured_rate_sccm": measured_rate_sccm,
                "allowable_rate_sccm": allowable_rate_sccm,
            }
        ]
    return []


def evaluate_functional_test(test_id, subsystem, passed, is_critical):
    """Violation list (empty if the test passed) for one subsystem functional
    test.  A failed critical subsystem produces a launch_hold finding; a
    failed non-critical subsystem produces an advisory finding.  A passing
    test produces no finding regardless of criticality."""
    if passed:
        return []
    if is_critical:
        return [
            {
                "issue": "functional_test_failed_critical_launch_hold",
                "test_id": test_id,
                "subsystem": subsystem,
            }
        ]
    return [
        {
            "issue": "functional_test_failed_noncritical_advisory",
            "test_id": test_id,
            "subsystem": subsystem,
        }
    ]


def evaluate_campaign_constraint(
    constraint_id, constraint_type, measured_value, lower_bound, upper_bound
):
    """Violation list (empty if within bounds) for one campaign constraint.

    constraint_type must be a recognized type.  measured_value is checked
    against [lower_bound, upper_bound] (both inclusive); a value outside
    that range produces an out_of_bounds finding.  Raises ValueError for an
    unrecognized constraint type."""
    if constraint_type not in CAMPAIGN_CONSTRAINT_TYPES:
        raise ValueError(
            "unrecognized campaign constraint type %r under ECSS-E-ST-10C §7"
            % (constraint_type,)
        )
    if measured_value < lower_bound:
        return [
            {
                "issue": "campaign_constraint_below_lower_bound",
                "constraint_id": constraint_id,
                "constraint_type": constraint_type,
                "measured_value": measured_value,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
            }
        ]
    if measured_value > upper_bound:
        return [
            {
                "issue": "campaign_constraint_above_upper_bound",
                "constraint_id": constraint_id,
                "constraint_type": constraint_type,
                "measured_value": measured_value,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
            }
        ]
    return []


def launch_readiness_review(
    health_checks, leak_checks, functional_tests, campaign_constraints
):
    """Aggregate pre-launch readiness review for all four check categories.

    health_checks: iterable of dicts with keys "check_id", "check_category",
    "result".  leak_checks: iterable of dicts with keys "check_id",
    "leak_type", "measured_rate_sccm", "allowable_rate_sccm".
    functional_tests: iterable of dicts with keys "test_id", "subsystem",
    "passed", "is_critical".  campaign_constraints: iterable of dicts with
    keys "constraint_id", "constraint_type", "measured_value", "lower_bound",
    "upper_bound".

    Returns {"health": [...], "leak": [...], "functional": [...],
    "constraints": [...]}, each a flat violation list.  Does not mutate
    the input iterables.  Raises ValueError for any unrecognized type or
    result value encountered during evaluation."""
    health_violations = []
    for hc in health_checks:
        health_violations.extend(
            evaluate_health_check(
                hc["check_id"], hc["check_category"], hc["result"]
            )
        )

    leak_violations = []
    for lc in leak_checks:
        leak_violations.extend(
            evaluate_leak_check(
                lc["check_id"],
                lc["leak_type"],
                lc["measured_rate_sccm"],
                lc["allowable_rate_sccm"],
            )
        )

    functional_violations = []
    for ft in functional_tests:
        functional_violations.extend(
            evaluate_functional_test(
                ft["test_id"], ft["subsystem"], ft["passed"], ft["is_critical"]
            )
        )

    constraint_violations = []
    for cc in campaign_constraints:
        constraint_violations.extend(
            evaluate_campaign_constraint(
                cc["constraint_id"],
                cc["constraint_type"],
                cc["measured_value"],
                cc["lower_bound"],
                cc["upper_bound"],
            )
        )

    return {
        "health": health_violations,
        "leak": leak_violations,
        "functional": functional_violations,
        "constraints": constraint_violations,
    }


def is_launch_ready(review):
    """True when every category in a launch_readiness_review result is
    empty -- the system satisfies all §7 pre-launch requirements."""
    return all(len(violations) == 0 for violations in review.values())
