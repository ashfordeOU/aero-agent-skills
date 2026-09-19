#!/usr/bin/env python3
"""Contract tests for test process planning, clause 5.7.1.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused policy,
a campaign with no activities, an activity depending on itself, a
predecessor the plan never declares, a dependency graph that closes on
itself, the longest path against the summed durations, a resource
committed past its own capacity, a missing required review and a
customer notified inside the lead the interface owes.
"""

import unittest

from q2007_process_planning_logic import (
    CUSTOMER_NOTIFIED_LATE,
    DEFAULT_PLANNING_POLICY,
    MARGIN_BELOW_REQUIRED,
    PLAN_COMMITTABLE,
    PROCESS_NOT_PLANNED,
    REQUIRED_REVIEW_MISSING,
    RESOURCE_OVER_CAPACITY,
    SCHEDULE_MARGIN_NEGATIVE,
    assess_test_process_plan,
    campaign_duration,
    critical_chain,
    customer_notification_lead,
    earliest_finishes,
    missing_reviews,
    resource_load,
    resources_over_capacity,
    schedule_margin,
    topological_order,
    validate_activities,
    validate_activity,
    validate_planning_policy,
    validate_resource_capacity,
)


def _policy(**overrides):
    policy = dict(DEFAULT_PLANNING_POLICY)
    policy.update(overrides)
    return policy


def _activities():
    return [
        {
            "activity_id": "incoming-inspection",
            "duration_days": 3.0,
            "resource": "receiving-bay",
            "predecessors": [],
        },
        {
            "activity_id": "fixture-integration",
            "duration_days": 5.0,
            "resource": "integration-hall",
            "predecessors": ["incoming-inspection"],
        },
        {
            "activity_id": "instrumentation-setup",
            "duration_days": 4.0,
            "resource": "integration-hall",
            "predecessors": ["incoming-inspection"],
        },
        {
            "activity_id": "vibration-run",
            "duration_days": 6.0,
            "resource": "shaker-a",
            "predecessors": ["fixture-integration", "instrumentation-setup"],
        },
        {
            "activity_id": "thermal-vacuum-run",
            "duration_days": 10.0,
            "resource": "tvac-chamber",
            "predecessors": ["fixture-integration"],
        },
        {
            "activity_id": "data-review-and-report",
            "duration_days": 4.0,
            "resource": "analysis-team",
            "predecessors": ["vibration-run", "thermal-vacuum-run"],
        },
    ]


def _capacity(**overrides):
    capacity = {
        "receiving-bay": 5.0,
        "integration-hall": 12.0,
        "shaker-a": 8.0,
        "tvac-chamber": 14.0,
        "analysis-team": 6.0,
    }
    capacity.update(overrides)
    return capacity


def _plan(**overrides):
    plan = {
        "activities": _activities(),
        "customer_milestone_days": 30.0,
        "resource_capacity": _capacity(),
        "planned_reviews": [
            "test-readiness-review",
            "post-test-review",
            "test-review-board",
        ],
        "campaign_start_day": 100,
        "notification_day": 80,
    }
    plan.update(overrides)
    return plan


def _case(**overrides):
    case = {"policy": _policy(), "plan": _plan()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_planning_policy(DEFAULT_PLANNING_POLICY),
            DEFAULT_PLANNING_POLICY,
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_planning_policy(14)

    def test_a_negative_margin_requirement_refused(self):
        with self.assertRaises(ValueError):
            validate_planning_policy(_policy(required_margin_days=-2.0))

    def test_an_empty_review_list_refused(self):
        with self.assertRaises(ValueError):
            validate_planning_policy(_policy(required_reviews=()))

    def test_a_review_list_that_is_not_a_sequence_refused(self):
        with self.assertRaises(ValueError):
            validate_planning_policy(_policy(required_reviews="trr"))


class ActivityValidationTests(unittest.TestCase):
    def test_activity_is_read_back(self):
        record = validate_activity(_activities()[1])
        self.assertEqual(record["resource"], "integration-hall")
        self.assertEqual(record["predecessors"], ("incoming-inspection",))

    def test_a_zero_duration_refused(self):
        activity = _activities()[0]
        activity["duration_days"] = 0.0
        with self.assertRaises(ValueError):
            validate_activity(activity)

    def test_an_activity_depending_on_itself_refused(self):
        activity = _activities()[1]
        activity["predecessors"] = ["fixture-integration"]
        with self.assertRaises(ValueError):
            validate_activity(activity)

    def test_a_blank_resource_refused(self):
        activity = _activities()[0]
        activity["resource"] = "  "
        with self.assertRaises(ValueError):
            validate_activity(activity)

    def test_a_repeated_predecessor_is_collapsed(self):
        activity = _activities()[3]
        activity["predecessors"] = [
            "fixture-integration",
            "fixture-integration",
            "instrumentation-setup",
        ]
        self.assertEqual(len(validate_activity(activity)["predecessors"]), 2)

    def test_the_same_activity_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_activities(_activities() + [_activities()[0]])

    def test_an_empty_activity_set_refused(self):
        with self.assertRaises(ValueError):
            validate_activities([])

    def test_a_predecessor_the_plan_never_declares_refused(self):
        activities = _activities()
        activities[1]["predecessors"] = ["shipping-and-customs"]
        with self.assertRaises(ValueError):
            validate_activities(activities)


class OrderingTests(unittest.TestCase):
    def test_every_predecessor_comes_before_its_activity(self):
        ordered = [record["activity_id"] for record in topological_order(_activities())]
        self.assertLess(
            ordered.index("fixture-integration"), ordered.index("vibration-run")
        )
        self.assertLess(
            ordered.index("incoming-inspection"), ordered.index("fixture-integration")
        )

    def test_a_cyclic_graph_is_refused_not_truncated(self):
        activities = _activities()
        activities[0]["predecessors"] = ["data-review-and-report"]
        with self.assertRaises(ValueError):
            topological_order(activities)


class DurationTests(unittest.TestCase):
    def test_the_campaign_is_the_longest_path(self):
        self.assertAlmostEqual(campaign_duration(_activities()), 22.0, places=9)

    def test_the_campaign_is_below_the_summed_durations(self):
        self.assertLess(campaign_duration(_activities()), 32.0)

    def test_parallel_activities_do_not_both_delay_the_chain(self):
        finishes = earliest_finishes(_activities())
        self.assertAlmostEqual(finishes["instrumentation-setup"], 7.0, places=9)
        self.assertAlmostEqual(finishes["fixture-integration"], 8.0, places=9)
        self.assertAlmostEqual(finishes["vibration-run"], 14.0, places=9)

    def test_the_critical_chain_is_the_path_that_set_the_duration(self):
        self.assertEqual(
            critical_chain(_activities()),
            (
                "incoming-inspection",
                "fixture-integration",
                "thermal-vacuum-run",
                "data-review-and-report",
            ),
        )

    def test_shortening_a_non_critical_activity_does_not_move_the_campaign(self):
        activities = _activities()
        activities[2]["duration_days"] = 1.0
        self.assertAlmostEqual(campaign_duration(activities), 22.0, places=9)

    def test_lengthening_the_critical_activity_moves_the_campaign(self):
        activities = _activities()
        activities[4]["duration_days"] = 14.0
        self.assertAlmostEqual(campaign_duration(activities), 26.0, places=9)


class MarginTests(unittest.TestCase):
    def test_margin_is_the_milestone_less_the_longest_path(self):
        self.assertAlmostEqual(schedule_margin(_activities(), 30.0), 8.0, places=9)

    def test_a_milestone_inside_the_campaign_gives_a_negative_margin(self):
        self.assertAlmostEqual(schedule_margin(_activities(), 20.0), -2.0, places=9)

    def test_a_non_positive_milestone_refused(self):
        with self.assertRaises(ValueError):
            schedule_margin(_activities(), 0.0)


class ResourceTests(unittest.TestCase):
    def test_a_resource_carries_every_activity_assigned_to_it(self):
        self.assertAlmostEqual(
            resource_load(_activities())["integration-hall"], 9.0, places=9
        )

    def test_a_plan_inside_every_capacity_has_nothing_over(self):
        self.assertEqual(resources_over_capacity(_activities(), _capacity()), ())

    def test_a_load_exactly_on_its_capacity_is_not_over(self):
        self.assertEqual(
            resources_over_capacity(
                _activities(), _capacity(**{"integration-hall": 9.0})
            ),
            (),
        )

    def test_one_over_committed_resource_is_named(self):
        over = resources_over_capacity(
            _activities(), _capacity(**{"integration-hall": 8.0})
        )
        self.assertEqual(over[0]["resource"], "integration-hall")
        self.assertAlmostEqual(over[0]["loaded_days"], 9.0, places=9)

    def test_a_resource_with_no_declared_capacity_refused(self):
        capacity = _capacity()
        del capacity["shaker-a"]
        with self.assertRaises(ValueError):
            resources_over_capacity(_activities(), capacity)

    def test_a_non_positive_capacity_refused(self):
        with self.assertRaises(ValueError):
            validate_resource_capacity({"shaker-a": 0.0})


class InterfaceTests(unittest.TestCase):
    def test_a_plan_naming_every_required_review_misses_none(self):
        self.assertEqual(
            missing_reviews(["test-readiness-review", "post-test-review"]), ()
        )

    def test_a_missing_review_is_named(self):
        self.assertEqual(
            missing_reviews(["test-readiness-review"]), ("post-test-review",)
        )

    def test_the_notification_lead_runs_back_from_the_campaign_start(self):
        self.assertEqual(customer_notification_lead(80, 100), 20)

    def test_a_notification_after_the_start_refused(self):
        with self.assertRaises(ValueError):
            customer_notification_lead(110, 100)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_plan_is_committable(self):
        result = assess_test_process_plan(_case())
        self.assertEqual(result["verdict"], PLAN_COMMITTABLE)
        self.assertEqual(result["activities"], 6)
        self.assertAlmostEqual(result["campaign_duration_days"], 22.0, places=9)
        self.assertAlmostEqual(result["schedule_margin_days"], 8.0, places=9)

    def test_no_plan_at_all_stops_the_assessment(self):
        result = assess_test_process_plan(_case(plan=None))
        self.assertEqual(result["verdict"], PROCESS_NOT_PLANNED)

    def test_a_plan_with_no_activities_is_not_a_zero_length_campaign(self):
        result = assess_test_process_plan(_case(plan=_plan(activities=[])))
        self.assertEqual(result["verdict"], PROCESS_NOT_PLANNED)

    def test_a_missing_review_outranks_a_negative_margin(self):
        result = assess_test_process_plan(
            _case(
                plan=_plan(
                    planned_reviews=["test-readiness-review"],
                    customer_milestone_days=20.0,
                )
            )
        )
        self.assertEqual(result["verdict"], REQUIRED_REVIEW_MISSING)
        self.assertEqual(result["missing_reviews"], ("post-test-review",))

    def test_a_negative_margin_outranks_an_over_committed_resource(self):
        result = assess_test_process_plan(
            _case(
                plan=_plan(
                    customer_milestone_days=20.0,
                    resource_capacity=_capacity(**{"integration-hall": 8.0}),
                )
            )
        )
        self.assertEqual(result["verdict"], SCHEDULE_MARGIN_NEGATIVE)

    def test_an_over_committed_resource_outranks_a_late_notification(self):
        result = assess_test_process_plan(
            _case(
                plan=_plan(
                    resource_capacity=_capacity(**{"integration-hall": 8.0}),
                    notification_day=95,
                )
            )
        )
        self.assertEqual(result["verdict"], RESOURCE_OVER_CAPACITY)

    def test_a_late_customer_notification_is_reported(self):
        result = assess_test_process_plan(_case(plan=_plan(notification_day=95)))
        self.assertEqual(result["verdict"], CUSTOMER_NOTIFIED_LATE)
        self.assertEqual(result["notification_lead_days"], 5)

    def test_margin_below_the_required_span_is_an_advisory(self):
        result = assess_test_process_plan(
            _case(plan=_plan(customer_milestone_days=25.0))
        )
        self.assertEqual(result["verdict"], MARGIN_BELOW_REQUIRED)
        self.assertEqual(len(result["advisories"]), 1)

    def test_margin_exactly_on_the_required_span_is_committable(self):
        result = assess_test_process_plan(
            _case(plan=_plan(customer_milestone_days=27.0))
        )
        self.assertEqual(result["verdict"], PLAN_COMMITTABLE)
        self.assertAlmostEqual(result["schedule_margin_days"], 5.0, places=9)

    def test_a_plan_with_no_declared_capacity_refused(self):
        plan = _plan()
        del plan["resource_capacity"]
        with self.assertRaises(ValueError):
            assess_test_process_plan(_case(plan=plan))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_test_process_plan(["plan"])


if __name__ == "__main__":
    unittest.main()
