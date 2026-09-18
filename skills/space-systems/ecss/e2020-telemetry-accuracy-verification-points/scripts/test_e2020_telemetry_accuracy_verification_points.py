#!/usr/bin/env python3
"""Contract test for the telemetry accuracy verification points (offline)."""

import copy
import unittest

from e2020_telemetry_accuracy_verification_points_logic import (
    DEFAULT_VERIFICATION_POLICY,
    POINTS_COMPLETE,
    POINTS_INCOMPLETE,
    assess_verification_points,
    coverage_report,
    duplicate_points_a,
    low_end_points_a,
    nearest_point_a,
    required_points_a,
    validate_verification_policy,
)

GOOD_PLAN = {
    "full_scale_a": 10.0,
    "proposed_points_a": [0.0, 1.0, 2.5, 3.2, 5.0, 7.5, 8.4, 10.0],
    "operating_points_a": [3.2, 8.4],
}

SPARSE_PLAN = {
    "full_scale_a": 10.0,
    "proposed_points_a": [5.0, 10.0],
    "operating_points_a": [],
}

TOP_HEAVY_PLAN = {
    "full_scale_a": 10.0,
    "proposed_points_a": [0.0, 2.5, 5.0, 7.5, 10.0],
    "operating_points_a": [],
}


def _plan(base, **overrides):
    plan = copy.deepcopy(base)
    plan.update(overrides)
    return plan


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_verification_policy(DEFAULT_VERIFICATION_POLICY),
            DEFAULT_VERIFICATION_POLICY,
        )

    def test_default_policy_covers_no_load_and_full_load(self):
        self.assertIn(0.0, DEFAULT_VERIFICATION_POLICY["required_fractions"])
        self.assertIn(1.00, DEFAULT_VERIFICATION_POLICY["required_fractions"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_policy("default")

    def test_empty_required_fractions_rejected(self):
        broken = copy.deepcopy(DEFAULT_VERIFICATION_POLICY)
        broken["required_fractions"] = ()
        with self.assertRaises(ValueError):
            validate_verification_policy(broken)

    def test_fraction_above_full_scale_rejected(self):
        broken = copy.deepcopy(DEFAULT_VERIFICATION_POLICY)
        broken["required_fractions"] = (0.0, 1.4)
        with self.assertRaises(ValueError):
            validate_verification_policy(broken)

    def test_whole_range_tolerance_rejected(self):
        broken = copy.deepcopy(DEFAULT_VERIFICATION_POLICY)
        broken["match_tolerance_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_verification_policy(broken)

    def test_non_integer_minimum_rejected(self):
        broken = copy.deepcopy(DEFAULT_VERIFICATION_POLICY)
        broken["min_distinct_points"] = 4.5
        with self.assertRaises(ValueError):
            validate_verification_policy(broken)

    def test_non_boolean_no_load_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_VERIFICATION_POLICY)
        broken["require_no_load_point"] = "yes"
        with self.assertRaises(ValueError):
            validate_verification_policy(broken)


class RequiredPointsTests(unittest.TestCase):
    def test_range_fractions_scale_with_full_scale(self):
        points = [entry["current_a"] for entry in required_points_a(10.0)]
        self.assertAlmostEqual(points[0], 0.0, places=12)
        self.assertAlmostEqual(points[-1], 10.0, places=12)
        self.assertEqual(len(points), 6)

    def test_points_come_back_in_ascending_order(self):
        points = [entry["current_a"] for entry in required_points_a(10.0, [3.2, 8.4])]
        self.assertEqual(points, sorted(points))

    def test_a_mission_point_becomes_a_required_point(self):
        entries = required_points_a(10.0, [3.2])
        origins = {entry["current_a"]: entry["origin"] for entry in entries}
        self.assertAlmostEqual(min(abs(c - 3.2) for c in origins), 0.0, places=12)
        self.assertEqual(origins[3.2], "mission-load-point")

    def test_a_mission_point_on_a_range_fraction_is_not_duplicated(self):
        self.assertEqual(len(required_points_a(10.0, [5.0])), 6)

    def test_mission_point_outside_the_range_rejected(self):
        with self.assertRaises(ValueError):
            required_points_a(10.0, [12.0])

    def test_zero_full_scale_rejected(self):
        with self.assertRaises(ValueError):
            required_points_a(0.0)


class NearestAndDuplicateTests(unittest.TestCase):
    def test_nearest_point_finds_the_closest_proposal(self):
        nearest = nearest_point_a(2.4, [0.0, 1.0, 2.5, 5.0])
        self.assertAlmostEqual(nearest["current_a"], 2.5, places=12)
        self.assertAlmostEqual(nearest["distance_a"], 0.1, places=12)

    def test_nearest_point_on_an_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            nearest_point_a(2.4, [])

    def test_points_inside_the_tolerance_of_each_other_are_grouped(self):
        grouped = duplicate_points_a([0.0, 5.0, 5.1, 10.0], 10.0)
        self.assertAlmostEqual(grouped["duplicate_points_a"][0], 5.1, places=12)
        self.assertEqual(len(grouped["distinct_points_a"]), 3)

    def test_well_separated_points_are_all_distinct(self):
        grouped = duplicate_points_a([0.0, 2.5, 5.0, 7.5, 10.0], 10.0)
        self.assertEqual(grouped["duplicate_points_a"], [])

    def test_a_negative_proposed_point_rejected(self):
        with self.assertRaises(ValueError):
            duplicate_points_a([-1.0, 5.0], 10.0)

    def test_a_proposed_point_above_the_range_rejected(self):
        with self.assertRaises(ValueError):
            duplicate_points_a([0.0, 11.0], 10.0)

    def test_an_empty_proposed_matrix_rejected(self):
        with self.assertRaises(ValueError):
            duplicate_points_a([], 10.0)


class CoverageTests(unittest.TestCase):
    def test_a_full_matrix_covers_every_required_point(self):
        coverage = coverage_report(GOOD_PLAN)
        self.assertEqual(coverage["missing"], [])
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0, places=12)

    def test_a_sparse_matrix_leaves_required_points_uncovered(self):
        coverage = coverage_report(SPARSE_PLAN)
        self.assertEqual(len(coverage["missing"]), 4)
        self.assertAlmostEqual(coverage["coverage_fraction"], 2.0 / 6.0, places=12)

    def test_a_point_exactly_on_the_tolerance_edge_still_covers(self):
        # 2.5 A + 2% of 10 A lands a couple of units in the last place beyond
        # the tolerance once the fraction has been multiplied out.
        plan = _plan(
            GOOD_PLAN,
            proposed_points_a=[0.0, 1.0, 2.7, 3.2, 5.0, 7.5, 8.4, 10.0],
        )
        coverage = coverage_report(plan)
        self.assertEqual(coverage["missing"], [])
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0, places=9)

    def test_coverage_records_the_origin_of_a_missing_point(self):
        plan = _plan(SPARSE_PLAN, operating_points_a=[3.2])
        origins = {record["origin"] for record in coverage_report(plan)["missing"]}
        self.assertIn("mission-load-point", origins)

    def test_coverage_rejects_a_non_mapping_plan(self):
        with self.assertRaises(ValueError):
            coverage_report([0.0, 5.0, 10.0])

    def test_coverage_rejects_a_plan_without_a_full_scale(self):
        plan = _plan(GOOD_PLAN)
        del plan["full_scale_a"]
        with self.assertRaises(ValueError):
            coverage_report(plan)


class LowEndTests(unittest.TestCase):
    def test_a_loaded_low_point_is_reported(self):
        self.assertEqual(low_end_points_a(GOOD_PLAN), [1.0])

    def test_the_no_load_point_is_not_a_low_end_point(self):
        self.assertNotIn(0.0, low_end_points_a(GOOD_PLAN))

    def test_a_top_heavy_matrix_has_no_low_end_point(self):
        self.assertEqual(low_end_points_a(TOP_HEAVY_PLAN), [])


class AssessmentTests(unittest.TestCase):
    def test_a_full_matrix_is_complete(self):
        result = assess_verification_points(GOOD_PLAN)
        self.assertEqual(result["verdict"], POINTS_COMPLETE)
        self.assertEqual(result["missing_points_a"], [])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["duties"], [])

    def test_a_sparse_matrix_is_incomplete_and_names_the_gaps(self):
        result = assess_verification_points(SPARSE_PLAN)
        self.assertEqual(result["verdict"], POINTS_INCOMPLETE)
        self.assertEqual(len(result["missing_points_a"]), 4)
        self.assertTrue(any("no no-load point" in f for f in result["findings"]))
        self.assertTrue(any("add a verification point" in d for d in result["duties"]))

    def test_a_top_heavy_matrix_fails_on_the_low_end_alone(self):
        result = assess_verification_points(TOP_HEAVY_PLAN)
        self.assertEqual(result["verdict"], POINTS_INCOMPLETE)
        self.assertEqual(result["missing_points_a"], [10.0 * 0.10])
        self.assertTrue(any("fixed error dominates" in f for f in result["findings"]))

    def test_duplicates_are_reported_and_do_not_raise_the_distinct_count(self):
        plan = _plan(
            GOOD_PLAN,
            proposed_points_a=[0.0, 1.0, 2.5, 2.6, 3.2, 5.0, 7.5, 8.4, 10.0],
        )
        result = assess_verification_points(plan)
        self.assertEqual(len(result["duplicate_points_a"]), 1)
        self.assertEqual(len(result["distinct_points_a"]), 8)
        self.assertEqual(result["verdict"], POINTS_INCOMPLETE)

    def test_too_few_distinct_points_is_a_finding_of_its_own(self):
        policy = copy.deepcopy(DEFAULT_VERIFICATION_POLICY)
        policy["required_fractions"] = (0.0, 0.10)
        result = assess_verification_points(
            _plan(GOOD_PLAN, proposed_points_a=[0.0, 1.0], operating_points_a=[]),
            policy,
        )
        self.assertTrue(any("distinct points" in f for f in result["findings"]))

    def test_a_mission_point_can_be_the_only_gap(self):
        plan = _plan(
            GOOD_PLAN,
            proposed_points_a=[0.0, 1.0, 2.5, 3.2, 5.0, 7.5, 10.0],
        )
        result = assess_verification_points(plan)
        self.assertEqual(result["verdict"], POINTS_INCOMPLETE)
        self.assertEqual(len(result["missing_points_a"]), 1)
        self.assertAlmostEqual(result["missing_points_a"][0], 8.4, places=12)

    def test_the_match_tolerance_scales_with_full_scale(self):
        result = assess_verification_points(
            _plan(
                GOOD_PLAN,
                full_scale_a=20.0,
                proposed_points_a=[0.0, 2.0, 5.0, 10.0, 15.0, 20.0],
                operating_points_a=[],
            )
        )
        self.assertAlmostEqual(result["match_tolerance_a"], 0.4, places=12)
        self.assertEqual(result["verdict"], POINTS_COMPLETE)

    def test_assessment_rejects_a_broken_policy(self):
        broken = copy.deepcopy(DEFAULT_VERIFICATION_POLICY)
        broken["low_end_fraction"] = 0.0
        with self.assertRaises(ValueError):
            assess_verification_points(GOOD_PLAN, broken)


if __name__ == "__main__":
    unittest.main()
