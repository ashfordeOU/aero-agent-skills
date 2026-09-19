#!/usr/bin/env python3
"""Gate 3 contract test for q2007-process-validation.

stdlib unittest, offline, deterministic. Run:
    python3 test_q2007_process_validation.py
"""

import math
import unittest

from q2007_process_validation_logic import (
    PROCESS_NOT_VALIDATED,
    PROCESS_VALIDATED,
    bias_estimate,
    capability_ratio,
    combined_standard_uncertainty,
    expanded_uncertainty,
    mean_value,
    repeatability_sd,
    reproducibility_sd,
    sample_standard_deviation,
    validate_groups,
    validate_test_process,
)

# Two operators, four runs each, same underlying value: tight, unbiased.
TIGHT_GROUPS = [
    [100.1, 99.9, 100.1, 99.9],
    [99.9, 100.1, 99.9, 100.1],
]

# Same within-group spread, group means one unit apart: reproducibility.
OFFSET_GROUPS = [
    [99.6, 99.4, 99.6, 99.4],
    [100.6, 100.4, 100.6, 100.4],
]


def good_record(**over):
    record = {
        "groups": [list(g) for g in TIGHT_GROUPS],
        "reference_value": 100.0,
        "tolerance": 4.0,
        "bias_allowance": 0.2,
    }
    record.update(over)
    return record


class TestGroupValidation(unittest.TestCase):
    def test_good_groups_normalize(self):
        groups = validate_groups(TIGHT_GROUPS)
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(groups[0]), 4)

    def test_a_single_group_cannot_resolve_reproducibility(self):
        with self.assertRaises(ValueError):
            validate_groups([TIGHT_GROUPS[0]])

    def test_a_group_with_one_run_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_groups([TIGHT_GROUPS[0], [100.0]])

    def test_too_few_total_runs_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_groups([[100.0, 100.1], [99.9, 100.0]])

    def test_a_non_numeric_result_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_groups([[100.0, "100.1", 100.0, 100.0], TIGHT_GROUPS[1]])

    def test_an_infinite_result_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_groups([[100.0, math.inf, 100.0, 100.0], TIGHT_GROUPS[1]])


class TestGroupStatistics(unittest.TestCase):
    def test_mean_of_a_group(self):
        self.assertAlmostEqual(mean_value([1.0, 2.0, 3.0, 4.0]), 2.5, places=9)

    def test_empty_sequence_has_no_mean(self):
        with self.assertRaises(ValueError):
            mean_value([])

    def test_sample_spread_uses_n_minus_one(self):
        # mean 5, deviations -4/0/+4, sum of squares 32 over 2 degrees of
        # freedom = 16, so the n-1 spread is exactly 4 while the n spread
        # would be sqrt(32/3).
        self.assertAlmostEqual(
            sample_standard_deviation([1.0, 5.0, 9.0]), 4.0, places=9
        )

    def test_a_single_result_has_no_spread(self):
        with self.assertRaises(ValueError):
            sample_standard_deviation([100.0])

    def test_identical_results_have_zero_spread(self):
        self.assertAlmostEqual(
            sample_standard_deviation([7.0, 7.0, 7.0]), 0.0, places=9
        )


class TestRepeatability(unittest.TestCase):
    def test_pooled_spread_of_equal_groups_is_that_spread(self):
        spread = sample_standard_deviation(TIGHT_GROUPS[0])
        self.assertAlmostEqual(repeatability_sd(TIGHT_GROUPS), spread, places=9)

    def test_pooling_weights_the_larger_group(self):
        groups = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0], [0.0, 2.0]]
        pooled = repeatability_sd(groups)
        self.assertAlmostEqual(pooled, math.sqrt(2.0 / 6.0), places=9)

    def test_pooled_spread_is_not_the_average_of_group_spreads(self):
        groups = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0], [0.0, 2.0]]
        average = (
            sample_standard_deviation(groups[0]) + sample_standard_deviation(groups[1])
        ) / 2.0
        self.assertAlmostEqual(average, math.sqrt(2.0) / 2.0, places=9)
        self.assertAlmostEqual(repeatability_sd(groups), math.sqrt(1.0 / 3.0), places=9)


class TestReproducibility(unittest.TestCase):
    def test_offset_group_means_produce_a_reproducibility_term(self):
        value = reproducibility_sd(OFFSET_GROUPS)
        self.assertAlmostEqual(value, math.sqrt(0.5 - (0.04 / 3.0) / 4.0), places=9)

    def test_coincident_group_means_resolve_no_reproducibility(self):
        self.assertAlmostEqual(reproducibility_sd(TIGHT_GROUPS), 0.0, places=9)

    def test_reproducibility_is_floored_at_zero(self):
        groups = [[100.0, 90.0, 110.0, 100.0], [100.0, 90.0, 110.0, 100.0]]
        self.assertAlmostEqual(reproducibility_sd(groups), 0.0, places=9)


class TestBias(unittest.TestCase):
    def test_unbiased_runs_report_zero_bias(self):
        self.assertAlmostEqual(bias_estimate(TIGHT_GROUPS, 100.0), 0.0, places=9)

    def test_a_high_reading_process_reports_positive_bias(self):
        self.assertAlmostEqual(bias_estimate(OFFSET_GROUPS, 99.5), 0.5, places=9)

    def test_a_non_numeric_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            bias_estimate(TIGHT_GROUPS, "one hundred")


class TestUncertainty(unittest.TestCase):
    def test_components_combine_in_quadrature(self):
        self.assertAlmostEqual(
            combined_standard_uncertainty(3.0, 4.0, 0.0), 5.0, places=9
        )

    def test_bias_enters_the_combination(self):
        self.assertAlmostEqual(
            combined_standard_uncertainty(0.0, 0.0, -2.0), 2.0, places=9
        )

    def test_a_negative_spread_is_rejected(self):
        with self.assertRaises(ValueError):
            combined_standard_uncertainty(-1.0, 0.0, 0.0)

    def test_expansion_scales_by_the_coverage_factor(self):
        self.assertAlmostEqual(expanded_uncertainty(0.5, 2.0), 1.0, places=9)

    def test_a_coverage_factor_under_one_is_rejected(self):
        with self.assertRaises(ValueError):
            expanded_uncertainty(0.5, 0.5)

    def test_capability_ratio_is_tolerance_over_expanded_uncertainty(self):
        self.assertAlmostEqual(capability_ratio(4.0, 1.0), 4.0, places=9)

    def test_zero_expanded_uncertainty_has_no_ratio(self):
        with self.assertRaises(ValueError):
            capability_ratio(4.0, 0.0)


class TestFullValidation(unittest.TestCase):
    def test_a_tight_unbiased_process_is_validated(self):
        report = validate_test_process(good_record())
        self.assertEqual(report["verdict"], PROCESS_VALIDATED)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["total_runs"], 8)

    def test_an_unresolved_reproducibility_term_is_a_limitation(self):
        report = validate_test_process(good_record())
        self.assertAlmostEqual(report["reproducibility_sd"], 0.0, places=9)
        self.assertEqual(len(report["limitations"]), 1)

    def test_operator_offset_shows_up_as_reproducibility(self):
        report = validate_test_process(
            good_record(groups=[list(g) for g in OFFSET_GROUPS])
        )
        self.assertAlmostEqual(
            report["reproducibility_sd"], math.sqrt(0.5 - (0.04 / 3.0) / 4.0), places=9
        )
        self.assertEqual(report["limitations"], [])

    def test_a_bias_over_the_allowance_is_a_finding(self):
        report = validate_test_process(good_record(reference_value=99.0))
        self.assertEqual(report["verdict"], PROCESS_NOT_VALIDATED)
        self.assertAlmostEqual(report["bias"], 1.0, places=9)

    def test_a_bias_exactly_on_the_allowance_is_not_a_finding(self):
        report = validate_test_process(
            good_record(reference_value=99.8, bias_allowance=0.2)
        )
        self.assertAlmostEqual(abs(report["bias"]), 0.2, places=9)
        self.assertEqual(
            [f for f in report["findings"] if f.startswith("bias")], []
        )

    def test_a_tolerance_too_narrow_for_the_process_is_a_finding(self):
        report = validate_test_process(good_record(tolerance=0.1))
        self.assertEqual(report["verdict"], PROCESS_NOT_VALIDATED)
        self.assertEqual(len(report["findings"]), 1)

    def test_a_negative_bias_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_process(good_record(bias_allowance=-0.1))

    def test_a_zero_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_process(good_record(tolerance=0.0))

    def test_validation_propagates_a_group_error(self):
        with self.assertRaises(ValueError):
            validate_test_process(good_record(groups=[TIGHT_GROUPS[0]]))


if __name__ == "__main__":
    unittest.main()
