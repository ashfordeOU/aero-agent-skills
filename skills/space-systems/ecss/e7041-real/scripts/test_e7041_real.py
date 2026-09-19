#!/usr/bin/env python3
"""Contract test for the real parameter type (offline).

Every numeric assertion here is either an exact binary quantity
(struct round trips, math.ldexp scalings) or an assertAlmostEqual at
nine places. No bound is asserted with a strict inequality against a
value a float computation can land exactly on.
"""

import math
import unittest

from e7041_real_logic import (
    DOUBLE,
    ENCODING_ORDER,
    REAL_PTC,
    SINGLE,
    VERDICT_OVERFLOWS,
    VERDICT_REPRESENTABLE,
    VERDICT_ROUNDED,
    VERDICT_UNDERFLOWS,
    assess_real_field,
    decode_real,
    encode_real,
    encoding_octets,
    is_exactly_representable,
    largest_finite,
    relative_resolution,
    round_trip,
    round_trip_error,
    select_real_encoding,
    smallest_normal,
    validate_encoding,
)


class EncodingTableTests(unittest.TestCase):
    def test_both_offered_encodings_validate(self):
        for encoding in ENCODING_ORDER:
            self.assertEqual(validate_encoding(encoding), encoding)

    def test_an_unknown_encoding_rejected(self):
        with self.assertRaises(ValueError):
            validate_encoding("ieee754-half")

    def test_the_single_encoding_occupies_four_octets(self):
        self.assertEqual(encoding_octets(SINGLE), 4)

    def test_the_double_encoding_occupies_eight_octets(self):
        self.assertEqual(encoding_octets(DOUBLE), 8)

    def test_the_order_runs_narrowest_first(self):
        self.assertEqual(ENCODING_ORDER[0], SINGLE)
        self.assertEqual(
            encoding_octets(ENCODING_ORDER[0]) < encoding_octets(ENCODING_ORDER[1]),
            True,
        )


class ResolutionTests(unittest.TestCase):
    def test_single_resolution_is_an_exact_binary_scaling(self):
        self.assertEqual(relative_resolution(SINGLE), math.ldexp(1.0, -23))

    def test_double_resolution_is_an_exact_binary_scaling(self):
        self.assertEqual(relative_resolution(DOUBLE), math.ldexp(1.0, -52))

    def test_the_double_resolution_is_far_finer_than_the_single_one(self):
        ratio = relative_resolution(SINGLE) / relative_resolution(DOUBLE)
        self.assertAlmostEqual(ratio / math.ldexp(1.0, 29), 1.0, places=9)

    def test_the_largest_finite_values_are_ordered(self):
        self.assertAlmostEqual(
            largest_finite(SINGLE) / largest_finite(DOUBLE), 0.0, places=9
        )

    def test_the_smallest_normal_values_are_positive(self):
        for encoding in ENCODING_ORDER:
            self.assertGreater(smallest_normal(encoding), 0.0)


class EncodeDecodeTests(unittest.TestCase):
    def test_a_binary_exact_value_survives_the_single_encoding(self):
        self.assertEqual(round_trip(0.25, SINGLE), 0.25)

    def test_a_binary_exact_value_survives_the_double_encoding(self):
        self.assertEqual(round_trip(0.25, DOUBLE), 0.25)

    def test_a_decimal_fraction_is_rounded_by_the_single_encoding(self):
        self.assertNotEqual(round_trip(0.1, SINGLE), 0.1)

    def test_a_double_encoding_round_trips_a_python_float_exactly(self):
        self.assertEqual(round_trip(0.1, DOUBLE), 0.1)

    def test_the_single_encoding_produces_four_octets(self):
        self.assertEqual(len(encode_real(1.0, SINGLE)), 4)

    def test_one_point_zero_has_the_expected_single_pattern(self):
        self.assertEqual(encode_real(1.0, SINGLE), b"\x3f\x80\x00\x00")

    def test_decoding_that_pattern_gives_one_point_zero_back(self):
        self.assertEqual(decode_real(b"\x3f\x80\x00\x00", SINGLE), 1.0)

    def test_an_octet_run_of_the_wrong_length_rejected(self):
        with self.assertRaises(ValueError):
            decode_real(b"\x3f\x80\x00", SINGLE)

    def test_a_text_octet_run_rejected(self):
        with self.assertRaises(ValueError):
            decode_real("3f800000", SINGLE)

    def test_an_infinite_value_is_refused_not_packed(self):
        with self.assertRaises(ValueError):
            encode_real(float("inf"), SINGLE)

    def test_a_not_a_number_value_is_refused(self):
        with self.assertRaises(ValueError):
            encode_real(float("nan"), DOUBLE)

    def test_a_magnitude_past_the_single_encoding_is_refused(self):
        with self.assertRaises(ValueError):
            encode_real(1.0e39, SINGLE)

    def test_a_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            encode_real("1.0", SINGLE)


class RepresentabilityTests(unittest.TestCase):
    def test_a_power_of_two_fraction_is_exact_in_the_single_encoding(self):
        self.assertTrue(is_exactly_representable(0.5, SINGLE))

    def test_a_decimal_fraction_is_not_exact_in_the_single_encoding(self):
        self.assertFalse(is_exactly_representable(0.1, SINGLE))

    def test_zero_carries_no_error(self):
        error = round_trip_error(0.0, SINGLE)
        self.assertAlmostEqual(error["relative_error"], 0.0, places=9)
        self.assertTrue(error["exact"])

    def test_the_single_encoding_error_stays_within_its_resolution(self):
        error = round_trip_error(0.1, SINGLE)
        self.assertLess(error["relative_error"], relative_resolution(SINGLE))

    def test_an_exact_value_reports_no_absolute_error(self):
        error = round_trip_error(2.5, SINGLE)
        self.assertAlmostEqual(error["absolute_error"], 0.0, places=9)


class SelectionTests(unittest.TestCase):
    def test_a_modest_range_and_precision_select_the_single_encoding(self):
        self.assertEqual(select_real_encoding(1000.0, 1.0e-5), SINGLE)

    def test_a_precision_exactly_on_the_single_resolution_still_selects_single(self):
        self.assertEqual(
            select_real_encoding(1000.0, relative_resolution(SINGLE)), SINGLE
        )

    def test_a_precision_finer_than_the_single_resolution_selects_double(self):
        self.assertEqual(
            select_real_encoding(1000.0, relative_resolution(DOUBLE)), DOUBLE
        )

    def test_a_magnitude_past_the_single_range_selects_double(self):
        self.assertEqual(select_real_encoding(1.0e39, 1.0e-5), DOUBLE)

    def test_a_precision_no_encoding_offers_is_refused(self):
        with self.assertRaises(ValueError):
            select_real_encoding(1.0, math.ldexp(1.0, -80))

    def test_a_magnitude_no_encoding_offers_is_refused(self):
        with self.assertRaises(ValueError):
            select_real_encoding(largest_finite(DOUBLE) * 2.0, 1.0e-3)

    def test_a_negative_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            select_real_encoding(-1.0, 1.0e-5)

    def test_a_zero_precision_rejected(self):
        with self.assertRaises(ValueError):
            select_real_encoding(1.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_an_exact_value_is_reported_representable(self):
        result = assess_real_field({"encoding": SINGLE, "value": 0.25})
        self.assertEqual(result["verdict"], VERDICT_REPRESENTABLE)
        self.assertEqual(result["ptc"], REAL_PTC)
        self.assertEqual(result["findings"], [])

    def test_a_rounded_value_is_reported_with_its_error(self):
        result = assess_real_field({"encoding": SINGLE, "value": 0.1})
        self.assertEqual(result["verdict"], VERDICT_ROUNDED)
        self.assertLess(result["relative_error"], relative_resolution(SINGLE))
        self.assertTrue(any("relative error" in f for f in result["findings"]))

    def test_an_over_range_value_is_reported_rather_than_packed(self):
        result = assess_real_field({"encoding": SINGLE, "value": 1.0e300})
        self.assertEqual(result["verdict"], VERDICT_OVERFLOWS)
        self.assertIsNone(result["stored"])
        self.assertTrue(any("infinity code" in f for f in result["findings"]))

    def test_a_tiny_value_is_reported_as_underflowing_to_zero(self):
        result = assess_real_field({"encoding": SINGLE, "value": 1.0e-50})
        self.assertEqual(result["verdict"], VERDICT_UNDERFLOWS)
        self.assertAlmostEqual(result["stored"], 0.0, places=9)

    def test_the_same_tiny_value_is_fine_in_the_double_encoding(self):
        result = assess_real_field({"encoding": DOUBLE, "value": 1.0e-50})
        self.assertEqual(result["verdict"], VERDICT_REPRESENTABLE)

    def test_the_octet_width_is_reported(self):
        result = assess_real_field({"encoding": DOUBLE, "value": 1.0})
        self.assertEqual(result["octets"], 8)

    def test_an_infinite_value_in_a_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_real_field({"encoding": SINGLE, "value": float("inf")})

    def test_a_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_real_field("0.25")

    def test_a_spec_without_an_encoding_rejected(self):
        with self.assertRaises(ValueError):
            assess_real_field({"value": 0.25})


if __name__ == "__main__":
    unittest.main()
