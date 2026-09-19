#!/usr/bin/env python3
"""Planning the test process of a campaign at a test centre.

Anchor: ECSS-Q-ST-20-07 clause 5.7.1, the requirement that the test
process is planned: the campaign activities, their schedule, the
resources they need, the reviews they pass through and the interfaces
with the customer. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

Four things follow from what the clause is for.

A campaign duration is the longest path, not the sum. Activities that
do not depend on each other run together, so summing the durations
overstates the campaign, while reading only the chain somebody wrote
down understates it. The longest path over the whole dependency graph
is the campaign.

A graph that closes on itself has no duration. A cycle means a
predecessor was wired backwards, and returning any number for it
invents a plan that cannot be executed.

Resource loading is per resource. A campaign can sit inside its total
effort and still be impossible because one shaker, one clean room or
one qualified operator is committed twice over.

The customer interface has a lead time measured back from the start of
the campaign. A plan written late does not shorten what the customer is
owed.

The policy numbers below are declared test-centre values, not physical
constants: a test centre substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PROCESS_NOT_PLANNED = "test-campaign-process-not-planned"
REQUIRED_REVIEW_MISSING = "test-campaign-required-review-missing"
SCHEDULE_MARGIN_NEGATIVE = "test-campaign-schedule-margin-negative"
RESOURCE_OVER_CAPACITY = "test-campaign-resource-over-capacity"
CUSTOMER_NOTIFIED_LATE = "test-campaign-customer-notified-late"
MARGIN_BELOW_REQUIRED = "test-campaign-margin-below-required"
PLAN_COMMITTABLE = "test-campaign-plan-committable"

DEFAULT_PLANNING_POLICY = {
    "required_margin_days": 5.0,
    "required_reviews": ("test-readiness-review", "post-test-review"),
    "customer_notification_lead_days": 14,
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


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    label = value.strip()
    if not label:
        raise ValueError("%s must not be blank" % name)
    return label


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


def _below(value, limit):
    """value < limit, and not merely by representation error."""
    return value < limit and not math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_planning_policy(policy):
    """Check the margin, the reviews owed and the notification lead."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_non_negative("required_margin_days", policy.get("required_margin_days"))
    reviews = policy.get("required_reviews")
    if not isinstance(reviews, (list, tuple)) or not reviews:
        raise ValueError(
            "required_reviews must be a non-empty sequence of review labels, "
            "got %r" % (reviews,)
        )
    for review in reviews:
        _require_label("required review", review)
    _require_count(
        "customer_notification_lead_days",
        policy.get("customer_notification_lead_days"),
    )
    return policy


def validate_activity(activity):
    """Read one campaign activity, its duration and what it waits on."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping, got %r" % (activity,))
    predecessors = activity.get("predecessors", ())
    if not isinstance(predecessors, (list, tuple)):
        raise ValueError("predecessors must be a sequence of activity labels")
    activity_id = _require_label("activity_id", activity.get("activity_id"))
    read_back = []
    for item in predecessors:
        name = _require_label("predecessor", item)
        if name == activity_id:
            raise ValueError("activity %r depends on itself" % activity_id)
        if name not in read_back:
            read_back.append(name)
    return {
        "activity_id": activity_id,
        "duration_days": _require_positive(
            "duration_days", activity.get("duration_days")
        ),
        "resource": _require_label("resource", activity.get("resource")),
        "predecessors": tuple(read_back),
    }


def validate_activities(activities):
    """Read the whole activity set, refusing duplicates and unknown links."""
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a sequence of activity records")
    checked = []
    seen = set()
    for activity in activities:
        record = validate_activity(activity)
        if record["activity_id"] in seen:
            raise ValueError("activity %r appears twice" % record["activity_id"])
        seen.add(record["activity_id"])
        checked.append(record)
    if not checked:
        raise ValueError("the campaign declares no activities at all")
    for record in checked:
        for name in record["predecessors"]:
            if name not in seen:
                raise ValueError(
                    "activity %r waits on %r, which the plan never declares"
                    % (record["activity_id"], name)
                )
    return tuple(checked)


def topological_order(activities):
    """Order the activities so every predecessor comes first."""
    checked = validate_activities(activities)
    pending = {record["activity_id"]: record for record in checked}
    placed = []
    placed_names = set()
    while pending:
        ready = sorted(
            name
            for name, record in pending.items()
            if all(link in placed_names for link in record["predecessors"])
        )
        if not ready:
            raise ValueError(
                "the dependency graph closes on itself among %s"
                % ", ".join(sorted(pending))
            )
        for name in ready:
            placed.append(pending.pop(name))
            placed_names.add(name)
    return tuple(placed)


def earliest_finishes(activities):
    """Earliest finish day of every activity along the longest path to it."""
    finishes = {}
    for record in topological_order(activities):
        start = 0.0
        for link in record["predecessors"]:
            if finishes[link] > start:
                start = finishes[link]
        finishes[record["activity_id"]] = start + record["duration_days"]
    return finishes


def campaign_duration(activities):
    """Longest path through the activity graph, in days."""
    finishes = earliest_finishes(activities)
    return max(finishes.values())


def critical_chain(activities):
    """The activity chain that produced the campaign duration."""
    checked = {
        record["activity_id"]: record for record in validate_activities(activities)
    }
    finishes = earliest_finishes(activities)
    end = max(sorted(finishes), key=lambda name: finishes[name])
    chain = [end]
    current = end
    while checked[current]["predecessors"]:
        previous = max(
            sorted(checked[current]["predecessors"]),
            key=lambda name: finishes[name],
        )
        chain.append(previous)
        current = previous
    chain.reverse()
    return tuple(chain)


def schedule_margin(activities, customer_milestone_days):
    """Days left between the end of the longest path and the milestone."""
    milestone = _require_positive(
        "customer_milestone_days", customer_milestone_days
    )
    return milestone - campaign_duration(activities)


def resource_load(activities):
    """Days of work each named resource is committed to."""
    load = {}
    for record in validate_activities(activities):
        load[record["resource"]] = (
            load.get(record["resource"], 0.0) + record["duration_days"]
        )
    return load


def validate_resource_capacity(capacity):
    """Read the days each resource can actually carry."""
    if not isinstance(capacity, dict):
        raise ValueError("resource capacity must be a mapping of resource to days")
    read_back = {}
    for resource, days in capacity.items():
        name = _require_label("capacity resource", resource)
        read_back[name] = _require_positive("capacity[%s]" % name, days)
    return read_back


def resources_over_capacity(activities, capacity):
    """Resources loaded past the capacity declared for them."""
    declared = validate_resource_capacity(capacity)
    over = []
    for resource, days in sorted(resource_load(activities).items()):
        if resource not in declared:
            raise ValueError(
                "activities load resource %r, for which no capacity is "
                "declared" % resource
            )
        if not _at_most(days, declared[resource]):
            over.append(
                {
                    "resource": resource,
                    "loaded_days": days,
                    "capacity_days": declared[resource],
                }
            )
    return tuple(over)


def missing_reviews(planned_reviews, policy=None):
    """Reviews the campaign owes that the plan does not name."""
    policy = validate_planning_policy(policy or DEFAULT_PLANNING_POLICY)
    if not isinstance(planned_reviews, (list, tuple, set, frozenset)):
        raise ValueError("planned_reviews must be a sequence of review labels")
    planned = {_require_label("planned review", item) for item in planned_reviews}
    required = {
        _require_label("required review", item)
        for item in policy["required_reviews"]
    }
    return tuple(sorted(required - planned))


def customer_notification_lead(notification_day, campaign_start_day):
    """Days between the customer notification and the campaign start."""
    start = _require_count("campaign_start_day", campaign_start_day)
    notified = _require_count("notification_day", notification_day)
    if notified > start:
        raise ValueError(
            "the customer was notified on day %d, after the campaign started "
            "on day %d" % (notified, start)
        )
    return start - notified


def assess_test_process_plan(case):
    """Grade a campaign plan and say whether it can be committed to."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_planning_policy(case.get("policy") or DEFAULT_PLANNING_POLICY)

    findings = []
    advisories = []
    result = {
        "activities": 0,
        "campaign_duration_days": None,
        "critical_chain": (),
        "schedule_margin_days": None,
        "resource_load": {},
        "resources_over_capacity": (),
        "missing_reviews": (),
        "notification_lead_days": None,
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    plan = case.get("plan")
    if plan is None:
        findings.append(
            "no campaign plan was supplied, so the test process stands "
            "unplanned"
        )
        result["verdict"] = PROCESS_NOT_PLANNED
        return result
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))

    activities = plan.get("activities")
    if not activities:
        findings.append(
            "the plan names no activities, which is an unplanned process "
            "rather than a campaign of zero length"
        )
        result["verdict"] = PROCESS_NOT_PLANNED
        return result

    checked = validate_activities(activities)
    result["activities"] = len(checked)
    result["campaign_duration_days"] = campaign_duration(checked)
    result["critical_chain"] = critical_chain(checked)
    result["resource_load"] = resource_load(checked)

    absent = missing_reviews(plan.get("planned_reviews", ()), policy)
    result["missing_reviews"] = absent
    if absent:
        findings.append(
            "the plan names no %s, so the campaign has no interface for it"
            % ", ".join(absent)
        )
        result["verdict"] = REQUIRED_REVIEW_MISSING
        return result

    margin = schedule_margin(checked, plan.get("customer_milestone_days"))
    result["schedule_margin_days"] = margin
    if _below(margin, 0.0):
        findings.append(
            "the longest path runs %.6g day(s) past the customer milestone"
            % (-margin)
        )
        result["verdict"] = SCHEDULE_MARGIN_NEGATIVE
        return result

    capacity = plan.get("resource_capacity")
    if capacity is None:
        raise ValueError(
            "the plan declares no resource capacity, so the activities cannot "
            "be loaded against anything"
        )
    over = resources_over_capacity(checked, capacity)
    result["resources_over_capacity"] = over
    if over:
        findings.append(
            "resource(s) are committed past their capacity: %s"
            % ", ".join(
                "%s at %.6g day(s) against %.6g"
                % (entry["resource"], entry["loaded_days"], entry["capacity_days"])
                for entry in over
            )
        )
        result["verdict"] = RESOURCE_OVER_CAPACITY
        return result

    lead = customer_notification_lead(
        plan.get("notification_day"), plan.get("campaign_start_day")
    )
    result["notification_lead_days"] = lead
    if lead < int(policy["customer_notification_lead_days"]):
        findings.append(
            "the customer was given %d day(s) notice against the %d day(s) "
            "the interface owes"
            % (lead, int(policy["customer_notification_lead_days"]))
        )
        result["verdict"] = CUSTOMER_NOTIFIED_LATE
        return result

    if not _at_least(margin, float(policy["required_margin_days"])):
        advisories.append(
            "the plan leaves %.6g day(s) of margin against the %.6g the test "
            "centre requires" % (margin, float(policy["required_margin_days"]))
        )
        result["verdict"] = MARGIN_BELOW_REQUIRED
        return result

    result["verdict"] = PLAN_COMMITTABLE
    return result
