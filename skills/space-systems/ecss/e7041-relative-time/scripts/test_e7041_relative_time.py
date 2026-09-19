"""Contract tests for the clause 7.3.11 relative-time data-type logic."""

import unittest

from e7041_relative_time_logic import (
    MAX_COARSE_OCTETS,
    MAX_FINE_OCTETS,
    add_to_absolute,
    assess_relative_time_usage,
    decode_relative,
    difference_of_absolutes,
    encode_relative,
    relative_resolution_s,
    relative_span_s,
    sum_of_relatives,
    validate_relative_spec,
)

REL_4_1 = validate_relative_spec(4, 1)
REL_1_1 = validate_relative_spec(1, 1)
REL_2_2 = validate_relative_spec(2, 2)


class SpecTests(unittest.TestCase):
    def test_a_relative_definition_carries_no_epoch(self):
        self.assertNotIn("epoch", REL_4_1)

    def test_the_definition_is_signed(self):
        self.assertTrue(REL_4_1["signed"])

    def test_field_octets_are_the_two_counts(self):
        self.assertEqual(REL_2_2["field_octets"], 4)

    def test_the_coarse_range_is_asymmetric(self):
        self.assertEqual(REL_1_1["coarse_min"], -128)
        self.assertEqual(REL_1_1["coarse_max"], 127)

    def test_resolution_comes_from_the_fine_field_alone(self):
        self.assertAlmostEqual(relative_resolution_s(REL_4_1), 1.0 / 256.0, places=12)

    def test_two_fine_octets_resolve_finer(self):
        self.assertAlmostEqual(relative_resolution_s(REL_2_2), 1.0 / 65536.0, places=15)

    def test_span_reaches_one_step_further_below_zero(self):
        low, high = relative_span_s(REL_1_1)
        self.assertAlmostEqual(low, -128.0, places=9)
        self.assertAlmostEqual(high, 127.0 + 255.0 / 256.0, places=9)

    def test_zero_coarse_octets_refused(self):
        with self.assertRaises(ValueError):
            validate_relative_spec(0, 1)

    def test_too_many_coarse_octets_refused(self):
        with self.assertRaises(ValueError):
            validate_relative_spec(MAX_COARSE_OCTETS + 1, 1)

    def test_too_many_fine_octets_refused(self):
        with self.assertRaises(ValueError):
            validate_relative_spec(4, MAX_FINE_OCTETS + 1)

    def test_non_integer_width_refused(self):
        with self.assertRaises(ValueError):
            validate_relative_spec("4", 1)


class EncodingTests(unittest.TestCase):
    def test_a_positive_whole_second(self):
        out = encode_relative(5.0, REL_4_1)
        self.assertEqual((out["coarse"], out["fine"]), (5, 0))

    def test_a_positive_fraction(self):
        out = encode_relative(5.5, REL_4_1)
        self.assertEqual((out["coarse"], out["fine"]), (5, 128))

    def test_a_negative_whole_second(self):
        out = encode_relative(-5.0, REL_4_1)
        self.assertEqual((out["coarse"], out["fine"]), (-5, 0))

    def test_a_negative_fraction_keeps_the_fine_count_non_negative(self):
        out = encode_relative(-0.5, REL_4_1)
        self.assertEqual((out["coarse"], out["fine"]), (-1, 128))

    def test_zero_encodes_to_zero(self):
        out = encode_relative(0.0, REL_4_1)
        self.assertEqual((out["coarse"], out["fine"]), (0, 0))

    def test_round_trip_of_a_negative_fraction(self):
        out = encode_relative(-2.25, REL_4_1)
        self.assertAlmostEqual(
            decode_relative(out["coarse"], out["fine"], REL_4_1), -2.25, places=9
        )

    def test_encoding_floors_towards_minus_infinity(self):
        out = encode_relative(-0.001, REL_4_1)
        self.assertEqual(out["coarse"], -1)
        self.assertLessEqual(decode_relative(out["coarse"], out["fine"], REL_4_1), -0.001)

    def test_the_most_negative_duration_is_representable(self):
        out = encode_relative(-128.0, REL_1_1)
        self.assertEqual(out["coarse"], -128)

    def test_one_step_beyond_the_negative_end_refused(self):
        with self.assertRaises(ValueError):
            encode_relative(-128.01, REL_1_1)

    def test_the_positive_end_refuses_one_step_past_it(self):
        with self.assertRaises(ValueError):
            encode_relative(128.0, REL_1_1)

    def test_a_non_finite_duration_refused(self):
        with self.assertRaises(ValueError):
            encode_relative(float("nan"), REL_4_1)

    def test_a_negative_fine_count_refused_on_decode(self):
        with self.assertRaises(ValueError):
            decode_relative(-1, -1, REL_4_1)

    def test_a_fine_count_overflowing_its_field_refused(self):
        with self.assertRaises(ValueError):
            decode_relative(0, 256, REL_4_1)

    def test_a_coarse_count_outside_the_signed_range_refused(self):
        with self.assertRaises(ValueError):
            decode_relative(128, 0, REL_1_1)


class ArithmeticTests(unittest.TestCase):
    def test_a_duration_offsets_a_moment_forward(self):
        self.assertAlmostEqual(add_to_absolute(1000.0, 30.5, 2.0 ** 32), 1030.5, places=9)

    def test_a_negative_duration_offsets_a_moment_back(self):
        self.assertAlmostEqual(add_to_absolute(1000.0, -30.5, 2.0 ** 32), 969.5, places=9)

    def test_an_offset_before_the_epoch_refused(self):
        with self.assertRaises(ValueError):
            add_to_absolute(10.0, -20.0, 2.0 ** 32)

    def test_an_offset_past_the_absolute_span_refused(self):
        with self.assertRaises(ValueError):
            add_to_absolute(100.0, 2.0 ** 32, 2.0 ** 32)

    def test_a_negative_moment_refused(self):
        with self.assertRaises(ValueError):
            add_to_absolute(-1.0, 5.0, 2.0 ** 32)

    def test_a_difference_of_moments_is_a_duration(self):
        self.assertAlmostEqual(difference_of_absolutes(1000.0, 940.25, REL_4_1), 59.75,
                               places=9)

    def test_a_backwards_difference_is_negative_not_an_error(self):
        self.assertAlmostEqual(difference_of_absolutes(940.0, 1000.0, REL_4_1), -60.0,
                               places=9)

    def test_a_difference_the_field_cannot_hold_refused(self):
        with self.assertRaises(ValueError):
            difference_of_absolutes(100000.0, 0.0, REL_1_1)

    def test_a_negative_moment_in_a_difference_refused(self):
        with self.assertRaises(ValueError):
            difference_of_absolutes(100.0, -1.0, REL_4_1)

    def test_durations_accumulate(self):
        self.assertAlmostEqual(sum_of_relatives([1.5, 2.5, -1.0], REL_4_1), 3.0, places=9)

    def test_a_running_total_leaving_the_range_refused(self):
        with self.assertRaises(ValueError):
            sum_of_relatives([100.0, 100.0], REL_1_1)

    def test_a_non_sequence_of_durations_refused(self):
        with self.assertRaises(ValueError):
            sum_of_relatives(5.0, REL_4_1)


class AssessmentTests(unittest.TestCase):
    def test_ordinary_durations_report_no_findings(self):
        report = assess_relative_time_usage(REL_4_1, [1.5, -2.25, 0.0])
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["adequate"])

    def test_negative_durations_are_counted_not_faulted(self):
        report = assess_relative_time_usage(REL_4_1, [-1.0, -2.0, 3.0])
        self.assertEqual(report["negative_durations"], 2)
        self.assertEqual(report["findings"], [])

    def test_applying_an_epoch_to_a_duration_is_a_finding(self):
        report = assess_relative_time_usage(REL_4_1, [1.0], reference_epoch_applied=True)
        self.assertTrue(any("measured from" in f for f in report["findings"]))

    def test_a_duration_coarser_than_its_endpoints_is_a_finding(self):
        report = assess_relative_time_usage(REL_4_1, [1.0], absolute_fine_octets=2)
        self.assertTrue(any("quantised coarser" in f for f in report["findings"]))

    def test_matching_fine_widths_report_nothing(self):
        report = assess_relative_time_usage(REL_2_2, [1.0], absolute_fine_octets=2)
        self.assertEqual(report["findings"], [])

    def test_a_resolution_shortfall_is_a_finding(self):
        report = assess_relative_time_usage(REL_4_1, [1.0], required_resolution_s=1e-6)
        self.assertTrue(any("coarser than" in f for f in report["findings"]))

    def test_a_duration_outside_the_field_is_refused_and_reported(self):
        report = assess_relative_time_usage(REL_1_1, [1000.0])
        self.assertEqual(len(report["refused"]), 1)
        self.assertFalse(report["adequate"])

    def test_reaching_the_asymmetric_negative_end_is_named(self):
        report = assess_relative_time_usage(REL_1_1, [-128.0])
        self.assertTrue(any("asymmetric" in f for f in report["findings"]))

    def test_the_reported_range_matches_the_definition(self):
        report = assess_relative_time_usage(REL_1_1, [])
        self.assertAlmostEqual(report["range_s"][0], -128.0, places=9)

    def test_a_non_definition_refused(self):
        with self.assertRaises(ValueError):
            assess_relative_time_usage({"code": "absolute"}, [1.0])

    def test_a_non_positive_required_resolution_refused(self):
        with self.assertRaises(ValueError):
            assess_relative_time_usage(REL_4_1, [1.0], required_resolution_s=-1.0)

    def test_a_negative_absolute_fine_width_refused(self):
        with self.assertRaises(ValueError):
            assess_relative_time_usage(REL_4_1, [1.0], absolute_fine_octets=-1)


if __name__ == "__main__":
    unittest.main()
