#!/usr/bin/env python3
"""Contract test for the output current limitation range check (offline)."""

import copy
import unittest

from e2020_output_current_limitation_range_logic import (
    ADVISORY_BAND_USE,
    DEFAULT_ASSESSMENT_POLICY,
    DEFAULT_CONTRIBUTORS,
    FINDING_ABOVE_MAX,
    FINDING_BAND_TOO_WIDE,
    FINDING_BELOW_MIN,
    FINDING_HARNESS,
    FINDING_LOAD_OVERLAP,
    VERDICT_OUTSIDE,
    VERDICT_WITHIN,
    assess_functional_separation,
    assess_limitation_range,
    contributor_amperes,
    limitation_range,
    recentred_nominal_a,
    stack_tolerances,
    validate_assessment_policy,
    validate_contributor,
    validate_contributors,
    verify_within_thresholds,
)

NOMINAL_CASE = {
    "nominal_a": 2.0,
    "contributors": DEFAULT_CONTRIBUTORS,
    "threshold_min_a": 1.70,
    "threshold_max_a": 2.40,
    "healthy_load_current_a": 1.5,
    "harness_rating_a": 3.0,
}


def _case(**overrides):
    case = dict(copy.deepcopy(NOMINAL_CASE))
    case["contributors"] = DEFAULT_CONTRIBUTORS
    case.update(overrides)
    return case


def _contrib(name="temperature-drift"):
    for row in DEFAULT_CONTRIBUTORS:
        if row["name"] == name:
            return copy.deepcopy(row)
    raise AssertionError("no such contributor: %s" % name)


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_assessment_policy(DEFAULT_ASSESSMENT_POLICY),
            DEFAULT_ASSESSMENT_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_assessment_policy(0.8)

    def test_advisory_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_assessment_policy({"band_advisory_fraction": 1.5})

    def test_zero_advisory_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_assessment_policy({"band_advisory_fraction": 0.0})


class ContributorTests(unittest.TestCase):
    def test_default_contributor_set_validates(self):
        rows = validate_contributors(DEFAULT_CONTRIBUTORS)
        self.assertEqual(len(rows), len(DEFAULT_CONTRIBUTORS))

    def test_contributor_missing_a_side_rejected(self):
        row = _contrib()
        del row["plus"]
        with self.assertRaises(ValueError):
            validate_contributor(row)

    def test_negative_tolerance_rejected(self):
        row = _contrib()
        row["minus"] = -0.01
        with self.assertRaises(ValueError):
            validate_contributor(row)

    def test_relative_tolerance_at_unity_rejected(self):
        row = _contrib()
        row["plus"] = 1.0
        with self.assertRaises(ValueError):
            validate_contributor(row)

    def test_unknown_contributor_kind_rejected(self):
        row = _contrib()
        row["kind"] = "statistical"
        with self.assertRaises(ValueError):
            validate_contributor(row)

    def test_two_sided_zero_contributor_rejected(self):
        with self.assertRaises(ValueError):
            validate_contributor(
                {"name": "spare", "kind": "absolute", "minus": 0.0, "plus": 0.0}
            )

    def test_blank_contributor_name_rejected(self):
        row = _contrib()
        row["name"] = "  "
        with self.assertRaises(ValueError):
            validate_contributor(row)

    def test_repeated_contributor_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_contributors([_contrib(), _contrib()])

    def test_empty_contributor_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_contributors([])

    def test_mapping_instead_of_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_contributors(_contrib())

    def test_relative_contributor_scales_with_the_setpoint(self):
        low, high = contributor_amperes(_contrib("temperature-drift"), 2.0)
        self.assertAlmostEqual(low, 0.06, places=12)
        self.assertAlmostEqual(high, 0.06, places=12)

    def test_absolute_contributor_ignores_the_setpoint(self):
        small = contributor_amperes(_contrib("sense-offset"), 1.0)
        large = contributor_amperes(_contrib("sense-offset"), 8.0)
        self.assertEqual(small, large)


class StackTests(unittest.TestCase):
    def test_arithmetic_stack_sums_both_sides(self):
        minus_a, plus_a = stack_tolerances(2.0, DEFAULT_CONTRIBUTORS, "arithmetic")
        self.assertAlmostEqual(minus_a, 0.18, places=12)
        self.assertAlmostEqual(plus_a, 0.20, places=12)

    def test_root_sum_square_stack_is_narrower_than_arithmetic(self):
        arith = stack_tolerances(2.0, DEFAULT_CONTRIBUTORS, "arithmetic")
        rss = stack_tolerances(2.0, DEFAULT_CONTRIBUTORS, "rss")
        self.assertLess(rss[0], arith[0])
        self.assertLess(rss[1], arith[1])

    def test_root_sum_square_of_one_contributor_equals_that_contributor(self):
        one = [_contrib("sense-offset")]
        arith = stack_tolerances(2.0, one, "arithmetic")
        rss = stack_tolerances(2.0, one, "rss")
        self.assertAlmostEqual(rss[0], arith[0], places=12)
        self.assertAlmostEqual(rss[1], arith[1], places=12)

    def test_unknown_stack_method_rejected(self):
        with self.assertRaises(ValueError):
            stack_tolerances(2.0, DEFAULT_CONTRIBUTORS, "monte-carlo")

    def test_zero_setpoint_rejected(self):
        with self.assertRaises(ValueError):
            stack_tolerances(0.0, DEFAULT_CONTRIBUTORS)


class LimitationRangeTests(unittest.TestCase):
    def test_range_brackets_the_nominal_setpoint(self):
        result = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        self.assertAlmostEqual(result["min_a"], 1.82, places=12)
        self.assertAlmostEqual(result["max_a"], 2.20, places=12)

    def test_band_width_is_the_two_sides_together(self):
        result = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        self.assertAlmostEqual(
            result["band_width_a"], result["minus_a"] + result["plus_a"], places=12
        )

    def test_range_records_the_method_it_used(self):
        self.assertEqual(
            limitation_range(2.0, DEFAULT_CONTRIBUTORS, "rss")["method"], "rss"
        )

    def test_a_downward_stack_that_consumes_the_setpoint_is_rejected(self):
        heavy = [{"name": "wild", "kind": "relative", "minus": 0.99, "plus": 0.1}] + [
            _contrib("sense-offset")
        ]
        with self.assertRaises(ValueError):
            limitation_range(0.01, heavy)


class ThresholdTests(unittest.TestCase):
    def test_nominal_range_sits_inside_the_window(self):
        result = verify_within_thresholds(
            limitation_range(2.0, DEFAULT_CONTRIBUTORS), 1.70, 2.40
        )
        self.assertTrue(result["within"])

    def test_window_usage_is_the_band_over_the_window(self):
        result = verify_within_thresholds(
            limitation_range(2.0, DEFAULT_CONTRIBUTORS), 1.70, 2.40
        )
        self.assertAlmostEqual(result["window_usage"], 0.38 / 0.70, places=9)

    def test_inverted_threshold_window_rejected(self):
        with self.assertRaises(ValueError):
            verify_within_thresholds(
                limitation_range(2.0, DEFAULT_CONTRIBUTORS), 2.40, 1.70
            )

    def test_range_missing_an_edge_rejected(self):
        broken = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        del broken["max_a"]
        with self.assertRaises(ValueError):
            verify_within_thresholds(broken, 1.70, 2.40)

    def test_lower_edge_exactly_on_the_floor_is_inside(self):
        current_range = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        result = verify_within_thresholds(current_range, current_range["min_a"], 2.40)
        self.assertAlmostEqual(result["lower_margin_a"], 0.0, places=9)
        self.assertTrue(result["above_floor"])

    def test_upper_edge_exactly_on_the_ceiling_is_inside(self):
        current_range = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        result = verify_within_thresholds(current_range, 1.70, current_range["max_a"])
        self.assertAlmostEqual(result["upper_margin_a"], 0.0, places=9)
        self.assertTrue(result["below_ceiling"])


class RecentreTests(unittest.TestCase):
    def test_recentred_setpoint_centres_the_band_in_the_window(self):
        current_range = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        self.assertAlmostEqual(
            recentred_nominal_a(current_range, 1.70, 2.40), 2.04, places=9
        )

    def test_recentred_setpoint_keeps_equal_slack_on_both_sides(self):
        current_range = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        centre = recentred_nominal_a(current_range, 1.70, 2.40)
        lower_slack = (centre - current_range["minus_a"]) - 1.70
        upper_slack = 2.40 - (centre + current_range["plus_a"])
        self.assertAlmostEqual(lower_slack, upper_slack, places=9)

    def test_a_band_wider_than_the_window_has_no_setpoint(self):
        current_range = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        self.assertIsNone(recentred_nominal_a(current_range, 1.95, 2.15))

    def test_a_band_exactly_as_wide_as_the_window_still_has_a_setpoint(self):
        current_range = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        floor = 1.80
        ceiling = floor + current_range["band_width_a"]
        centre = recentred_nominal_a(current_range, floor, ceiling)
        self.assertIsNotNone(centre)
        self.assertAlmostEqual(centre - current_range["minus_a"], floor, places=9)


class SeparationTests(unittest.TestCase):
    def test_nominal_range_clears_the_healthy_load(self):
        result = assess_functional_separation(
            limitation_range(2.0, DEFAULT_CONTRIBUTORS), 1.5, 3.0
        )
        self.assertTrue(result["clears_healthy_load"])
        self.assertAlmostEqual(result["load_headroom_a"], 0.32, places=9)

    def test_a_load_at_the_lower_edge_does_not_clear_it(self):
        current_range = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        result = assess_functional_separation(
            current_range, current_range["min_a"], 3.0
        )
        self.assertAlmostEqual(result["load_headroom_a"], 0.0, places=9)
        self.assertFalse(result["clears_healthy_load"])

    def test_upper_edge_exactly_on_the_harness_rating_still_protects(self):
        current_range = limitation_range(2.0, DEFAULT_CONTRIBUTORS)
        result = assess_functional_separation(
            current_range, 1.5, current_range["max_a"]
        )
        self.assertAlmostEqual(result["harness_headroom_a"], 0.0, places=9)
        self.assertTrue(result["protects_harness"])

    def test_zero_harness_rating_rejected(self):
        with self.assertRaises(ValueError):
            assess_functional_separation(
                limitation_range(2.0, DEFAULT_CONTRIBUTORS), 1.5, 0.0
            )


class AssessmentTests(unittest.TestCase):
    def test_nominal_case_is_compliant_and_quiet(self):
        result = assess_limitation_range(NOMINAL_CASE)
        self.assertEqual(result["verdict"], VERDICT_WITHIN)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["advisories"], [])

    def test_a_raised_floor_puts_the_lower_edge_outside(self):
        result = assess_limitation_range(_case(threshold_min_a=1.90))
        self.assertEqual(result["verdict"], VERDICT_OUTSIDE)
        self.assertTrue(any(FINDING_BELOW_MIN in f for f in result["findings"]))

    def test_a_lowered_ceiling_puts_the_upper_edge_outside(self):
        result = assess_limitation_range(_case(threshold_max_a=2.10))
        self.assertFalse(result["compliant"])
        self.assertTrue(any(FINDING_ABOVE_MAX in f for f in result["findings"]))

    def test_a_load_inside_the_range_is_a_nuisance_limitation_finding(self):
        result = assess_limitation_range(_case(healthy_load_current_a=1.90))
        self.assertTrue(any(FINDING_LOAD_OVERLAP in f for f in result["findings"]))

    def test_a_harness_below_the_upper_edge_is_a_protection_finding(self):
        result = assess_limitation_range(_case(harness_rating_a=2.0))
        self.assertTrue(any(FINDING_HARNESS in f for f in result["findings"]))

    def test_a_window_narrower_than_the_stack_names_the_stack(self):
        result = assess_limitation_range(
            _case(threshold_min_a=1.95, threshold_max_a=2.15)
        )
        self.assertIsNone(result["recentred_nominal_a"])
        self.assertTrue(any(FINDING_BAND_TOO_WIDE in f for f in result["findings"]))

    def test_a_tight_but_feasible_window_raises_an_advisory_only(self):
        result = assess_limitation_range(
            _case(threshold_min_a=1.80, threshold_max_a=2.25)
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(any(ADVISORY_BAND_USE in a for a in result["advisories"]))

    def test_root_sum_square_widens_the_margins_against_the_same_window(self):
        arith = assess_limitation_range(_case(method="arithmetic"))
        rss = assess_limitation_range(_case(method="rss"))
        self.assertGreater(
            rss["thresholds"]["lower_margin_a"],
            arith["thresholds"]["lower_margin_a"],
        )
        self.assertGreater(
            rss["thresholds"]["upper_margin_a"],
            arith["thresholds"]["upper_margin_a"],
        )

    def test_assessment_rejects_an_unknown_method(self):
        with self.assertRaises(ValueError):
            assess_limitation_range(_case(method="worst-of-three"))

    def test_assessment_rejects_a_case_missing_a_threshold(self):
        case = _case()
        del case["threshold_max_a"]
        with self.assertRaises(ValueError):
            assess_limitation_range(case)

    def test_assessment_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            assess_limitation_range("2.0 A")

    def test_assessment_reports_the_recentred_setpoint_when_it_fits(self):
        result = assess_limitation_range(NOMINAL_CASE)
        self.assertAlmostEqual(result["recentred_nominal_a"], 2.04, places=9)


if __name__ == "__main__":
    unittest.main()
