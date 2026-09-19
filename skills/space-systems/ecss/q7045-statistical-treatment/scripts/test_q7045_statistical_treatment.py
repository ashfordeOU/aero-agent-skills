"""Contract tests for the statistical treatment of mechanical test results.

The cases walk a sample into an allowable: the sample statistics, the maximum
normed residual an extreme result is screened with, the tolerance factor the
coverage and confidence of a basis demand, the basis value that factor
produces, the scatter the sample carries, and the comparison against a design
allowable already in use.
"""

import unittest

from q7045_statistical_treatment_logic import (
    BASIS_DEFINITIONS,
    DEFAULT_MAX_CV_PCT,
    DEFAULT_MIN_SAMPLES,
    assess_statistical_treatment,
    basis_value,
    mnr_critical_value,
    normal_tolerance_factor,
    outlier_screen,
    sample_statistics,
    scatter_finding,
)

# Sixteen proof-strength results in MPa, tight enough to pass the scatter
# limit and large enough to carry an A-basis value.
SAMPLE = [
    302.0, 298.0, 305.0, 297.0, 301.0, 299.0, 303.0, 300.0,
    296.0, 304.0, 300.5, 299.5, 302.5, 298.5, 301.5, 300.0,
]


def _spec(**overrides):
    spec = {"values": list(SAMPLE), "basis": "B"}
    spec.update(overrides)
    return spec


class SampleStatisticsTests(unittest.TestCase):
    def test_mean_and_size_are_reported(self):
        stats = sample_statistics([10.0, 12.0, 14.0])
        self.assertEqual(stats["n"], 3)
        self.assertAlmostEqual(stats["mean"], 12.0, places=12)

    def test_standard_deviation_uses_the_sample_divisor(self):
        stats = sample_statistics([10.0, 12.0, 14.0])
        self.assertAlmostEqual(stats["standard_deviation"], 2.0, places=12)

    def test_coefficient_of_variation_is_a_percentage_of_the_mean(self):
        stats = sample_statistics([10.0, 12.0, 14.0])
        self.assertAlmostEqual(stats["cv_pct"], 100.0 * 2.0 / 12.0, places=12)

    def test_extremes_are_reported(self):
        stats = sample_statistics(SAMPLE)
        self.assertAlmostEqual(stats["minimum"], 296.0, places=12)
        self.assertAlmostEqual(stats["maximum"], 305.0, places=12)

    def test_a_single_result_is_refused(self):
        with self.assertRaises(ValueError):
            sample_statistics([300.0])

    def test_a_text_result_is_refused(self):
        with self.assertRaises(ValueError):
            sample_statistics([300.0, "301"])

    def test_a_zero_mean_has_no_scatter(self):
        with self.assertRaises(ValueError):
            sample_statistics([-5.0, 5.0])


class CriticalValueTests(unittest.TestCase):
    def test_a_tabulated_size_returns_its_own_value(self):
        self.assertAlmostEqual(mnr_critical_value(10), 2.290, places=12)

    def test_an_untabulated_size_is_interpolated(self):
        value = mnr_critical_value(22)
        self.assertGreater(value, mnr_critical_value(20))
        self.assertLess(value, mnr_critical_value(25))

    def test_a_sample_below_the_table_is_refused(self):
        with self.assertRaises(ValueError):
            mnr_critical_value(2)

    def test_a_sample_above_the_table_is_refused(self):
        with self.assertRaises(ValueError):
            mnr_critical_value(250)

    def test_a_non_integer_size_is_refused(self):
        with self.assertRaises(ValueError):
            mnr_critical_value(10.5)


class OutlierScreenTests(unittest.TestCase):
    def test_a_tight_sample_flags_nothing(self):
        screen = outlier_screen(SAMPLE)
        self.assertFalse(screen["flagged"])
        self.assertEqual(len(screen["retained"]), len(SAMPLE))

    def test_one_extreme_result_is_flagged_and_located(self):
        values = list(SAMPLE)
        values[3] = 240.0
        screen = outlier_screen(values)
        self.assertTrue(screen["flagged"])
        self.assertEqual(screen["index"], 3)
        self.assertAlmostEqual(screen["value"], 240.0, places=12)

    def test_the_flagged_result_is_the_one_left_out_of_the_retained_set(self):
        values = list(SAMPLE)
        values[3] = 240.0
        screen = outlier_screen(values)
        self.assertEqual(len(screen["retained"]), len(values) - 1)
        self.assertNotIn(240.0, screen["retained"])

    def test_an_identical_sample_has_no_normed_residual(self):
        screen = outlier_screen([300.0] * 10)
        self.assertFalse(screen["flagged"])
        self.assertAlmostEqual(screen["mnr"], 0.0, places=12)

    def test_the_normed_residual_is_below_the_critical_value_on_a_clean_sample(self):
        screen = outlier_screen(SAMPLE)
        self.assertLess(screen["mnr"], screen["critical"])


class ToleranceFactorTests(unittest.TestCase):
    def test_the_b_basis_factor_matches_the_published_value(self):
        self.assertAlmostEqual(normal_tolerance_factor(10, 0.90, 0.95), 2.355, places=3)

    def test_the_a_basis_factor_matches_the_published_value(self):
        self.assertAlmostEqual(normal_tolerance_factor(10, 0.99, 0.95), 3.981, places=3)

    def test_a_larger_sample_gives_a_smaller_factor(self):
        self.assertLess(
            normal_tolerance_factor(30, 0.90, 0.95), normal_tolerance_factor(15, 0.90, 0.95)
        )

    def test_the_a_basis_factor_always_exceeds_the_b_basis_factor(self):
        self.assertGreater(
            normal_tolerance_factor(20, 0.99, 0.95), normal_tolerance_factor(20, 0.90, 0.95)
        )

    def test_a_sample_below_three_has_no_factor(self):
        with self.assertRaises(ValueError):
            normal_tolerance_factor(2, 0.90, 0.95)

    def test_a_coverage_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            normal_tolerance_factor(10, 1.0, 0.95)

    def test_a_repeated_call_returns_the_same_factor(self):
        first = normal_tolerance_factor(12, 0.90, 0.95)
        second = normal_tolerance_factor(12, 0.90, 0.95)
        self.assertAlmostEqual(first, second, places=12)


class BasisValueTests(unittest.TestCase):
    def test_a_basis_value_sits_below_the_mean(self):
        result = basis_value(SAMPLE, "B")
        self.assertLess(result["value"], result["mean"])

    def test_the_a_basis_value_sits_below_the_b_basis_value(self):
        self.assertLess(basis_value(SAMPLE, "A")["value"], basis_value(SAMPLE, "B")["value"])

    def test_the_value_is_the_mean_less_the_factor_times_the_deviation(self):
        result = basis_value(SAMPLE, "B")
        expected = result["mean"] - result["tolerance_factor"] * result["standard_deviation"]
        self.assertAlmostEqual(result["value"], expected, places=12)

    def test_the_sample_floor_is_reported_against_the_basis(self):
        result = basis_value(SAMPLE, "A")
        self.assertEqual(result["min_samples"], DEFAULT_MIN_SAMPLES["A"])
        self.assertTrue(result["sample_sufficient"])

    def test_a_short_sample_is_reported_insufficient_not_silently_accepted(self):
        result = basis_value(SAMPLE[:8], "B")
        self.assertFalse(result["sample_sufficient"])

    def test_an_unknown_basis_is_refused(self):
        with self.assertRaises(ValueError):
            basis_value(SAMPLE, "C")

    def test_a_basis_carries_its_coverage_and_confidence(self):
        self.assertAlmostEqual(BASIS_DEFINITIONS["A"]["proportion"], 0.99, places=12)
        self.assertAlmostEqual(BASIS_DEFINITIONS["B"]["proportion"], 0.90, places=12)


class ScatterTests(unittest.TestCase):
    def test_tight_scatter_raises_nothing(self):
        result = scatter_finding(3.0)
        self.assertTrue(result["within"])
        self.assertIsNone(result["finding"])

    def test_scatter_above_the_limit_raises_a_finding(self):
        result = scatter_finding(14.0)
        self.assertFalse(result["within"])
        self.assertIsNotNone(result["finding"])

    def test_scatter_exactly_on_the_limit_is_accepted(self):
        result = scatter_finding(DEFAULT_MAX_CV_PCT)
        self.assertTrue(result["within"])

    def test_negative_scatter_is_refused(self):
        with self.assertRaises(ValueError):
            scatter_finding(-1.0)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_sample_yields_a_usable_b_basis_value(self):
        result = assess_statistical_treatment(_spec())
        self.assertTrue(result["usable"])
        self.assertLess(result["basis"]["value"], result["statistics"]["mean"])

    def test_an_extreme_result_is_raised_as_a_finding(self):
        values = list(SAMPLE)
        values[3] = 240.0
        result = assess_statistical_treatment(_spec(values=values))
        self.assertFalse(result["usable"])
        self.assertTrue(result["screen"]["flagged"])

    def test_dropping_the_flagged_result_shrinks_the_sample(self):
        values = list(SAMPLE)
        values[3] = 240.0
        kept = assess_statistical_treatment(_spec(values=values))
        dropped = assess_statistical_treatment(_spec(values=values, drop_outlier=True))
        self.assertEqual(dropped["statistics"]["n"], kept["statistics"]["n"] - 1)
        self.assertGreater(dropped["basis"]["value"], kept["basis"]["value"])

    def test_a_short_sample_blocks_an_a_basis_value(self):
        result = assess_statistical_treatment(_spec(values=SAMPLE[:10], basis="A"))
        self.assertFalse(result["usable"])

    def test_a_design_allowable_below_the_basis_value_is_supported(self):
        result = assess_statistical_treatment(_spec(design_allowable=280.0))
        self.assertTrue(result["usable"])
        self.assertGreater(result["margin"], 0.0)

    def test_a_design_allowable_above_the_basis_value_is_a_finding(self):
        result = assess_statistical_treatment(_spec(design_allowable=299.0))
        self.assertFalse(result["usable"])
        self.assertLess(result["margin"], 0.0)

    def test_no_margin_is_reported_when_no_allowable_is_given(self):
        result = assess_statistical_treatment(_spec())
        self.assertIsNone(result["margin"])

    def test_a_scattered_sample_is_reported(self):
        values = [300.0, 360.0, 240.0, 330.0, 270.0, 315.0, 285.0, 345.0, 255.0, 300.0,
                  310.0, 290.0, 320.0, 280.0, 305.0, 295.0]
        result = assess_statistical_treatment(_spec(values=values, max_cv_pct=5.0))
        self.assertFalse(result["scatter"]["within"])

    def test_a_missing_key_is_refused(self):
        spec = _spec()
        del spec["basis"]
        with self.assertRaises(ValueError):
            assess_statistical_treatment(spec)

    def test_a_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_statistical_treatment(SAMPLE)


if __name__ == "__main__":
    unittest.main()
