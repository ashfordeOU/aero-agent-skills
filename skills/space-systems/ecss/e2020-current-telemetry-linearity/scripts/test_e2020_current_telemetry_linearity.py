"""Contract tests for the clause 5.2.8.4.1 current-telemetry linearity logic."""

import unittest

from e2020_current_telemetry_linearity_logic import (
    ACCURACY_TOLERANCE,
    MIN_DISTINCT_POINTS,
    assess_linearity,
    class_referenced_errors,
    compare_reference_bases,
    fit_linear,
    max_non_linearity,
    non_linearity_ratios,
    range_coverage,
    reversal_indices,
    signed_errors,
    validate_samples,
    worst_class_referenced_error,
)

# A 1 A class device whose telemetry is read over a 0 A to 2 A range.
CLASS_A = 1.0
RANGE_A = (0.0, 2.0)

IDEAL = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (1.5, 1.5), (2.0, 2.0)]
# One per cent gain error on top of a five milliamp zero offset.
SLOPED = [(0.0, 0.005), (0.5, 0.51), (1.0, 1.015), (1.5, 1.52), (2.0, 2.025)]
# A bow away from the straight line at mid range.
BOWED = [(0.0, 0.0), (1.0, 1.1), (2.0, 2.0)]
# The reported current falls back between the second and third point.
FOLDED = [(0.0, 0.0), (1.0, 1.2), (1.5, 1.0), (2.0, 2.0)]
# Clustered around mid range, reaching neither end.
CLUSTERED = [(0.9, 0.9), (1.0, 1.0), (1.1, 1.1)]


def _spec(**overrides):
    """Return a linearity spec with a three per cent class-referenced allowance."""
    spec = {
        "samples": list(SLOPED),
        "class_current_a": CLASS_A,
        "range_a": RANGE_A,
        "allowed_error_ratio": 0.03,
    }
    spec.update(overrides)
    return spec


class SampleValidationTests(unittest.TestCase):
    def test_pairs_are_returned_ordered_by_applied_current(self):
        pairs = validate_samples([(2.0, 2.0), (0.0, 0.0), (1.0, 1.0)])
        self.assertEqual([applied for applied, _ in pairs], [0.0, 1.0, 2.0])

    def test_integers_are_widened_to_floats(self):
        pairs = validate_samples([(0, 0), (1, 1), (2, 2)])
        self.assertIsInstance(pairs[1][0], float)

    def test_negative_reported_current_is_allowed(self):
        pairs = validate_samples([(0.0, -0.01), (1.0, 1.0), (2.0, 2.0)])
        self.assertAlmostEqual(pairs[0][1], -0.01, places=9)

    def test_negative_applied_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples([(-0.1, 0.0), (1.0, 1.0), (2.0, 2.0)])

    def test_too_few_points_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples([(0.0, 0.0), (1.0, 1.0)])

    def test_too_few_distinct_applied_currents_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples([(1.0, 1.0), (1.0, 1.01), (1.0, 0.99)])

    def test_malformed_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples([(0.0, 0.0), (1.0,), (2.0, 2.0)])

    def test_non_numeric_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples([(0.0, "0"), (1.0, 1.0), (2.0, 2.0)])

    def test_minimum_distinct_points_exceeds_a_two_point_fit(self):
        self.assertGreater(MIN_DISTINCT_POINTS, 2)


class ErrorTests(unittest.TestCase):
    def test_ideal_chain_has_no_error(self):
        self.assertEqual(signed_errors(IDEAL), [0.0] * len(IDEAL))

    def test_errors_carry_their_sign(self):
        errors = signed_errors([(0.0, -0.02), (1.0, 1.0), (2.0, 2.05)])
        self.assertAlmostEqual(errors[0], -0.02, places=9)
        self.assertAlmostEqual(errors[2], 0.05, places=9)

    def test_class_reference_divides_by_the_class_current_not_the_reading(self):
        ratios = class_referenced_errors([(0.0, 0.0), (1.0, 1.0), (2.0, 2.2)], 2.0)
        self.assertAlmostEqual(ratios[2], 0.1, places=9)

    def test_worst_point_is_the_largest_magnitude_not_the_last(self):
        worst = worst_class_referenced_error(
            [(0.0, -0.3), (1.0, 1.05), (2.0, 2.02)], CLASS_A
        )
        self.assertAlmostEqual(worst["applied_a"], 0.0, places=9)
        self.assertAlmostEqual(worst["class_referenced_ratio"], -0.3, places=9)

    def test_worst_point_reports_its_own_index(self):
        self.assertEqual(worst_class_referenced_error(SLOPED, CLASS_A)["index"], 4)

    def test_zero_class_current_rejected(self):
        with self.assertRaises(ValueError):
            class_referenced_errors(IDEAL, 0.0)


class ReferenceBasisTests(unittest.TestCase):
    def test_reading_basis_is_undefined_at_the_bottom_of_the_range(self):
        bases = compare_reference_bases(0.0, 0.01, CLASS_A)
        self.assertIsNone(bases["reading_referenced_ratio"])
        self.assertAlmostEqual(bases["class_referenced_ratio"], 0.01, places=9)

    def test_reading_basis_flatters_the_top_of_the_range(self):
        bases = compare_reference_bases(2.0, 2.1, CLASS_A)
        self.assertAlmostEqual(bases["class_referenced_ratio"], 0.1, places=9)
        self.assertAlmostEqual(bases["reading_referenced_ratio"], 0.05, places=9)

    def test_full_scale_basis_is_returned_when_a_full_scale_is_given(self):
        bases = compare_reference_bases(1.0, 1.1, CLASS_A, full_scale_a=5.0)
        self.assertAlmostEqual(bases["full_scale_referenced_ratio"], 0.02, places=9)

    def test_full_scale_basis_absent_without_a_full_scale(self):
        self.assertIsNone(
            compare_reference_bases(1.0, 1.1, CLASS_A)["full_scale_referenced_ratio"]
        )

    def test_negative_applied_current_rejected(self):
        with self.assertRaises(ValueError):
            compare_reference_bases(-1.0, 0.0, CLASS_A)


class FitTests(unittest.TestCase):
    def test_ideal_chain_fits_unit_slope_and_zero_intercept(self):
        slope, intercept = fit_linear(IDEAL)
        self.assertAlmostEqual(slope, 1.0, places=9)
        self.assertAlmostEqual(intercept, 0.0, places=9)

    def test_gain_and_offset_are_recovered_from_the_fit(self):
        slope, intercept = fit_linear(SLOPED)
        self.assertAlmostEqual(slope, 1.01, places=9)
        self.assertAlmostEqual(intercept, 0.005, places=9)

    def test_ideal_chain_has_no_residual(self):
        self.assertAlmostEqual(max_non_linearity(IDEAL, CLASS_A), 0.0, places=9)

    def test_a_pure_gain_and_offset_error_is_not_a_non_linearity(self):
        self.assertAlmostEqual(max_non_linearity(SLOPED, CLASS_A), 0.0, places=9)

    def test_a_bow_shows_up_as_a_residual(self):
        self.assertAlmostEqual(max_non_linearity(BOWED, CLASS_A), 1.0 / 15.0, places=9)

    def test_residuals_sum_to_zero_about_the_fitted_line(self):
        self.assertAlmostEqual(sum(non_linearity_ratios(BOWED, CLASS_A)), 0.0, places=9)


class CoverageAndReversalTests(unittest.TestCase):
    def test_a_set_reaching_both_ends_is_covered(self):
        self.assertTrue(range_coverage(IDEAL, 0.0, 2.0)["covered"])

    def test_a_clustered_set_covers_neither_end(self):
        coverage = range_coverage(CLUSTERED, 0.0, 2.0)
        self.assertFalse(coverage["low_covered"])
        self.assertFalse(coverage["high_covered"])
        self.assertAlmostEqual(coverage["high_gap_a"], 0.9, places=9)

    def test_edge_allowance_scales_with_the_declared_span(self):
        self.assertAlmostEqual(
            range_coverage(IDEAL, 0.0, 2.0, 0.10)["allowance_a"], 0.2, places=9
        )

    def test_inverted_declared_range_rejected(self):
        with self.assertRaises(ValueError):
            range_coverage(IDEAL, 2.0, 0.0)

    def test_edge_tolerance_at_half_the_span_rejected(self):
        with self.assertRaises(ValueError):
            range_coverage(IDEAL, 0.0, 2.0, 0.5)

    def test_a_monotone_set_has_no_reversal(self):
        self.assertEqual(reversal_indices(SLOPED), [])

    def test_a_fold_back_is_reported_at_its_index(self):
        self.assertEqual(reversal_indices(FOLDED), [2])


class AssessmentTests(unittest.TestCase):
    def test_a_chain_inside_its_allowance_is_compliant(self):
        result = assess_linearity(_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["worst_class_referenced_ratio"], 0.025, places=9)

    def test_a_tighter_allowance_turns_the_same_chain_non_compliant(self):
        result = assess_linearity(_spec(allowed_error_ratio=0.02))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("class current" in f for f in result["findings"]))

    def test_an_error_exactly_on_the_allowance_is_inside_it(self):
        result = assess_linearity(
            {
                "samples": [(0.0, 0.0), (1.0, 1.0), (2.0, 2.5)],
                "class_current_a": 10.0,
                "range_a": (0.0, 2.0),
                "allowed_error_ratio": 0.05,
            }
        )
        self.assertAlmostEqual(result["worst_class_referenced_ratio"], 0.05, places=9)
        self.assertTrue(result["within_accuracy"])

    def test_gain_and_offset_are_reported_against_the_class_current(self):
        result = assess_linearity(_spec())
        self.assertAlmostEqual(result["gain_error"], 0.01, places=9)
        self.assertAlmostEqual(result["offset_class_ratio"], 0.005, places=9)

    def test_a_clustered_calibration_is_a_coverage_finding(self):
        result = assess_linearity(_spec(samples=list(CLUSTERED)))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("bottom of the" in f for f in result["findings"]))
        self.assertTrue(any("short of the top" in f for f in result["findings"]))

    def test_a_fold_back_is_a_finding_of_its_own(self):
        result = assess_linearity(_spec(samples=list(FOLDED)))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("not linear" in f for f in result["findings"]))

    def test_a_bow_inside_the_accuracy_band_still_fails_a_residual_limit(self):
        result = assess_linearity(
            _spec(
                samples=list(BOWED),
                allowed_error_ratio=0.2,
                allowed_non_linearity_ratio=0.01,
            )
        )
        self.assertTrue(result["within_accuracy"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("fitted line" in f for f in result["findings"]))

    def test_no_residual_limit_leaves_the_bow_judged_on_accuracy_alone(self):
        result = assess_linearity(_spec(samples=list(BOWED), allowed_error_ratio=0.2))
        self.assertTrue(result["compliant"])

    def test_missing_key_rejected(self):
        spec = _spec()
        del spec["class_current_a"]
        with self.assertRaises(ValueError):
            assess_linearity(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_linearity(["samples"])

    def test_malformed_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_linearity(_spec(range_a=(0.0,)))

    def test_allowance_of_a_whole_class_current_rejected(self):
        with self.assertRaises(ValueError):
            assess_linearity(_spec(allowed_error_ratio=1.0))

    def test_accuracy_tolerance_stays_an_engineering_zero(self):
        self.assertLess(ACCURACY_TOLERANCE, 1e-9)


if __name__ == "__main__":
    unittest.main()
