#!/usr/bin/env python3
"""Maintenance control of a test facility before it carries a campaign.

Anchor: ECSS-Q-ST-20-07 clause 5.6.4, the requirement that preventive
and corrective maintenance of a test facility is planned and recorded.
The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

Four things follow from what the clause is for.

Every preventive task carries its own interval. A pump seal on a ninety
day cycle and a crane inspection on a yearly one lapse at different
moments, so each task is aged against its own interval rather than
against one facility-wide calendar date.

A lapsed safety-critical task is a different decision, not a larger
span. One of them holds the facility whatever the rest of the plan
looks like, so it is separated before any span ordering is applied.

Corrective work is aged from the day it was raised, against the
close-out allowance its priority carries. That clock is unrelated to
the preventive intervals, and mixing them lets a fresh high-priority
order hide behind a current preventive plan.

Maintenance completed is not maintenance closed. Work that disturbed a
measurement chain, an interlock or a structural path leaves the
facility unproven until the revalidation it called for is recorded.

The policy numbers below are declared test-centre values, not physical
constants: a test centre substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

NO_MAINTENANCE_PLAN = "test-facility-not-under-maintenance-plan"
SAFETY_CRITICAL_LAPSED = "test-facility-safety-critical-task-lapsed"
REVALIDATION_OUTSTANDING = "test-facility-revalidation-outstanding"
CORRECTIVE_PAST_ALLOWANCE = "test-facility-corrective-order-past-allowance"
PREVENTIVE_CURRENCY_SHORT = "test-facility-preventive-currency-short"
ROUTINE_TASK_OVERDUE = "test-facility-routine-task-overdue"
RELEASED_TO_SERVICE = "test-facility-released-to-service"

DEFAULT_MAINTENANCE_POLICY = {
    "routine_overdue_tolerance_days": 7,
    "min_preventive_currency": 0.9,
    "close_out_allowance_days": {"high": 14, "medium": 45, "low": 120},
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
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    count = _require_count(name, value)
    if count == 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return count


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    label = value.strip()
    if not label:
        raise ValueError("%s must not be blank" % name)
    return label


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_maintenance_policy(policy):
    """Check the policy the facility maintenance state is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count(
        "routine_overdue_tolerance_days",
        policy.get("routine_overdue_tolerance_days"),
    )
    _require_fraction(
        "min_preventive_currency", policy.get("min_preventive_currency")
    )
    allowances = policy.get("close_out_allowance_days")
    if not isinstance(allowances, dict) or not allowances:
        raise ValueError(
            "close_out_allowance_days must be a non-empty mapping of priority "
            "to days, got %r" % (allowances,)
        )
    for priority, days in allowances.items():
        _require_label("close-out priority", priority)
        _require_count("close_out_allowance_days[%s]" % priority, days)
    return policy


def validate_preventive_task(task, as_of_day):
    """Read one preventive maintenance task and when it was last done."""
    if not isinstance(task, dict):
        raise ValueError("preventive task must be a mapping, got %r" % (task,))
    day = _require_count("as_of_day", as_of_day)
    last_done = _require_count("last_done_day", task.get("last_done_day"))
    if last_done > day:
        raise ValueError(
            "task %r was last done on day %d, after the assessment day %d"
            % (task.get("task_id"), last_done, day)
        )
    return {
        "task_id": _require_label("task_id", task.get("task_id")),
        "interval_days": _require_positive_count(
            "interval_days", task.get("interval_days")
        ),
        "last_done_day": last_done,
        "safety_critical": _require_flag(
            "safety_critical", task.get("safety_critical", False)
        ),
        "revalidation_required": _require_flag(
            "revalidation_required", task.get("revalidation_required", False)
        ),
        "revalidation_recorded": _require_flag(
            "revalidation_recorded", task.get("revalidation_recorded", False)
        ),
    }


def validate_preventive_plan(tasks, as_of_day):
    """Read the whole preventive plan, refusing the same task twice."""
    if not isinstance(tasks, (list, tuple)):
        raise ValueError("preventive plan must be a sequence of tasks")
    checked = []
    seen = set()
    for task in tasks:
        record = validate_preventive_task(task, as_of_day)
        if record["task_id"] in seen:
            raise ValueError("preventive task %r appears twice" % record["task_id"])
        seen.add(record["task_id"])
        checked.append(record)
    if not checked:
        raise ValueError("the preventive plan declares no tasks at all")
    return tuple(checked)


def task_overdue_span(task, as_of_day):
    """Days past its own interval; negative means time still in hand."""
    record = validate_preventive_task(task, as_of_day)
    elapsed = _require_count("as_of_day", as_of_day) - record["last_done_day"]
    return elapsed - record["interval_days"]


def overdue_tasks(tasks, as_of_day):
    """Preventive tasks past their own interval, worst span first."""
    spans = []
    for record in validate_preventive_plan(tasks, as_of_day):
        span = task_overdue_span(record, as_of_day)
        if span > 0:
            spans.append({"task_id": record["task_id"], "overdue_days": span})
    return tuple(sorted(spans, key=lambda item: (-item["overdue_days"], item["task_id"])))


def lapsed_safety_critical(tasks, as_of_day):
    """Safety-critical tasks past their interval, whatever the span."""
    lapsed = []
    for record in validate_preventive_plan(tasks, as_of_day):
        if record["safety_critical"] and task_overdue_span(record, as_of_day) > 0:
            lapsed.append(record["task_id"])
    return tuple(sorted(lapsed))


def preventive_currency(tasks, as_of_day):
    """Share of the preventive plan sitting inside its own interval."""
    checked = validate_preventive_plan(tasks, as_of_day)
    current = sum(
        1 for record in checked if task_overdue_span(record, as_of_day) <= 0
    )
    return current / float(len(checked))


def revalidations_outstanding(tasks, as_of_day):
    """Completed tasks that called for a revalidation nobody recorded."""
    return tuple(
        sorted(
            record["task_id"]
            for record in validate_preventive_plan(tasks, as_of_day)
            if record["revalidation_required"] and not record["revalidation_recorded"]
        )
    )


def validate_work_order(order, as_of_day):
    """Read one corrective work order and the priority it was raised at."""
    if not isinstance(order, dict):
        raise ValueError("work order must be a mapping, got %r" % (order,))
    day = _require_count("as_of_day", as_of_day)
    raised = _require_count("raised_day", order.get("raised_day"))
    if raised > day:
        raise ValueError(
            "work order %r was raised on day %d, after the assessment day %d"
            % (order.get("order_id"), raised, day)
        )
    return {
        "order_id": _require_label("order_id", order.get("order_id")),
        "priority": _require_label("priority", order.get("priority")),
        "raised_day": raised,
        "closed": _require_flag("closed", order.get("closed", False)),
    }


def validate_work_orders(orders, as_of_day):
    """Read every corrective order, refusing the same identifier twice."""
    if not isinstance(orders, (list, tuple)):
        raise ValueError("work orders must be a sequence of order records")
    checked = []
    seen = set()
    for order in orders:
        record = validate_work_order(order, as_of_day)
        if record["order_id"] in seen:
            raise ValueError("work order %r appears twice" % record["order_id"])
        seen.add(record["order_id"])
        checked.append(record)
    return tuple(checked)


def work_order_age(order, as_of_day):
    """Days an order has stood open since it was raised."""
    record = validate_work_order(order, as_of_day)
    return _require_count("as_of_day", as_of_day) - record["raised_day"]


def orders_past_allowance(orders, as_of_day, policy=None):
    """Open corrective orders older than the allowance their priority carries."""
    policy = validate_maintenance_policy(policy or DEFAULT_MAINTENANCE_POLICY)
    allowances = policy["close_out_allowance_days"]
    late = []
    for record in validate_work_orders(orders, as_of_day):
        if record["closed"]:
            continue
        if record["priority"] not in allowances:
            raise ValueError(
                "work order %r carries priority %r, which the close-out "
                "allowance does not cover"
                % (record["order_id"], record["priority"])
            )
        allowance = int(allowances[record["priority"]])
        age = work_order_age(record, as_of_day)
        if age > allowance:
            late.append(
                {
                    "order_id": record["order_id"],
                    "priority": record["priority"],
                    "age_days": age,
                    "allowance_days": allowance,
                }
            )
    return tuple(sorted(late, key=lambda item: (-item["age_days"], item["order_id"])))


def assess_facility_maintenance(case):
    """Grade a facility's maintenance state and say what it obliges."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_maintenance_policy(
        case.get("policy") or DEFAULT_MAINTENANCE_POLICY
    )

    findings = []
    advisories = []
    result = {
        "tasks_planned": 0,
        "preventive_currency": None,
        "overdue_tasks": (),
        "lapsed_safety_critical": (),
        "revalidations_outstanding": (),
        "orders_past_allowance": (),
        "worst_overdue_days": None,
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    facility = case.get("facility")
    if facility is None:
        findings.append(
            "no facility record was supplied, so there is no maintenance "
            "state to release from"
        )
        result["verdict"] = NO_MAINTENANCE_PLAN
        return result
    if not isinstance(facility, dict):
        raise ValueError("facility must be a mapping, got %r" % (facility,))

    tasks = facility.get("preventive_tasks")
    if not tasks:
        findings.append(
            "the facility carries no preventive maintenance plan, so nothing "
            "can be overdue against anything and nothing is proven current"
        )
        result["verdict"] = NO_MAINTENANCE_PLAN
        return result

    as_of_day = _require_count("as_of_day", facility.get("as_of_day"))
    checked = validate_preventive_plan(tasks, as_of_day)
    result["tasks_planned"] = len(checked)
    result["preventive_currency"] = preventive_currency(checked, as_of_day)
    result["overdue_tasks"] = overdue_tasks(checked, as_of_day)
    result["worst_overdue_days"] = (
        result["overdue_tasks"][0]["overdue_days"] if result["overdue_tasks"] else 0
    )

    lapsed = lapsed_safety_critical(checked, as_of_day)
    result["lapsed_safety_critical"] = lapsed
    if lapsed:
        findings.append(
            "safety-critical task(s) %s have run past their interval, which "
            "holds the facility whatever the rest of the plan shows"
            % ", ".join(lapsed)
        )
        result["verdict"] = SAFETY_CRITICAL_LAPSED
        return result

    outstanding = revalidations_outstanding(checked, as_of_day)
    result["revalidations_outstanding"] = outstanding
    if outstanding:
        findings.append(
            "completed task(s) %s called for a revalidation that is not "
            "recorded, so the facility is unproven after the work"
            % ", ".join(outstanding)
        )
        result["verdict"] = REVALIDATION_OUTSTANDING
        return result

    late = orders_past_allowance(facility.get("work_orders", ()), as_of_day, policy)
    result["orders_past_allowance"] = late
    if late:
        findings.append(
            "corrective order(s) stand past their close-out allowance: %s"
            % ", ".join(
                "%s at %d day(s) against %d"
                % (entry["order_id"], entry["age_days"], entry["allowance_days"])
                for entry in late
            )
        )
        result["verdict"] = CORRECTIVE_PAST_ALLOWANCE
        return result

    if not _at_least(
        result["preventive_currency"], float(policy["min_preventive_currency"])
    ):
        findings.append(
            "%d of %d preventive task(s) have lapsed, leaving the plan at "
            "%.3g current against the %.3g the test centre requires"
            % (
                len(result["overdue_tasks"]),
                len(checked),
                result["preventive_currency"],
                float(policy["min_preventive_currency"]),
            )
        )
        result["verdict"] = PREVENTIVE_CURRENCY_SHORT
        return result

    tolerance = int(policy["routine_overdue_tolerance_days"])
    if result["worst_overdue_days"] > tolerance:
        findings.append(
            "routine task %s has run %d day(s) past its interval against the "
            "%d day(s) tolerated"
            % (
                result["overdue_tasks"][0]["task_id"],
                result["worst_overdue_days"],
                tolerance,
            )
        )
        result["verdict"] = ROUTINE_TASK_OVERDUE
        return result

    if result["overdue_tasks"]:
        advisories.append(
            "%d routine task(s) sit inside the %d day tolerance but are past "
            "their interval" % (len(result["overdue_tasks"]), tolerance)
        )

    result["verdict"] = RELEASED_TO_SERVICE
    return result
