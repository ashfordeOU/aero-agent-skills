#!/usr/bin/env python3
"""Contract tests for facility maintenance control, clause 5.6.4.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused policy,
a facility with no plan, a task last done in the future, per-task
overdue spans, a lapsed safety-critical task outranking a larger routine
span, a revalidation nobody recorded, a corrective order past the
allowance its priority carries, and preventive currency short.
"""

import unittest

from q2007_tf_maintenance_logic import (
    CORRECTIVE_PAST_ALLOWANCE,
    DEFAULT_MAINTENANCE_POLICY,
    NO_MAINTENANCE_PLAN,
    PREVENTIVE_CURRENCY_SHORT,
    RELEASED_TO_SERVICE,
    REVALIDATION_OUTSTANDING,
    ROUTINE_TASK_OVERDUE,
    SAFETY_CRITICAL_LAPSED,
    assess_facility_maintenance,
    lapsed_safety_critical,
    orders_past_allowance,
    overdue_tasks,
    preventive_currency,
    revalidations_outstanding,
    task_overdue_span,
    validate_maintenance_policy,
    validate_preventive_plan,
    validate_preventive_task,
    validate_work_order,
    validate_work_orders,
    work_order_age,
)

AS_OF = 400


def _policy(**overrides):
    policy = dict(DEFAULT_MAINTENANCE_POLICY)
    policy["close_out_allowance_days"] = dict(
        DEFAULT_MAINTENANCE_POLICY["close_out_allowance_days"]
    )
    policy.update(overrides)
    return policy


def _tasks():
    return [
        {
            "task_id": "chamber-pump-seal-replacement",
            "interval_days": 90,
            "last_done_day": 340,
        },
        {
            "task_id": "overhead-crane-load-inspection",
            "interval_days": 365,
            "last_done_day": 100,
            "safety_critical": True,
        },
        {
            "task_id": "interlock-function-check",
            "interval_days": 30,
            "last_done_day": 380,
            "safety_critical": True,
        },
        {
            "task_id": "chiller-filter-change",
            "interval_days": 180,
            "last_done_day": 240,
        },
    ]


def _orders():
    return [
        {
            "order_id": "wo-501",
            "priority": "high",
            "raised_day": 390,
            "closed": False,
        },
        {
            "order_id": "wo-490",
            "priority": "low",
            "raised_day": 350,
            "closed": False,
        },
        {
            "order_id": "wo-410",
            "priority": "high",
            "raised_day": 100,
            "closed": True,
        },
    ]


def _facility(**overrides):
    facility = {
        "preventive_tasks": _tasks(),
        "work_orders": _orders(),
        "as_of_day": AS_OF,
    }
    facility.update(overrides)
    return facility


def _case(**overrides):
    case = {"policy": _policy(), "facility": _facility()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_maintenance_policy(DEFAULT_MAINTENANCE_POLICY),
            DEFAULT_MAINTENANCE_POLICY,
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_maintenance_policy(30)

    def test_a_negative_overdue_tolerance_refused(self):
        with self.assertRaises(ValueError):
            validate_maintenance_policy(_policy(routine_overdue_tolerance_days=-1))

    def test_an_empty_close_out_table_refused(self):
        with self.assertRaises(ValueError):
            validate_maintenance_policy(_policy(close_out_allowance_days={}))

    def test_a_negative_close_out_allowance_refused(self):
        with self.assertRaises(ValueError):
            validate_maintenance_policy(
                _policy(close_out_allowance_days={"high": -3})
            )

    def test_a_currency_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_maintenance_policy(_policy(min_preventive_currency=1.5))


class TaskValidationTests(unittest.TestCase):
    def test_task_is_read_back(self):
        record = validate_preventive_task(_tasks()[0], AS_OF)
        self.assertEqual(record["interval_days"], 90)
        self.assertFalse(record["safety_critical"])

    def test_a_zero_interval_refused(self):
        task = _tasks()[0]
        task["interval_days"] = 0
        with self.assertRaises(ValueError):
            validate_preventive_task(task, AS_OF)

    def test_a_task_last_done_in_the_future_refused(self):
        task = _tasks()[0]
        task["last_done_day"] = AS_OF + 10
        with self.assertRaises(ValueError):
            validate_preventive_task(task, AS_OF)

    def test_a_non_boolean_safety_flag_refused(self):
        task = _tasks()[0]
        task["safety_critical"] = "yes"
        with self.assertRaises(ValueError):
            validate_preventive_task(task, AS_OF)

    def test_the_same_task_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_preventive_plan(_tasks() + [_tasks()[0]], AS_OF)

    def test_an_empty_plan_refused(self):
        with self.assertRaises(ValueError):
            validate_preventive_plan([], AS_OF)


class SpanTests(unittest.TestCase):
    def test_a_task_inside_its_interval_has_time_in_hand(self):
        self.assertEqual(task_overdue_span(_tasks()[0], AS_OF), -30)

    def test_each_task_is_aged_against_its_own_interval(self):
        tasks = _tasks()
        self.assertEqual(task_overdue_span(tasks[1], AS_OF), -65)
        self.assertEqual(task_overdue_span(tasks[2], AS_OF), -10)

    def test_a_lapsed_task_has_a_positive_span(self):
        task = _tasks()[3]
        task["last_done_day"] = 200
        self.assertEqual(task_overdue_span(task, AS_OF), 20)

    def test_overdue_tasks_are_ordered_worst_span_first(self):
        tasks = _tasks()
        tasks[0]["last_done_day"] = 300
        tasks[3]["last_done_day"] = 200
        ordered = overdue_tasks(tasks, AS_OF)
        self.assertEqual(ordered[0]["task_id"], "chiller-filter-change")
        self.assertEqual(ordered[0]["overdue_days"], 20)
        self.assertEqual(ordered[1]["task_id"], "chamber-pump-seal-replacement")
        self.assertEqual(ordered[1]["overdue_days"], 10)
        self.assertEqual(len(ordered), 2)

    def test_a_current_plan_has_no_overdue_tasks(self):
        self.assertEqual(overdue_tasks(_tasks(), AS_OF), ())

    def test_currency_is_the_share_inside_interval(self):
        tasks = _tasks()
        tasks[3]["last_done_day"] = 200
        self.assertAlmostEqual(preventive_currency(tasks, AS_OF), 0.75, places=9)

    def test_a_lapsed_safety_critical_task_is_separated(self):
        tasks = _tasks()
        tasks[2]["last_done_day"] = 360
        self.assertEqual(
            lapsed_safety_critical(tasks, AS_OF), ("interlock-function-check",)
        )

    def test_a_current_safety_critical_task_is_not_separated(self):
        self.assertEqual(lapsed_safety_critical(_tasks(), AS_OF), ())


class RevalidationTests(unittest.TestCase):
    def test_a_task_needing_no_revalidation_is_not_outstanding(self):
        self.assertEqual(revalidations_outstanding(_tasks(), AS_OF), ())

    def test_a_recorded_revalidation_closes_the_task(self):
        tasks = _tasks()
        tasks[0]["revalidation_required"] = True
        tasks[0]["revalidation_recorded"] = True
        self.assertEqual(revalidations_outstanding(tasks, AS_OF), ())

    def test_a_missing_revalidation_is_outstanding(self):
        tasks = _tasks()
        tasks[0]["revalidation_required"] = True
        self.assertEqual(
            revalidations_outstanding(tasks, AS_OF),
            ("chamber-pump-seal-replacement",),
        )


class WorkOrderTests(unittest.TestCase):
    def test_order_is_read_back(self):
        record = validate_work_order(_orders()[0], AS_OF)
        self.assertEqual(record["priority"], "high")
        self.assertFalse(record["closed"])

    def test_an_order_raised_in_the_future_refused(self):
        order = _orders()[0]
        order["raised_day"] = AS_OF + 1
        with self.assertRaises(ValueError):
            validate_work_order(order, AS_OF)

    def test_the_same_order_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_work_orders(_orders() + [_orders()[0]], AS_OF)

    def test_order_age_runs_from_the_day_it_was_raised(self):
        self.assertEqual(work_order_age(_orders()[1], AS_OF), 50)

    def test_an_order_inside_its_allowance_is_not_late(self):
        self.assertEqual(orders_past_allowance(_orders(), AS_OF), ())

    def test_a_high_priority_order_goes_late_before_a_low_one(self):
        orders = _orders()
        orders[0]["raised_day"] = 380
        late = orders_past_allowance(orders, AS_OF)
        self.assertEqual(late[0]["order_id"], "wo-501")
        self.assertEqual(late[0]["allowance_days"], 14)

    def test_a_closed_order_is_never_late(self):
        orders = _orders()
        orders[0]["raised_day"] = 100
        orders[0]["closed"] = True
        self.assertEqual(orders_past_allowance(orders, AS_OF), ())

    def test_an_uncovered_priority_is_refused(self):
        orders = _orders()
        orders[0]["priority"] = "emergency"
        with self.assertRaises(ValueError):
            orders_past_allowance(orders, AS_OF)


class AssessmentTests(unittest.TestCase):
    def test_a_maintained_facility_is_released(self):
        result = assess_facility_maintenance(_case())
        self.assertEqual(result["verdict"], RELEASED_TO_SERVICE)
        self.assertEqual(result["tasks_planned"], 4)
        self.assertAlmostEqual(result["preventive_currency"], 1.0, places=9)

    def test_no_facility_at_all_stops_the_assessment(self):
        result = assess_facility_maintenance(_case(facility=None))
        self.assertEqual(result["verdict"], NO_MAINTENANCE_PLAN)

    def test_an_empty_plan_is_not_a_clean_plan(self):
        result = assess_facility_maintenance(
            _case(facility=_facility(preventive_tasks=[]))
        )
        self.assertEqual(result["verdict"], NO_MAINTENANCE_PLAN)

    def test_a_lapsed_safety_critical_task_outranks_a_larger_routine_span(self):
        tasks = _tasks()
        tasks[2]["last_done_day"] = 368
        tasks[3]["last_done_day"] = 150
        result = assess_facility_maintenance(
            _case(facility=_facility(preventive_tasks=tasks))
        )
        self.assertEqual(result["verdict"], SAFETY_CRITICAL_LAPSED)
        self.assertEqual(result["worst_overdue_days"], 70)

    def test_an_outstanding_revalidation_outranks_a_late_order(self):
        tasks = _tasks()
        tasks[0]["revalidation_required"] = True
        orders = _orders()
        orders[0]["raised_day"] = 300
        result = assess_facility_maintenance(
            _case(facility=_facility(preventive_tasks=tasks, work_orders=orders))
        )
        self.assertEqual(result["verdict"], REVALIDATION_OUTSTANDING)

    def test_a_late_corrective_order_holds_a_current_plan(self):
        orders = _orders()
        orders[0]["raised_day"] = 300
        result = assess_facility_maintenance(
            _case(facility=_facility(work_orders=orders))
        )
        self.assertEqual(result["verdict"], CORRECTIVE_PAST_ALLOWANCE)
        self.assertEqual(result["orders_past_allowance"][0]["age_days"], 100)

    def test_preventive_currency_short_is_reported(self):
        tasks = _tasks()
        tasks[3]["last_done_day"] = 200
        result = assess_facility_maintenance(
            _case(facility=_facility(preventive_tasks=tasks))
        )
        self.assertEqual(result["verdict"], PREVENTIVE_CURRENCY_SHORT)
        self.assertAlmostEqual(result["preventive_currency"], 0.75, places=9)

    def test_currency_exactly_on_its_limit_is_not_short(self):
        tasks = _tasks()
        tasks[3]["last_done_day"] = 200
        result = assess_facility_maintenance(
            _case(
                policy=_policy(min_preventive_currency=0.75),
                facility=_facility(preventive_tasks=tasks),
            )
        )
        self.assertNotEqual(result["verdict"], PREVENTIVE_CURRENCY_SHORT)

    def test_a_routine_task_past_the_tolerated_span_holds_the_release(self):
        tasks = _tasks()
        tasks[3]["last_done_day"] = 200
        result = assess_facility_maintenance(
            _case(
                policy=_policy(min_preventive_currency=0.5),
                facility=_facility(preventive_tasks=tasks),
            )
        )
        self.assertEqual(result["verdict"], ROUTINE_TASK_OVERDUE)
        self.assertEqual(result["worst_overdue_days"], 20)

    def test_a_routine_task_inside_the_tolerance_is_only_advised(self):
        tasks = _tasks()
        tasks[3]["last_done_day"] = 215
        result = assess_facility_maintenance(
            _case(
                policy=_policy(min_preventive_currency=0.5),
                facility=_facility(preventive_tasks=tasks),
            )
        )
        self.assertEqual(result["verdict"], RELEASED_TO_SERVICE)
        self.assertEqual(result["worst_overdue_days"], 5)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_facility_maintenance(("facility",))


if __name__ == "__main__":
    unittest.main()
