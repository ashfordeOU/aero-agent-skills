#!/usr/bin/env python3
"""Contract test for the microwave die development plan review item (offline)."""

import copy
import unittest

from q6012_development_plan_review_item_logic import (
    MILESTONE_UNREACHABLE,
    MILESTONE_WITHOUT_FLOAT,
    MILESTONES_REACHABLE,
    RESOURCE_ADEQUATE,
    RESOURCE_OVER,
    RESOURCE_TIGHT,
    SCHEDULE_ADEQUATE,
    SCHEDULE_INFEASIBLE,
    SCHEDULE_THIN,
    VERDICT_ACTIONED,
    VERDICT_CLOSED,
    VERDICT_REJECTED,
    assess_milestones,
    assess_resources,
    assess_schedule,
    critical_path_activities,
    normalize_activities,
    normalize_milestones,
    peak_resource_loading,
    plan_finish_day,
    resource_loading_profile,
    review_development_plan_item,
    schedule_activities,
    schedule_margin_days,
)

REFERENCE_ACTIVITIES = [
    {
        "activity_id": "act-a-layout-freeze",
        "duration_days": 10.0,
        "effort_person_days": 20.0,
        "predecessors": [],
    },
    {
        "activity_id": "act-b-mask-set",
        "duration_days": 15.0,
        "effort_person_days": 30.0,
        "predecessors": ["act-a-layout-freeze"],
    },
    {
        "activity_id": "act-c-test-fixture",
        "duration_days": 8.0,
        "effort_person_days": 8.0,
        "predecessors": ["act-a-layout-freeze"],
    },
    {
        "activity_id": "act-d-wafer-lot",
        "duration_days": 5.0,
        "effort_person_days": 10.0,
        "predecessors": ["act-b-mask-set", "act-c-test-fixture"],
    },
]

REFERENCE_MILESTONES = [
    {
        "milestone_id": "ms-fixture-ready",
        "day": 20.0,
        "activity_ids": ["act-c-test-fixture"],
    },
    {
        "milestone_id": "ms-lot-released",
        "day": 34.0,
        "activity_ids": ["act-d-wafer-lot"],
    },
]

REFERENCE_CASE = {
    "activities": REFERENCE_ACTIVITIES,
    "milestones": REFERENCE_MILESTONES,
    "committed_finish_day": 36.0,
    "capacity_persons": 4.0,
}


def _case(**overrides):
    case = copy.deepcopy(REFERENCE_CASE)
    case.update(overrides)
    return case


def _plan():
    return normalize_activities(copy.deepcopy(REFERENCE_ACTIVITIES))


class NormalizeActivityTests(unittest.TestCase):
    def test_activities_come_back_in_identifier_order(self):
        plan = _plan()
        self.assertEqual(
            [activity["activity_id"] for activity in plan],
            [
                "act-a-layout-freeze",
                "act-b-mask-set",
                "act-c-test-fixture",
                "act-d-wafer-lot",
            ],
        )

    def test_predecessors_are_normalized_to_a_tuple(self):
        plan = _plan()
        last = plan[-1]
        self.assertEqual(
            last["predecessors"], ("act-b-mask-set", "act-c-test-fixture")
        )

    def test_repeated_predecessor_is_collapsed(self):
        plan = normalize_activities(
            [
                {"activity_id": "a", "duration_days": 2.0, "effort_person_days": 2.0},
                {
                    "activity_id": "b",
                    "duration_days": 3.0,
                    "effort_person_days": 3.0,
                    "predecessors": ["a", "a"],
                },
            ]
        )
        self.assertEqual(plan[1]["predecessors"], ("a",))

    def test_effort_defaults_to_zero_when_not_stated(self):
        plan = normalize_activities(
            [{"activity_id": "a", "duration_days": 2.0}]
        )
        self.assertAlmostEqual(plan[0]["effort_person_days"], 0.0, places=9)

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activities([])

    def test_duplicate_activity_identifier_rejected(self):
        rows = copy.deepcopy(REFERENCE_ACTIVITIES)
        rows.append(copy.deepcopy(REFERENCE_ACTIVITIES[0]))
        with self.assertRaises(ValueError):
            normalize_activities(rows)

    def test_zero_duration_activity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activities(
                [{"activity_id": "a", "duration_days": 0.0, "effort_person_days": 1.0}]
            )

    def test_negative_effort_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activities(
                [{"activity_id": "a", "duration_days": 2.0, "effort_person_days": -1.0}]
            )

    def test_unknown_activity_field_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activities(
                [
                    {
                        "activity_id": "a",
                        "duration_days": 2.0,
                        "effort_person_days": 1.0,
                        "owner": "the team",
                    }
                ]
            )

    def test_dangling_predecessor_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activities(
                [
                    {
                        "activity_id": "a",
                        "duration_days": 2.0,
                        "predecessors": ["not-in-the-plan"],
                    }
                ]
            )

    def test_self_dependency_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activities(
                [{"activity_id": "a", "duration_days": 2.0, "predecessors": ["a"]}]
            )

    def test_blank_activity_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activities([{"activity_id": "   ", "duration_days": 2.0}])


class ScheduleTests(unittest.TestCase):
    def test_an_activity_with_no_predecessor_starts_at_day_zero(self):
        schedule = schedule_activities(_plan())
        self.assertAlmostEqual(
            schedule["act-a-layout-freeze"]["early_start"], 0.0, places=9
        )

    def test_a_successor_waits_for_its_latest_predecessor(self):
        schedule = schedule_activities(_plan())
        self.assertAlmostEqual(
            schedule["act-d-wafer-lot"]["early_start"], 25.0, places=9
        )

    def test_parallel_branches_share_a_start(self):
        schedule = schedule_activities(_plan())
        self.assertAlmostEqual(
            schedule["act-b-mask-set"]["early_start"],
            schedule["act-c-test-fixture"]["early_start"],
            places=9,
        )

    def test_plan_finish_is_the_latest_early_finish(self):
        schedule = schedule_activities(_plan())
        self.assertAlmostEqual(plan_finish_day(schedule), 30.0, places=9)

    def test_dependency_cycle_rejected(self):
        activities = (
            {
                "activity_id": "a",
                "duration_days": 2.0,
                "effort_person_days": 1.0,
                "predecessors": ("b",),
            },
            {
                "activity_id": "b",
                "duration_days": 2.0,
                "effort_person_days": 1.0,
                "predecessors": ("a",),
            },
        )
        with self.assertRaises(ValueError):
            schedule_activities(activities)

    def test_empty_schedule_has_no_finish_day(self):
        with self.assertRaises(ValueError):
            plan_finish_day({})

    def test_fractional_durations_accumulate_without_being_rounded(self):
        plan = normalize_activities(
            [
                {"activity_id": "a", "duration_days": 0.1},
                {"activity_id": "b", "duration_days": 0.2, "predecessors": ["a"]},
            ]
        )
        schedule = schedule_activities(plan)
        self.assertAlmostEqual(plan_finish_day(schedule), 0.3, places=9)


class CriticalPathTests(unittest.TestCase):
    def test_critical_path_runs_through_the_longest_branch(self):
        plan = _plan()
        schedule = schedule_activities(plan)
        self.assertEqual(
            critical_path_activities(plan, schedule),
            ("act-a-layout-freeze", "act-b-mask-set", "act-d-wafer-lot"),
        )

    def test_critical_path_excludes_the_branch_with_float(self):
        plan = _plan()
        schedule = schedule_activities(plan)
        self.assertNotIn(
            "act-c-test-fixture", critical_path_activities(plan, schedule)
        )

    def test_a_single_activity_plan_is_its_own_critical_path(self):
        plan = normalize_activities([{"activity_id": "solo", "duration_days": 4.0}])
        schedule = schedule_activities(plan)
        self.assertEqual(critical_path_activities(plan, schedule), ("solo",))


class ScheduleAssessmentTests(unittest.TestCase):
    def test_margin_is_the_commitment_less_the_earliest_finish(self):
        self.assertAlmostEqual(schedule_margin_days(30.0, 36.0), 6.0, places=9)

    def test_negative_commitment_day_rejected(self):
        with self.assertRaises(ValueError):
            schedule_margin_days(30.0, -1.0)

    def test_reference_plan_carries_adequate_float(self):
        result = assess_schedule(_plan(), 36.0)
        self.assertEqual(result["status"], SCHEDULE_ADEQUATE)
        self.assertAlmostEqual(result["margin_days"], 6.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_float_below_the_policy_share_is_thin(self):
        result = assess_schedule(_plan(), 31.0)
        self.assertEqual(result["status"], SCHEDULE_THIN)
        self.assertAlmostEqual(result["required_margin_days"], 3.0, places=9)

    def test_float_exactly_on_the_policy_share_is_adequate(self):
        # 30 * 0.10 does not evaluate to exactly 3.0, so a strict comparison
        # would call a plan holding precisely the required float thin.
        result = assess_schedule(_plan(), 33.0)
        self.assertAlmostEqual(result["margin_days"], 3.0, places=9)
        self.assertAlmostEqual(result["required_margin_days"], 3.0, places=9)
        self.assertEqual(result["status"], SCHEDULE_ADEQUATE)

    def test_finish_past_the_commitment_is_infeasible(self):
        result = assess_schedule(_plan(), 29.0)
        self.assertEqual(result["status"], SCHEDULE_INFEASIBLE)
        self.assertTrue(any("commitment" in f for f in result["findings"]))

    def test_finish_exactly_on_the_commitment_is_thin_not_infeasible(self):
        result = assess_schedule(_plan(), 30.0)
        self.assertAlmostEqual(result["margin_days"], 0.0, places=9)
        self.assertEqual(result["status"], SCHEDULE_THIN)

    def test_margin_fraction_outside_the_unit_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_schedule(_plan(), 36.0, 1.4)


class ResourceLoadingTests(unittest.TestCase):
    def test_profile_segments_cover_the_whole_span(self):
        plan = _plan()
        segments = resource_loading_profile(plan, schedule_activities(plan))
        self.assertAlmostEqual(segments[0]["start_day"], 0.0, places=9)
        self.assertAlmostEqual(segments[-1]["end_day"], 30.0, places=9)

    def test_overlapping_activities_add_their_rates(self):
        plan = _plan()
        segments = resource_loading_profile(plan, schedule_activities(plan))
        overlap = [s for s in segments if s["start_day"] == 10.0][0]
        self.assertAlmostEqual(overlap["persons"], 3.0, places=9)

    def test_peak_is_the_highest_segment_not_the_average(self):
        plan = _plan()
        self.assertAlmostEqual(
            peak_resource_loading(plan, schedule_activities(plan)), 3.0, places=9
        )

    def test_capacity_above_the_peak_is_adequate(self):
        plan = _plan()
        result = assess_resources(plan, schedule_activities(plan), 4.0)
        self.assertEqual(result["status"], RESOURCE_ADEQUATE)
        self.assertAlmostEqual(result["utilization"], 0.75, places=9)

    def test_capacity_exactly_on_the_peak_is_tight_not_over(self):
        plan = _plan()
        result = assess_resources(plan, schedule_activities(plan), 3.0)
        self.assertAlmostEqual(result["utilization"], 1.0, places=9)
        self.assertEqual(result["status"], RESOURCE_TIGHT)

    def test_capacity_below_the_peak_is_over_committed(self):
        plan = _plan()
        result = assess_resources(plan, schedule_activities(plan), 2.5)
        self.assertEqual(result["status"], RESOURCE_OVER)
        self.assertTrue(any("capacity" in f for f in result["findings"]))

    def test_zero_capacity_rejected(self):
        plan = _plan()
        with self.assertRaises(ValueError):
            assess_resources(plan, schedule_activities(plan), 0.0)

    def test_a_plan_with_no_effort_demands_nobody(self):
        plan = normalize_activities([{"activity_id": "a", "duration_days": 4.0}])
        self.assertAlmostEqual(
            peak_resource_loading(plan, schedule_activities(plan)), 0.0, places=9
        )


class MilestoneTests(unittest.TestCase):
    def test_milestones_come_back_in_identifier_order(self):
        plan = _plan()
        rows = normalize_milestones(copy.deepcopy(REFERENCE_MILESTONES), plan)
        self.assertEqual(
            [row["milestone_id"] for row in rows],
            ["ms-fixture-ready", "ms-lot-released"],
        )

    def test_milestone_naming_no_activity_rejected(self):
        plan = _plan()
        with self.assertRaises(ValueError):
            normalize_milestones([{"milestone_id": "ms-empty", "day": 5.0}], plan)

    def test_milestone_naming_an_unlisted_activity_rejected(self):
        plan = _plan()
        with self.assertRaises(ValueError):
            normalize_milestones(
                [
                    {
                        "milestone_id": "ms-ghost",
                        "day": 5.0,
                        "activity_ids": ["act-z-unknown"],
                    }
                ],
                plan,
            )

    def test_duplicate_milestone_identifier_rejected(self):
        plan = _plan()
        rows = copy.deepcopy(REFERENCE_MILESTONES)
        rows.append(copy.deepcopy(REFERENCE_MILESTONES[0]))
        with self.assertRaises(ValueError):
            normalize_milestones(rows, plan)

    def test_reference_milestones_are_reachable(self):
        plan = _plan()
        result = assess_milestones(
            copy.deepcopy(REFERENCE_MILESTONES), plan, schedule_activities(plan)
        )
        self.assertEqual(result["status"], MILESTONES_REACHABLE)
        self.assertEqual(result["findings"], [])

    def test_milestone_before_its_work_is_unreachable(self):
        plan = _plan()
        rows = copy.deepcopy(REFERENCE_MILESTONES)
        rows[0]["day"] = 17.0
        result = assess_milestones(rows, plan, schedule_activities(plan))
        self.assertEqual(result["status"], MILESTONE_UNREACHABLE)
        self.assertEqual(result["unreachable"], ("ms-fixture-ready",))

    def test_milestone_on_the_earliest_finish_carries_no_float(self):
        plan = _plan()
        rows = copy.deepcopy(REFERENCE_MILESTONES)
        rows[0]["day"] = 18.0
        result = assess_milestones(rows, plan, schedule_activities(plan))
        self.assertEqual(result["status"], MILESTONE_WITHOUT_FLOAT)
        self.assertEqual(result["without_float"], ("ms-fixture-ready",))

    def test_a_milestone_on_an_inexact_finish_is_not_read_as_unreachable(self):
        # 0.1 + 0.2 lands just above 0.3, so a strict comparison would call a
        # milestone placed on the stated finish day unreachable.
        plan = normalize_activities(
            [
                {"activity_id": "a", "duration_days": 0.1},
                {"activity_id": "b", "duration_days": 0.2, "predecessors": ["a"]},
            ]
        )
        schedule = schedule_activities(plan)
        result = assess_milestones(
            [{"milestone_id": "ms-x", "day": 0.3, "activity_ids": ["b"]}],
            plan,
            schedule,
        )
        self.assertEqual(result["status"], MILESTONE_WITHOUT_FLOAT)
        self.assertAlmostEqual(result["milestones"][0]["float_days"], 0.0, places=9)

    def test_milestone_float_is_reported_per_milestone(self):
        plan = _plan()
        result = assess_milestones(
            copy.deepcopy(REFERENCE_MILESTONES), plan, schedule_activities(plan)
        )
        floats = {row["milestone_id"]: row["float_days"] for row in result["milestones"]}
        self.assertAlmostEqual(floats["ms-fixture-ready"], 2.0, places=9)
        self.assertAlmostEqual(floats["ms-lot-released"], 4.0, places=9)


class ReviewItemTests(unittest.TestCase):
    def test_reference_case_closes_the_item(self):
        result = review_development_plan_item(REFERENCE_CASE)
        self.assertEqual(result["verdict"], VERDICT_CLOSED)
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["findings"], [])

    def test_thin_schedule_float_leaves_an_action(self):
        result = review_development_plan_item(_case(committed_finish_day=31.0))
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("float" in action for action in result["actions"]))

    def test_commitment_before_the_earliest_finish_rejects_the_item(self):
        result = review_development_plan_item(_case(committed_finish_day=29.0))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["schedule"]["status"], SCHEDULE_INFEASIBLE)

    def test_tight_loading_leaves_an_action(self):
        result = review_development_plan_item(_case(capacity_persons=3.0))
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertEqual(result["resources"]["status"], RESOURCE_TIGHT)

    def test_loading_beyond_capacity_rejects_the_item(self):
        result = review_development_plan_item(_case(capacity_persons=2.0))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["resources"]["status"], RESOURCE_OVER)

    def test_unreachable_milestone_rejects_the_item(self):
        rows = copy.deepcopy(REFERENCE_MILESTONES)
        rows[0]["day"] = 12.0
        result = review_development_plan_item(_case(milestones=rows))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)

    def test_zero_float_milestone_leaves_an_action(self):
        rows = copy.deepcopy(REFERENCE_MILESTONES)
        rows[0]["day"] = 18.0
        result = review_development_plan_item(_case(milestones=rows))
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)

    def test_plan_with_no_milestones_still_reviews(self):
        result = review_development_plan_item(_case(milestones=[]))
        self.assertEqual(result["verdict"], VERDICT_CLOSED)
        self.assertEqual(result["milestones"]["milestones"], ())

    def test_critical_path_is_reported_with_the_verdict(self):
        result = review_development_plan_item(REFERENCE_CASE)
        self.assertEqual(
            result["schedule"]["critical_path"],
            ("act-a-layout-freeze", "act-b-mask-set", "act-d-wafer-lot"),
        )

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            review_development_plan_item("act-a-layout-freeze")

    def test_missing_capacity_rejected(self):
        case = _case()
        del case["capacity_persons"]
        with self.assertRaises(ValueError):
            review_development_plan_item(case)

    def test_missing_commitment_day_rejected(self):
        case = _case()
        del case["committed_finish_day"]
        with self.assertRaises(ValueError):
            review_development_plan_item(case)

    def test_several_findings_are_reported_together(self):
        result = review_development_plan_item(
            _case(committed_finish_day=29.0, capacity_persons=2.0)
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertGreaterEqual(len(result["findings"]), 2)


if __name__ == "__main__":
    unittest.main()
