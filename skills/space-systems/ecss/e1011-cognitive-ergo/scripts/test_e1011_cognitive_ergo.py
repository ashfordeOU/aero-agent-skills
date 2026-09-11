#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.6.6 cognitive ergonomics for
human-operated space system interfaces.

Exercises scripts/e1011_cognitive_ergo_logic.py (stdlib unittest, offline).
Contract: categorize_workload maps a 0-10 composite workload index to exactly
one of "under_loaded", "optimal", or "over_loaded" and raises for out-of-range
input; check_simultaneous_tasks returns within_limit True when task_count is at
or below the threshold and False above it, and raises for invalid inputs;
check_coding_dimensions returns within_limit True when the count of distinct
coding dimensions is at or below max_dims, raises for unrecognized dimension
names, deduplicates repeated names, and lists excess dimensions when the limit
is exceeded; check_information_density returns in_bounds True when element_count
is at or below max_elements, and raises for negative inputs;
assess_sa_coverage returns a sorted list of SA level names not covered and
returns empty when all three SA levels are present;
cognitive_ergo_review aggregates workload, task, coding, density, and SA
findings and sets compliant True only when all checks pass;
is_cognitively_ergonomic mirrors the compliant flag.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_cognitive_ergo_logic as ce  # noqa: E402

_ALL_SA_LEVELS = list(ce.SA_LEVELS)

_GOOD_REVIEW_KWARGS = dict(
    workload_index=5.0,
    task_count=3,
    coding_sets=[["color", "shape"], ["text_label"]],
    element_counts=[5, 7],
    sa_levels=_ALL_SA_LEVELS,
)


class CategorizeWorkloadTest(unittest.TestCase):
    def test_low_index_is_under_loaded(self):
        self.assertEqual(ce.categorize_workload(1.0), "under_loaded")

    def test_zero_is_under_loaded(self):
        self.assertEqual(ce.categorize_workload(0.0), "under_loaded")

    def test_boundary_at_lower_optimal_is_optimal(self):
        self.assertEqual(ce.categorize_workload(3.0), "optimal")

    def test_mid_range_is_optimal(self):
        self.assertEqual(ce.categorize_workload(5.0), "optimal")

    def test_boundary_at_upper_optimal_is_optimal(self):
        self.assertEqual(ce.categorize_workload(7.0), "optimal")

    def test_above_upper_bound_is_over_loaded(self):
        self.assertEqual(ce.categorize_workload(8.5), "over_loaded")

    def test_max_value_is_over_loaded(self):
        self.assertEqual(ce.categorize_workload(10.0), "over_loaded")

    def test_negative_index_raises(self):
        with self.assertRaises(ValueError):
            ce.categorize_workload(-0.1)

    def test_above_max_raises(self):
        with self.assertRaises(ValueError):
            ce.categorize_workload(10.1)


class CheckSimultaneousTasksTest(unittest.TestCase):
    def test_at_threshold_within_limit(self):
        result = ce.check_simultaneous_tasks(4)
        self.assertTrue(result["within_limit"])

    def test_below_threshold_within_limit(self):
        result = ce.check_simultaneous_tasks(2)
        self.assertTrue(result["within_limit"])

    def test_above_threshold_not_within_limit(self):
        result = ce.check_simultaneous_tasks(5)
        self.assertFalse(result["within_limit"])

    def test_result_dict_has_expected_keys(self):
        result = ce.check_simultaneous_tasks(3)
        for key in ("task_count", "threshold", "within_limit"):
            self.assertIn(key, result)

    def test_custom_threshold_respected(self):
        result = ce.check_simultaneous_tasks(6, threshold=7)
        self.assertTrue(result["within_limit"])

    def test_negative_task_count_raises(self):
        with self.assertRaises(ValueError):
            ce.check_simultaneous_tasks(-1)

    def test_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            ce.check_simultaneous_tasks(1, threshold=0)

    def test_zero_tasks_within_limit(self):
        result = ce.check_simultaneous_tasks(0)
        self.assertTrue(result["within_limit"])


class CheckCodingDimensionsTest(unittest.TestCase):
    def test_two_dimensions_within_limit(self):
        result = ce.check_coding_dimensions(["color", "shape"])
        self.assertTrue(result["within_limit"])

    def test_three_dimensions_at_limit(self):
        result = ce.check_coding_dimensions(["color", "shape", "size"])
        self.assertTrue(result["within_limit"])

    def test_four_dimensions_exceeds_limit(self):
        result = ce.check_coding_dimensions(["color", "shape", "size", "position"])
        self.assertFalse(result["within_limit"])

    def test_excess_listed_when_over_limit(self):
        result = ce.check_coding_dimensions(["color", "shape", "size", "position"])
        self.assertGreater(len(result["excess"]), 0)

    def test_empty_coding_set_within_limit(self):
        result = ce.check_coding_dimensions([])
        self.assertTrue(result["within_limit"])

    def test_unrecognized_dimension_raises(self):
        with self.assertRaises(ValueError):
            ce.check_coding_dimensions(["color", "haptical_vibration"])

    def test_result_dict_has_expected_keys(self):
        result = ce.check_coding_dimensions(["color"])
        for key in ("dimensions", "count", "max_dims", "within_limit", "excess"):
            self.assertIn(key, result)

    def test_duplicate_dimensions_deduplicated(self):
        result = ce.check_coding_dimensions(["color", "color", "shape"])
        self.assertEqual(result["count"], 2)

    def test_excess_is_empty_when_within_limit(self):
        result = ce.check_coding_dimensions(["color", "shape"])
        self.assertEqual(result["excess"], [])

    def test_custom_max_dims_respected(self):
        result = ce.check_coding_dimensions(
            ["color", "shape", "size", "position"], max_dims=4
        )
        self.assertTrue(result["within_limit"])


class CheckInformationDensityTest(unittest.TestCase):
    def test_count_within_limit_is_in_bounds(self):
        result = ce.check_information_density(5)
        self.assertTrue(result["in_bounds"])

    def test_count_at_limit_is_in_bounds(self):
        result = ce.check_information_density(9)
        self.assertTrue(result["in_bounds"])

    def test_count_above_limit_not_in_bounds(self):
        result = ce.check_information_density(10)
        self.assertFalse(result["in_bounds"])

    def test_zero_elements_in_bounds(self):
        result = ce.check_information_density(0)
        self.assertTrue(result["in_bounds"])

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            ce.check_information_density(-1)

    def test_custom_max_elements_respected(self):
        result = ce.check_information_density(12, max_elements=15)
        self.assertTrue(result["in_bounds"])

    def test_result_dict_has_expected_keys(self):
        result = ce.check_information_density(5)
        for key in ("element_count", "max_elements", "in_bounds"):
            self.assertIn(key, result)

    def test_zero_max_elements_raises(self):
        with self.assertRaises(ValueError):
            ce.check_information_density(0, max_elements=0)


class AssessSaCoverageTest(unittest.TestCase):
    def test_all_sa_levels_present_returns_empty(self):
        self.assertEqual(ce.assess_sa_coverage(ce.SA_LEVELS), [])

    def test_missing_projection_level_returned(self):
        missing = ce.assess_sa_coverage(
            ["level_1_perception", "level_2_comprehension"]
        )
        self.assertIn("level_3_projection", missing)
        self.assertNotIn("level_1_perception", missing)

    def test_empty_provided_returns_all_three_levels(self):
        missing = ce.assess_sa_coverage([])
        self.assertEqual(len(missing), 3)

    def test_result_is_sorted(self):
        missing = ce.assess_sa_coverage([])
        self.assertEqual(missing, sorted(missing))

    def test_single_level_supplied_two_missing(self):
        missing = ce.assess_sa_coverage(["level_2_comprehension"])
        self.assertEqual(len(missing), 2)
        self.assertNotIn("level_2_comprehension", missing)


class CognitiveErgoReviewTest(unittest.TestCase):
    def test_fully_compliant_review(self):
        review = ce.cognitive_ergo_review(**_GOOD_REVIEW_KWARGS)
        self.assertTrue(review["compliant"])
        self.assertTrue(ce.is_cognitively_ergonomic(review))

    def test_over_loaded_workload_makes_non_compliant(self):
        review = ce.cognitive_ergo_review(
            workload_index=9.0,
            task_count=3,
            sa_levels=_ALL_SA_LEVELS,
        )
        self.assertFalse(review["compliant"])
        self.assertEqual(review["workload_band"], "over_loaded")
        self.assertFalse(review["workload_ok"])

    def test_under_loaded_workload_makes_non_compliant(self):
        review = ce.cognitive_ergo_review(
            workload_index=1.0,
            task_count=3,
            sa_levels=_ALL_SA_LEVELS,
        )
        self.assertFalse(review["compliant"])
        self.assertEqual(review["workload_band"], "under_loaded")

    def test_task_overload_makes_non_compliant(self):
        review = ce.cognitive_ergo_review(
            workload_index=5.0,
            task_count=7,
            sa_levels=_ALL_SA_LEVELS,
        )
        self.assertFalse(review["compliant"])
        self.assertFalse(review["simultaneous_tasks_ok"])

    def test_coding_violation_makes_non_compliant(self):
        review = ce.cognitive_ergo_review(
            workload_index=5.0,
            task_count=3,
            coding_sets=[["color", "shape", "size", "position"]],
            sa_levels=_ALL_SA_LEVELS,
        )
        self.assertFalse(review["compliant"])
        self.assertEqual(len(review["coding_violations"]), 1)

    def test_density_violation_makes_non_compliant(self):
        review = ce.cognitive_ergo_review(
            workload_index=5.0,
            task_count=3,
            element_counts=[14],
            sa_levels=_ALL_SA_LEVELS,
        )
        self.assertFalse(review["compliant"])
        self.assertEqual(len(review["density_violations"]), 1)

    def test_missing_sa_level_makes_non_compliant(self):
        review = ce.cognitive_ergo_review(
            workload_index=5.0,
            task_count=3,
            sa_levels=["level_1_perception"],
        )
        self.assertFalse(review["compliant"])
        self.assertIn("level_3_projection", review["sa_missing"])

    def test_no_sa_levels_supplied_defaults_to_all_missing(self):
        review = ce.cognitive_ergo_review(workload_index=5.0, task_count=3)
        self.assertEqual(len(review["sa_missing"]), 3)

    def test_review_dict_has_expected_keys(self):
        review = ce.cognitive_ergo_review(**_GOOD_REVIEW_KWARGS)
        for key in (
            "workload_band",
            "workload_ok",
            "simultaneous_tasks_ok",
            "coding_violations",
            "density_violations",
            "sa_missing",
            "compliant",
        ):
            self.assertIn(key, review)

    def test_multiple_violations_all_reported(self):
        review = ce.cognitive_ergo_review(
            workload_index=5.0,
            task_count=3,
            coding_sets=[
                ["color", "shape", "size", "position"],
                ["brightness", "motion", "text_label", "auditory_code"],
            ],
            element_counts=[12, 15],
            sa_levels=_ALL_SA_LEVELS,
        )
        self.assertEqual(len(review["coding_violations"]), 2)
        self.assertEqual(len(review["density_violations"]), 2)
        self.assertFalse(review["compliant"])

    def test_clean_coding_and_density_with_bad_workload(self):
        review = ce.cognitive_ergo_review(
            workload_index=8.0,
            task_count=2,
            coding_sets=[["color"]],
            element_counts=[4],
            sa_levels=_ALL_SA_LEVELS,
        )
        self.assertEqual(review["coding_violations"], [])
        self.assertEqual(review["density_violations"], [])
        self.assertFalse(review["compliant"])

    def test_is_cognitively_ergonomic_false_when_not_compliant(self):
        review = ce.cognitive_ergo_review(
            workload_index=9.0,
            task_count=3,
            sa_levels=_ALL_SA_LEVELS,
        )
        self.assertFalse(ce.is_cognitively_ergonomic(review))


if __name__ == "__main__":
    unittest.main()
