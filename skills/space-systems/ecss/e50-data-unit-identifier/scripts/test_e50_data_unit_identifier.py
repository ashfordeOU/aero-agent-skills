"""Contract tests for the clause 5.6.13.2 data unit identifier logic."""

import unittest

from e50_data_unit_identifier_logic import (
    AMBIGUOUS,
    MARGIN_SHORT,
    UNAMBIGUOUS,
    analyse_observed_sequence,
    assess_identifier_scheme,
    identifier_modulus,
    minimum_width_bits,
    units_in_window,
    validate_positive,
    validate_width_bits,
    wrap_period_s,
)


class ValidationTests(unittest.TestCase):
    def test_single_bit_field_accepted(self):
        self.assertEqual(validate_width_bits(1), 1)

    def test_zero_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_width_bits(0)

    def test_absurd_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_width_bits(128)

    def test_boolean_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_width_bits(True)

    def test_float_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_width_bits(8.0)

    def test_zero_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "production_rate_per_s")

    def test_non_finite_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("inf"), "production_rate_per_s")


class FieldArithmeticTests(unittest.TestCase):
    def test_modulus_is_two_to_the_width(self):
        self.assertEqual(identifier_modulus(8), 256)
        self.assertEqual(identifier_modulus(14), 16384)

    def test_wrap_period_is_the_modulus_over_the_rate(self):
        self.assertAlmostEqual(wrap_period_s(8, 10.0), 25.6, places=9)

    def test_a_wider_field_wraps_less_often(self):
        self.assertTrue(wrap_period_s(16, 10.0) > wrap_period_s(8, 10.0))

    def test_live_units_are_rate_times_window(self):
        self.assertAlmostEqual(units_in_window(10.0, 60.0), 600.0, places=9)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            units_in_window(10.0, 0.0)


class MinimumWidthTests(unittest.TestCase):
    def test_width_is_exact_at_a_power_of_two(self):
        self.assertEqual(minimum_width_bits(1024.0, 1.0, 2.0), 11)

    def test_width_rounds_up_off_a_power_of_two(self):
        self.assertEqual(minimum_width_bits(10.0, 60.0, 2.0), 11)

    def test_a_larger_margin_costs_a_bit(self):
        narrow = minimum_width_bits(1024.0, 1.0, 1.0)
        wide = minimum_width_bits(1024.0, 1.0, 2.0)
        self.assertEqual(narrow, 10)
        self.assertEqual(wide, 11)

    def test_a_tiny_demand_still_needs_one_bit(self):
        self.assertEqual(minimum_width_bits(0.1, 1.0, 1.0), 1)

    def test_margin_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            minimum_width_bits(10.0, 60.0, 0.5)

    def test_an_impossible_demand_raises(self):
        with self.assertRaises(ValueError):
            minimum_width_bits(1.0e18, 1000.0, 2.0)


class SchemeAssessmentTests(unittest.TestCase):
    def test_a_field_wrapping_inside_the_window_is_ambiguous(self):
        result = assess_identifier_scheme(8, 10.0, 60.0)
        self.assertEqual(result["verdict"], AMBIGUOUS)
        self.assertFalse(result["unambiguous"])

    def test_the_ambiguous_finding_names_the_wrap_period(self):
        result = assess_identifier_scheme(8, 10.0, 60.0)
        self.assertTrue(any("wraps every" in f for f in result["findings"]))

    def test_a_generous_field_is_unambiguous(self):
        result = assess_identifier_scheme(16, 10.0, 60.0)
        self.assertEqual(result["verdict"], UNAMBIGUOUS)
        self.assertTrue(result["unambiguous"])

    def test_coverage_is_reported(self):
        result = assess_identifier_scheme(10, 10.0, 60.0)
        self.assertAlmostEqual(result["coverage"], 1.7066666666666668, places=9)

    def test_a_field_covering_the_window_exactly_once_is_not_ambiguous(self):
        result = assess_identifier_scheme(10, 1024.0, 1.0)
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)
        self.assertTrue(result["unambiguous"])
        self.assertEqual(result["verdict"], MARGIN_SHORT)

    def test_a_field_meeting_the_margin_exactly_is_unambiguous(self):
        result = assess_identifier_scheme(11, 1024.0, 1.0, margin_factor=2.0)
        self.assertAlmostEqual(result["coverage"], 2.0, places=9)
        self.assertEqual(result["verdict"], UNAMBIGUOUS)

    def test_the_recommended_width_fixes_an_ambiguous_scheme(self):
        result = assess_identifier_scheme(8, 10.0, 60.0)
        fixed = assess_identifier_scheme(
            result["recommended_width_bits"], 10.0, 60.0
        )
        self.assertEqual(fixed["verdict"], UNAMBIGUOUS)

    def test_wrap_period_is_carried_in_the_report(self):
        result = assess_identifier_scheme(8, 10.0, 60.0)
        self.assertAlmostEqual(result["wrap_period_s"], 25.6, places=9)

    def test_margin_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_identifier_scheme(16, 10.0, 60.0, margin_factor=0.9)

    def test_negative_window_rejected(self):
        with self.assertRaises(ValueError):
            assess_identifier_scheme(16, 10.0, -1.0)


class ObservedSequenceTests(unittest.TestCase):
    def test_a_contiguous_run_has_no_gaps(self):
        result = analyse_observed_sequence([0, 1, 2, 3], 4)
        self.assertTrue(result["contiguous"])
        self.assertEqual(result["gaps"], [])

    def test_a_missing_unit_is_named(self):
        result = analyse_observed_sequence([0, 1, 3, 4], 4)
        self.assertEqual(result["gaps"], [2])
        self.assertEqual(result["missing_count"], 1)

    def test_several_missing_units_are_all_named(self):
        result = analyse_observed_sequence([0, 5], 4)
        self.assertEqual(result["gaps"], [1, 2, 3, 4])

    def test_a_wrap_is_counted_and_is_not_a_gap(self):
        result = analyse_observed_sequence([6, 7, 0, 1], 3)
        self.assertEqual(result["wrap_count"], 1)
        self.assertEqual(result["gaps"], [])

    def test_a_repeated_identifier_is_a_duplicate_not_a_wrap(self):
        result = analyse_observed_sequence([0, 1, 1, 2], 4)
        self.assertEqual(result["duplicates"], [1])
        self.assertEqual(result["wrap_count"], 0)
        self.assertFalse(result["contiguous"])

    def test_gaps_are_named_modulo_the_field(self):
        result = analyse_observed_sequence([6, 1], 3)
        self.assertEqual(result["gaps"], [7, 0])

    def test_expected_next_wraps_with_the_field(self):
        result = analyse_observed_sequence([6, 7], 3)
        self.assertEqual(result["expected_next"], 0)

    def test_distinct_count_separates_repeats_from_length(self):
        result = analyse_observed_sequence([0, 1, 1, 2], 4)
        self.assertEqual(result["observed_count"], 4)
        self.assertEqual(result["distinct_count"], 3)

    def test_a_value_the_field_cannot_carry_is_rejected(self):
        with self.assertRaises(ValueError):
            analyse_observed_sequence([0, 1, 16], 4)

    def test_a_negative_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            analyse_observed_sequence([0, -1], 4)

    def test_a_boolean_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            analyse_observed_sequence([0, True], 4)

    def test_an_empty_run_is_rejected(self):
        with self.assertRaises(ValueError):
            analyse_observed_sequence([], 4)

    def test_a_non_list_run_is_rejected(self):
        with self.assertRaises(ValueError):
            analyse_observed_sequence({"id": 1}, 4)


if __name__ == "__main__":
    unittest.main()
