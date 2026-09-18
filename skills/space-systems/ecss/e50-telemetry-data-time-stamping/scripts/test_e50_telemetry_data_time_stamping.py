"""Contract tests for the clause 5.5.5 telemetry time-stamping logic."""

import math
import unittest

from e50_telemetry_data_time_stamping_logic import (
    ACCURACY_TOLERANCE_S,
    COMBINATION_RULES,
    assess_time_stamping,
    clock_drift_error_s,
    combine_errors_s,
    monotonicity_breaks,
    quantisation_error_s,
    rank_contributors,
    required_field_bits,
    validate_contributor,
    validate_contributors,
)

WEEK_S = 604800.0


def _latency():
    return [
        {"name": "acquisition-conversion", "magnitude_s": 0.002},
        {"name": "sampling-to-stamp-latency", "magnitude_s": 0.008},
    ]


class ValidateContributorTests(unittest.TestCase):
    def test_returns_normalised_record(self):
        record = validate_contributor({"name": "latency", "magnitude_s": 3})
        self.assertEqual(record["name"], "latency")
        self.assertAlmostEqual(record["magnitude_s"], 3.0)

    def test_zero_magnitude_allowed(self):
        self.assertAlmostEqual(
            validate_contributor({"name": "latency", "magnitude_s": 0.0})["magnitude_s"],
            0.0,
        )

    def test_negative_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_contributor({"name": "latency", "magnitude_s": -1e-3})

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_contributor({"name": "latency"})

    def test_non_finite_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_contributor({"name": "latency", "magnitude_s": float("nan")})

    def test_non_mapping_contributor_rejected(self):
        with self.assertRaises(ValueError):
            validate_contributor(("latency", 1.0))

    def test_empty_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_contributors([])

    def test_duplicate_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_contributors(_latency() + [
                {"name": "acquisition-conversion", "magnitude_s": 0.001}
            ])


class DriftAndQuantisationTests(unittest.TestCase):
    def test_drift_over_a_week_at_one_ppm(self):
        self.assertAlmostEqual(clock_drift_error_s(1.0, WEEK_S), 0.6048, places=9)

    def test_drift_is_linear_in_the_correlation_interval(self):
        one = clock_drift_error_s(2.5, WEEK_S)
        two = clock_drift_error_s(2.5, 2.0 * WEEK_S)
        self.assertAlmostEqual(two, 2.0 * one, places=9)

    def test_drift_is_zero_immediately_after_correlation(self):
        self.assertAlmostEqual(clock_drift_error_s(5.0, 0.0), 0.0)

    def test_negative_stability_rejected(self):
        with self.assertRaises(ValueError):
            clock_drift_error_s(-1.0, WEEK_S)

    def test_quantisation_is_half_the_least_significant_bit(self):
        self.assertAlmostEqual(quantisation_error_s(2.0 ** -16), 2.0 ** -17, places=12)

    def test_quantisation_rejects_zero_lsb(self):
        with self.assertRaises(ValueError):
            quantisation_error_s(0.0)


class CombinationTests(unittest.TestCase):
    def test_worst_case_is_the_sum(self):
        self.assertAlmostEqual(combine_errors_s([0.002, 0.008, 0.01]), 0.02, places=12)

    def test_root_sum_square_of_three_and_four(self):
        self.assertAlmostEqual(
            combine_errors_s([3.0, 4.0], "root-sum-square"), 5.0, places=12
        )

    def test_root_sum_square_is_never_above_the_worst_case(self):
        values = [0.002, 0.008, 0.01]
        rss = combine_errors_s(values, "root-sum-square")
        worst = combine_errors_s(values, "worst-case")
        self.assertLess(rss, worst)

    def test_single_contributor_is_itself_under_both_rules(self):
        self.assertAlmostEqual(combine_errors_s([0.25], "worst-case"), 0.25, places=12)
        self.assertAlmostEqual(
            combine_errors_s([0.25], "root-sum-square"), 0.25, places=12
        )

    def test_unknown_rule_rejected(self):
        with self.assertRaises(ValueError):
            combine_errors_s([1.0], "average")

    def test_empty_magnitudes_rejected(self):
        with self.assertRaises(ValueError):
            combine_errors_s([])

    def test_both_rules_are_published(self):
        self.assertEqual(set(COMBINATION_RULES), {"worst-case", "root-sum-square"})

    def test_ranking_puts_the_dominant_term_first(self):
        ranked = rank_contributors(_latency() + [
            {"name": "on-board-clock-drift", "magnitude_s": 0.6048}
        ])
        self.assertEqual(ranked[0]["name"], "on-board-clock-drift")

    def test_ranking_breaks_ties_by_name(self):
        ranked = rank_contributors([
            {"name": "zulu", "magnitude_s": 0.01},
            {"name": "alpha", "magnitude_s": 0.01},
        ])
        self.assertEqual([r["name"] for r in ranked], ["alpha", "zulu"])


class FieldSizingTests(unittest.TestCase):
    def test_exact_power_of_two_span(self):
        self.assertEqual(required_field_bits(1024.0, 1.0), 10)

    def test_one_tick_over_a_power_of_two_needs_another_bit(self):
        self.assertEqual(required_field_bits(1025.0, 1.0), 11)

    def test_finer_resolution_costs_bits(self):
        coarse = required_field_bits(1024.0, 1.0)
        fine = required_field_bits(1024.0, 0.25)
        self.assertEqual(fine - coarse, 2)

    def test_single_tick_span_needs_one_bit(self):
        self.assertEqual(required_field_bits(1.0, 1.0), 1)

    def test_zero_span_rejected(self):
        with self.assertRaises(ValueError):
            required_field_bits(0.0, 1.0)

    def test_zero_resolution_rejected(self):
        with self.assertRaises(ValueError):
            required_field_bits(1024.0, 0.0)


class MonotonicityTests(unittest.TestCase):
    def test_increasing_sequence_has_no_breaks(self):
        self.assertEqual(monotonicity_breaks([1.0, 2.0, 3.0, 4.0]), [])

    def test_repeated_stamp_is_not_a_backward_step(self):
        self.assertEqual(monotonicity_breaks([1.0, 1.0, 2.0]), [])

    def test_backward_step_is_reported_with_its_index(self):
        breaks = monotonicity_breaks([1.0, 5.0, 3.0, 6.0])
        self.assertEqual(len(breaks), 1)
        self.assertEqual(breaks[0][0], 2)
        self.assertAlmostEqual(breaks[0][1], -2.0, places=12)

    def test_two_backward_steps_are_both_reported(self):
        self.assertEqual(len(monotonicity_breaks([5.0, 4.0, 6.0, 1.0])), 2)

    def test_single_stamp_rejected(self):
        with self.assertRaises(ValueError):
            monotonicity_breaks([1.0])

    def test_non_numeric_stamp_rejected(self):
        with self.assertRaises(ValueError):
            monotonicity_breaks([1.0, "2.0"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "latency_contributors": _latency(),
            "stability_ppm": 0.05,
            "elapsed_since_correlation_s": 3600.0,
            "correlation_residual_s": 0.001,
            "least_significant_bit_s": 2.0 ** -16,
            "required_accuracy_s": 0.05,
            "mission_span_s": 5.0e8,
            "declared_field_bits": 48,
            "combination_rule": "worst-case",
        }
        spec.update(overrides)
        return spec

    def test_clean_design_is_compliant(self):
        result = assess_time_stamping(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_drift_and_quantisation_join_the_contributor_list(self):
        names = [r["name"] for r in assess_time_stamping(self._spec())["contributors"]]
        self.assertIn("on-board-clock-drift", names)
        self.assertIn("stamp-field-quantisation", names)

    def test_total_is_the_worst_case_sum_of_the_terms(self):
        result = assess_time_stamping(self._spec())
        expected = math.fsum(r["magnitude_s"] for r in result["contributors"])
        self.assertAlmostEqual(result["total_error_s"], expected, places=12)

    def test_root_sum_square_gives_a_smaller_total(self):
        worst = assess_time_stamping(self._spec())["total_error_s"]
        rss = assess_time_stamping(
            self._spec(combination_rule="root-sum-square")
        )["total_error_s"]
        self.assertLess(rss, worst)

    def test_long_correlation_interval_makes_drift_dominant(self):
        result = assess_time_stamping(
            self._spec(elapsed_since_correlation_s=WEEK_S, required_accuracy_s=0.1)
        )
        self.assertEqual(result["dominant_contributor"], "on-board-clock-drift")

    def test_budget_overrun_is_flagged(self):
        result = assess_time_stamping(
            self._spec(stability_ppm=5.0, elapsed_since_correlation_s=WEEK_S)
        )
        self.assertFalse(result["compliant"])
        self.assertFalse(result["within_accuracy"])
        self.assertTrue(any("exceeds the required accuracy" in f for f in result["findings"]))

    def test_exact_boundary_budget_is_within_accuracy(self):
        spec = self._spec()
        total = assess_time_stamping(spec)["total_error_s"]
        result = assess_time_stamping(self._spec(required_accuracy_s=total))
        self.assertTrue(result["within_accuracy"])
        self.assertAlmostEqual(
            result["total_error_s"] - result["required_accuracy_s"], 0.0, places=12
        )

    def test_coarse_field_cannot_resolve_the_requirement(self):
        result = assess_time_stamping(
            self._spec(least_significant_bit_s=1.0, required_accuracy_s=0.05)
        )
        self.assertTrue(any("cannot resolve" in f for f in result["findings"]))

    def test_narrow_field_wraps_before_end_of_mission(self):
        result = assess_time_stamping(self._spec(declared_field_bits=20))
        self.assertGreater(result["required_field_bits"], 20)
        self.assertTrue(any("wraps" in f for f in result["findings"]))

    def test_backward_stamp_is_flagged(self):
        result = assess_time_stamping(self._spec(stamps_s=[10.0, 12.0, 11.5, 14.0]))
        self.assertEqual(len(result["monotonicity_breaks"]), 1)
        self.assertTrue(any("steps backwards" in f for f in result["findings"]))

    def test_monotonic_stamp_sequence_adds_no_finding(self):
        result = assess_time_stamping(self._spec(stamps_s=[10.0, 12.0, 14.0]))
        self.assertEqual(result["monotonicity_breaks"], [])
        self.assertTrue(result["compliant"])

    def test_tolerance_is_representation_sized(self):
        self.assertLess(ACCURACY_TOLERANCE_S, 1e-9)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["mission_span_s"]
        with self.assertRaises(ValueError):
            assess_time_stamping(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_time_stamping(["latency_contributors"])

    def test_zero_declared_field_bits_rejected(self):
        with self.assertRaises(ValueError):
            assess_time_stamping(self._spec(declared_field_bits=0))

    def test_unknown_combination_rule_rejected(self):
        with self.assertRaises(ValueError):
            assess_time_stamping(self._spec(combination_rule="average"))


if __name__ == "__main__":
    unittest.main()
