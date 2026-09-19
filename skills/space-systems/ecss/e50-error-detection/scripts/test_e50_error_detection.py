"""Contract tests for the clause 5.6.13.4 error detection logic."""

import unittest

from e50_error_detection_logic import (
    COMPLIANT,
    COVER_NONE,
    COVER_PAYLOAD,
    COVER_WHOLE_UNIT,
    NON_COMPLIANT,
    assess_error_detection,
    corruption_probability,
    escape_fraction,
    undetected_probability,
    undetected_units_per_pass,
    validate_code,
    validate_coverage,
    validate_length_bits,
    validate_probability,
    weakest_sufficient_code,
)

UNIT = 8192
HEADER = 48
BER = 1e-7


class ValidationTests(unittest.TestCase):
    def test_known_code_accepted(self):
        self.assertEqual(validate_code("crc-32"), "crc-32")

    def test_unknown_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_code("reed-solomon-255")

    def test_known_coverage_accepted(self):
        self.assertEqual(validate_coverage(COVER_WHOLE_UNIT), COVER_WHOLE_UNIT)

    def test_unknown_coverage_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverage("trailer")

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_length_bits(0)

    def test_float_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_length_bits(8192.0)

    def test_boolean_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_length_bits(True)

    def test_probability_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(1.5)

    def test_negative_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(-1e-9)

    def test_text_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability("1e-7")

    def test_header_not_smaller_than_unit_rejected(self):
        with self.assertRaises(ValueError):
            assess_error_detection(64, 64, "crc-32", COVER_WHOLE_UNIT, BER, 1e-9)


class EscapeTests(unittest.TestCase):
    def test_no_code_lets_everything_through(self):
        self.assertAlmostEqual(escape_fraction("none"), 1.0, places=9)

    def test_crc16_escape_is_two_to_the_minus_sixteen(self):
        self.assertAlmostEqual(escape_fraction("crc-16"), 1.0 / 65536.0, places=15)

    def test_crc32_is_stronger_than_crc16(self):
        self.assertLess(escape_fraction("crc-32"), escape_fraction("crc-16"))

    def test_parity_escape_is_one_half(self):
        self.assertAlmostEqual(escape_fraction("parity"), 0.5, places=12)


class CorruptionTests(unittest.TestCase):
    def test_clean_channel_corrupts_nothing(self):
        self.assertAlmostEqual(corruption_probability(UNIT, 0.0), 0.0, places=12)

    def test_fully_broken_channel_corrupts_everything(self):
        self.assertAlmostEqual(corruption_probability(UNIT, 1.0), 1.0, places=12)

    def test_small_rate_is_close_to_the_linear_estimate(self):
        value = corruption_probability(UNIT, BER)
        self.assertAlmostEqual(value, UNIT * BER, places=6)

    def test_longer_unit_is_more_likely_to_be_corrupted(self):
        self.assertGreater(
            corruption_probability(2 * UNIT, BER), corruption_probability(UNIT, BER)
        )

    def test_single_bit_unit_matches_the_bit_error_rate(self):
        self.assertAlmostEqual(corruption_probability(1, 0.25), 0.25, places=12)


class UndetectedTests(unittest.TestCase):
    def test_undetected_is_corruption_times_escape(self):
        self.assertAlmostEqual(
            undetected_probability(UNIT, BER, "crc-16"),
            corruption_probability(UNIT, BER) * escape_fraction("crc-16"),
            places=15,
        )

    def test_uncoded_undetected_equals_corruption(self):
        self.assertAlmostEqual(
            undetected_probability(UNIT, BER, "none"),
            corruption_probability(UNIT, BER),
            places=15,
        )

    def test_per_pass_scales_with_the_unit_count(self):
        one = undetected_units_per_pass(UNIT, BER, "crc-16", 1)
        many = undetected_units_per_pass(UNIT, BER, "crc-16", 1000)
        self.assertAlmostEqual(many, 1000.0 * one, places=12)

    def test_zero_units_in_pass_rejected(self):
        with self.assertRaises(ValueError):
            undetected_units_per_pass(UNIT, BER, "crc-16", 0)


class SufficientCodeTests(unittest.TestCase):
    def test_loose_bound_is_met_by_the_weakest_code(self):
        self.assertEqual(weakest_sufficient_code(UNIT, BER, 1.0), "parity")

    def test_tight_bound_needs_a_wider_code(self):
        code = weakest_sufficient_code(UNIT, BER, 1e-12)
        self.assertEqual(code, "crc-32")

    def test_impossible_bound_returns_none(self):
        self.assertIsNone(weakest_sufficient_code(UNIT, BER, 1e-30))

    def test_named_code_actually_meets_the_bound(self):
        bound = 1e-12
        code = weakest_sufficient_code(UNIT, BER, bound)
        self.assertLessEqual(undetected_probability(UNIT, BER, code), bound)


class AssessTests(unittest.TestCase):
    def test_sound_design_is_compliant(self):
        result = assess_error_detection(UNIT, HEADER, "crc-32", COVER_WHOLE_UNIT, BER, 1e-12)
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertEqual(result["findings"], [])

    def test_missing_code_fails_the_first_obligation(self):
        result = assess_error_detection(UNIT, HEADER, "none", COVER_NONE, BER, 1e-12)
        self.assertFalse(result["obligations"]["code_present"])
        self.assertEqual(result["verdict"], NON_COMPLIANT)

    def test_payload_only_coverage_fails_the_second_obligation(self):
        result = assess_error_detection(UNIT, HEADER, "crc-32", COVER_PAYLOAD, BER, 1e-12)
        self.assertFalse(result["obligations"]["covers_whole_unit"])
        self.assertTrue(any("header bits are unprotected" in f for f in result["findings"]))

    def test_payload_only_coverage_still_counts_the_code_as_present(self):
        result = assess_error_detection(UNIT, HEADER, "crc-32", COVER_PAYLOAD, BER, 1e-12)
        self.assertTrue(result["obligations"]["code_present"])

    def test_weak_code_fails_the_third_obligation(self):
        result = assess_error_detection(UNIT, HEADER, "crc-16", COVER_WHOLE_UNIT, BER, 1e-12)
        self.assertFalse(result["obligations"]["within_bound"])

    def test_weak_code_is_told_which_code_would_do(self):
        result = assess_error_detection(UNIT, HEADER, "crc-16", COVER_WHOLE_UNIT, BER, 1e-12)
        self.assertEqual(result["weakest_sufficient_code"], "crc-32")

    def test_recommended_code_clears_the_bound_finding(self):
        result = assess_error_detection(UNIT, HEADER, "crc-16", COVER_WHOLE_UNIT, BER, 1e-12)
        fixed = assess_error_detection(
            UNIT, HEADER, result["weakest_sufficient_code"], COVER_WHOLE_UNIT, BER, 1e-12
        )
        self.assertTrue(fixed["obligations"]["within_bound"])

    def test_design_exactly_on_the_bound_is_within_it(self):
        exact = undetected_probability(UNIT, BER, "crc-32")
        result = assess_error_detection(UNIT, HEADER, "crc-32", COVER_WHOLE_UNIT, BER, exact)
        self.assertAlmostEqual(result["undetected_per_unit"], result["bound_per_unit"], places=15)
        self.assertTrue(result["obligations"]["within_bound"])

    def test_three_obligations_are_reported_separately(self):
        result = assess_error_detection(UNIT, HEADER, "crc-32", COVER_WHOLE_UNIT, BER, 1e-12)
        self.assertEqual(
            sorted(result["obligations"]), ["code_present", "covers_whole_unit", "within_bound"]
        )

    def test_payload_length_is_the_unit_less_the_header(self):
        result = assess_error_detection(UNIT, HEADER, "crc-32", COVER_WHOLE_UNIT, BER, 1e-12)
        self.assertEqual(result["payload_bits"], UNIT - HEADER)

    def test_per_pass_figure_is_carried(self):
        result = assess_error_detection(
            UNIT, HEADER, "crc-32", COVER_WHOLE_UNIT, BER, 1e-12, units_in_pass=5000
        )
        self.assertAlmostEqual(
            result["undetected_per_pass"], 5000.0 * result["undetected_per_unit"], places=15
        )

    def test_uncoded_unit_escapes_everything(self):
        result = assess_error_detection(UNIT, HEADER, "none", COVER_NONE, BER, 1e-12)
        self.assertAlmostEqual(result["escape_fraction"], 1.0, places=12)

    def test_bad_coverage_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_error_detection(UNIT, HEADER, "crc-32", "trailer", BER, 1e-12)

    def test_bad_bound_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_error_detection(UNIT, HEADER, "crc-32", COVER_WHOLE_UNIT, BER, 2.0)


if __name__ == "__main__":
    unittest.main()
